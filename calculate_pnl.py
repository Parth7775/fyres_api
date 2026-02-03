
import history
import main
import datetime

def get_candle_data(token, symbol):
    today = datetime.date.today().strftime("%Y-%m-%d")
    data = history.get_history(token, symbol, "2", today, today)
    return data.get("candles", [])

def simulate_trade(candles, entry_time_str, trade_type="SHORT", symbol=""):
    # entry_time_str e.g. "11:27"
    # match candle with start time corresponding to entry? 
    # Usually entry is at Close of candle ending at Time, or Open of candle starting at Time?
    # User said "11:27am". 2 min candles: 11:26-11:28? Or 11:24-11:26?
    # Let's assume Entry Price is the OPEN of the candle starting at specified time (or CLOSE of prev).
    # Let's align with the provided time being the ENTRY execution.
    
    entry_index = -1
    entry_price = 0
    sl_price = 0
    
    # helper to parse time
    def parse_time(ts):
        if ts > 9999999999: ts /= 1000
        return datetime.datetime.fromtimestamp(ts)

    # Find Entry Candle
    for i, c in enumerate(candles):
        dt = parse_time(c[0])
        t_str = dt.strftime("%H:%M")
        
        # We look for candle starting at or just before provided time?
        # If user says 11:27, likely the 11:26 candle (covering 11:26-11:28)?
        # Let's try to find exact match or closest.
        
        # 11:27 is odd. 2m candles are 11:26, 11:28.
        # So 11:27 is inside 11:26 candle.
        if t_str == entry_time_str or (int(t_str.split(':')[1]) == int(entry_time_str.split(':')[1]) - 1):
             # This is a bit fuzzy, let's just look for the candle covering the time.
             pass
    
    # Better approach: Iterate and check time >= entry_time
    target_start_dt = datetime.datetime.strptime(f"{datetime.date.today()} {entry_time_str}", "%Y-%m-%d %H:%M")
    
    found_entry = False
    
    pnl = 0
    exit_reason = "HOLD"
    exit_time = ""
    exit_price = 0
    
    for i in range(len(candles)):
        c = candles[i]
        dt = parse_time(c[0])
        
        # STOP at 15:00 for Intra-Day Square Off
        if dt.hour >= 15:
             exit_price = c[1] # Open of 15:00 candle? Or Close of last? Let's use Open of 15:00 as exit.
             exit_reason = "EXIT_TIME"
             exit_time = dt.strftime("%H:%M")
             if found_entry:
                 pnl = entry_price - exit_price # Short PnL
                 break
        
        if not found_entry:
            # Check if this is the start of the trade
            # Allow 1-2 min variance
            delta = (dt - target_start_dt).total_seconds()
            if -120 <= delta <= 120:
                # FOUND ENTRY
                found_entry = True
                entry_index = i
                entry_price = c[4] # UPDATED: Entry at Candle CLOSE
                
                # SL Setup: High of PREVIOUS candle (Signal Candle) is strict strategy. 
                # Or High of THIS candle? Strategy says "SL = Candle High" of Signal Candle.
                # Signal Candle is usually i-1.
                if i > 0:
                    sl_price = candles[i-1][2] # High of previous
                else:
                    sl_price = c[2] + 10 # Fallback
                
                print(f"ENTRY (CLOSE): {symbol} at {dt.strftime('%H:%M')} | Price: {entry_price} | SL: {sl_price}")
        else:
            # Manage Trade
            # Check SL (High of current candle >= SL)
            if c[2] >= sl_price:
                exit_price = sl_price
                exit_reason = "EXIT_SL"
                exit_time = dt.strftime("%H:%M")
                pnl = entry_price - exit_price
                break
                
    if found_entry and exit_reason == "HOLD":
        # Market Close at end of data if not 15:00 yet?
        last_c = candles[-1]
        exit_price = last_c[4] # Close
        exit_reason = "EXIT_MKT"
        exit_time = parse_time(last_c[0]).strftime("%H:%M")
        pnl = entry_price - exit_price

    if not found_entry:
        print(f"ERROR: Could not find entry for {symbol} at {entry_time_str}")
        return 0

    print(f"EXIT: {exit_reason} at {exit_time} | Price: {exit_price} | PnL: {pnl:.2f}")
    return pnl

token = main.load_access_token()

trades = [
    ("NSE:NIFTY2620325200PE", "11:27"),
    ("NSE:NIFTY2620324400CE", "11:49"),
    ("NSE:NIFTY2620324400CE", "12:21"),
    ("NSE:NIFTY2620324400CE", "13:13")
]

total_pnl = 0

print("\n--- CALCULATING P&L (Lot Size 65) ---")
for sym, time in trades:
    candles = get_candle_data(token, sym)
    pts = simulate_trade(candles, time, "SHORT", sym)
    
    # If duplicate trades overlap, this simple sum assumes they are separate accounts or adds. 
    # User asked for 'cumulative', implying sum of all.
    total_pnl += pts

print(f"\nTotal Points: {total_pnl:.2f}")
print(f"Total P&L (INR): ₹ {total_pnl * 65:.2f}")
