
import history
import main
import datetime
import strategy
import indicators
import os
import csv
import concurrent.futures

# CONFIG
DATES = ["2026-01-29", "2026-01-30"]
TIMEFRAME = "2" # 2 Minute
token = main.load_access_token()

STRIKES_TO_CHECK = range(24000, 26000, 100) 
EXPIRY_CODE = "26203" # Feb 03 Expiry as requested

def get_valid_option_symbols(date_str, token):
    valid_symbols = []
    potential_symbols = []
    for s in STRIKES_TO_CHECK:
        potential_symbols.append(f"NSE:NIFTY{EXPIRY_CODE}{s}CE")
        potential_symbols.append(f"NSE:NIFTY{EXPIRY_CODE}{s}PE")
    
    # print(f"[{date_str}] Checking {len(potential_symbols)} symbols...")
    
    # print(f"[{date_str}] Checking {len(potential_symbols)} symbols...")
    
    # Sequential fetch to avoid rate limits
    for sym in potential_symbols:
        try:
            data = history.get_history(token, sym, "2", date_str, date_str)
            if not data.get("candles"): continue
            
            open_price = data["candles"][0][1]
            if 350 <= open_price <= 650:
                valid_symbols.append(sym)
                
            if len(valid_symbols) >= 50: break
        except:
             pass
             
    return valid_symbols

def simulate_day(date_str, symbols, token):
    trades = []
    
    # 1. Fetch All Data First
    data_map = {}
    for sym in symbols:
        try:
            # print(f"Fetching data for {sym}...")
            data = history.get_history(token, sym, TIMEFRAME, date_str, date_str)
            if data.get("candles"):
                data_map[sym] = {
                    "candles": data["candles"],
                    "rsi": indicators.calculate_rsi(data["candles"]),
                    "state": {'trigger_candle': None, 'trigger_rsi': 0, 'steps': 0},
                    "position": None, # "SHORT"
                    "entry_price": 0,
                    "sl": 0,
                    "is_ce": "CE" in sym
                }
            else:
                 print(f"  Warning: No candles for {sym}. Response: {data.get('message')}")
        except Exception as e:
            print(f"  Error fetching {sym}: {e}")

    if not data_map: return []
    
    # Synchronization: Iterate by Time Index
    # Assuming all have same start time 9:15. Verify lengths?
    # We'll rely on timestamps.
    
    # Get all unique timestamps from first valid symbol
    base_sym = next(iter(data_map))
    timestamps = [c[0] for c in data_map[base_sym]["candles"]]
    
    active_ce_sym = None
    active_pe_sym = None
    
    for i in range(2, len(timestamps)): # Start from index 2
        # Current time check
        # Processing 'i' means we look at completed candle at 'i-1'
        
        # 15:00 Stop
        ts = timestamps[i-1]
        if ts > 9999999999: ts /= 1000
        dt = datetime.datetime.fromtimestamp(ts)
        time_str = dt.strftime("%H:%M")
        if dt.hour >= 15: break

        # Iterate all symbols for this timestamp
        for sym, d in data_map.items():
            candles = d["candles"]
            if i >= len(candles): continue
            
            target_candle = candles[i-1]
            target_rsi = d["rsi"][i-1]
            is_ce = d["is_ce"]
            
            # --- MANAGE EXIT FIRST ---
            if d["position"] == "SHORT":
                current_sl = d["sl"]
                entry_price = d["entry_price"]
                # SL Check (High of current candle 'i-1' vs SL??)
                # Wait, 'target_candle' is the candle that JUST closed.
                # If we were short, did this candle hit SL?
                if target_candle[2] >= current_sl:
                    pnl = entry_price - current_sl
                    trades.append({
                        "Time": time_str,
                        "Symbol": sym,
                        "Side": "SHORT",
                        "Qty": 65,
                        "Entry": entry_price,
                        "ExitTime": time_str,
                        "ExitPrice": current_sl,
                        "PnL": pnl * 65
                    })
                    d["position"] = None
                    # Release Lock
                    if is_ce: active_ce_sym = None
                    else: active_pe_sym = None
                    continue # Trade closed, don't check entry same candle

            # --- CHECK ENTRY (Only if No Active Trade of this Side) ---
            if d["position"] is None:
                # Check Lock
                if is_ce and active_ce_sym is not None: continue
                if not is_ce and active_pe_sym is not None: continue
                
                # Check Signal
                signal, new_state = strategy.check_rsi_signal(target_candle, target_rsi, None, d["state"])
                d["state"] = new_state
                
                if signal.get("action") == "ENTER_SHORT":
                    # ENTRY!
                    d["position"] = "SHORT"
                    d["entry_price"] = target_candle[4] # Close
                    d["sl"] = signal.get("sl")
                    
                    # Set Lock
                    if is_ce: active_ce_sym = sym
                    else: active_pe_sym = sym
                    
                    # Note: We don't log "Trade" yet, only on Exit? 
                    # Or we log entry separate? User wants P&L list.
                    # We append to list only on exit usually, or store partial?
                    # Let's store logic to append on exit.

    # EOD Square Off
    for sym, d in data_map.items():
        if d["position"] == "SHORT":
            # Close at last available price
            last_candle = d["candles"][-1]
            exit_price = last_candle[4]
            pnl = d["entry_price"] - exit_price
            trades.append({
                "Time": "15:00",
                "Symbol": sym,
                "Side": "SHORT",
                "Qty": 65,
                "Entry": d["entry_price"],
                "ExitTime": "15:00",
                "ExitPrice": exit_price,
                "PnL": pnl * 65
            })

    # Sort trades by time
    trades.sort(key=lambda x: x["Time"])
    return trades

def main_run():
    total_cumulative_pnl = 0
    
    # Check if we should include today's existing P&L?
    # User asked "Calculate cumulative PL for all recorded trades" (28, 29, 30 + today verified)
    
    for date_str in DATES:
        print(f"\nProcessing {date_str}...")
        syms = get_valid_option_symbols(date_str, token)
        print(f"  Selected: {syms}")
        
        day_trades = simulate_day(date_str, syms, token)
        
        # Save to CSV
        if day_trades:
            trades_dir = "daily_data/trades"
            os.makedirs(trades_dir, exist_ok=True)
            file_path = os.path.join(trades_dir, f"{date_str}_trades.csv")
            
            day_pnl = sum([t["PnL"] for t in day_trades])
            total_cumulative_pnl += day_pnl
            
            with open(file_path, "w", newline='') as f:
                writer = csv.DictWriter(f, fieldnames=["Time", "Symbol", "Side", "Qty", "Entry", "ExitTime", "ExitPrice", "PnL"])
                writer.writeheader()
                writer.writerows(day_trades)
                
            print(f"  Saved {len(day_trades)} trades. Day P&L: {day_pnl}")
        else:
            print("  No trades generated.")

    # Add Today's (Feb 02) P&L
    try:
        with open("daily_data/trades/2026-02-02_trades.csv", "r") as f:
            reader = csv.DictReader(f)
            today_pnl = sum([float(r["PnL"]) for r in reader])
            total_cumulative_pnl += today_pnl
            print(f"\nToday (2026-02-02) P&L: {today_pnl}")
    except:
        pass
        
    print(f"\n--------------------------------")
    print(f"GRAND TOTAL CUMULATIVE P&L: {total_cumulative_pnl}")
    print(f"--------------------------------")

if __name__ == "__main__":
    main_run()
