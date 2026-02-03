
import history
import indicators
import strategy
import datetime
import main


def verify_symbol(symbol, token):
    print(f"\n--- Verifying {symbol} ---")
    today = datetime.date.today().strftime("%Y-%m-%d")
    # Fetch data
    data = history.get_history(token, symbol, "2", today, today)
    
    if not data.get("candles"):
        print("No candle data found.")
        return

    candles = data["candles"]
    rsi_values = indicators.calculate_rsi(candles, period=14)
    
    # Simulate Strategy
    # State tracking
    state = {'trigger_candle': None, 'trigger_rsi': 0, 'steps': 0}
    current_position = None
    current_sl = 0
    entry_price = 0
    trades = []
    
    print(f"Total Candles: {len(candles)}")
    
    for i in range(2, len(candles)):
        # Simulate "Live" loop where we check the completed candle (i-1)
        # In live trader: target_candle = candles[-2] (completed)
        
        target_index = i - 1 
        target_candle = candles[target_index]
        target_rsi = rsi_values[target_index]
        
        ts = target_candle[0]
        if ts > 9999999999: ts /= 1000
        dt = datetime.datetime.fromtimestamp(ts)
        time_str = dt.strftime("%H:%M")
        
        print(f"DEBUG: {time_str} | RSI: {target_rsi:.2f} | Pos: {current_position} | Trig: {state.get('trigger_rsi')}")

        
        # STOP LOGIC AT 15:00 (Market Close for our strategy)
        if dt.hour >= 15:
             break

        # 1. Manage Existing Position (SL Check)
        if current_position == "SHORT":
            if target_candle[2] >= current_sl:
                pnl = entry_price - current_sl
                print(f"EXIT SL: {time_str} | Price: {current_sl} | PnL: {pnl:.2f}")
                trades.append({
                    "time": time_str,
                    "price": current_sl,
                    "type": "EXIT_SL",
                    "pnl": pnl
                })
                current_position = None
            else:
                 pass # Holding

        # 2. Check Signal (Only if No Position)
        if current_position is None:
            eff_side = current_position
            signal, new_state = strategy.check_rsi_signal(target_candle, target_rsi, eff_side, state)
            state = new_state
            
            action = signal.get("action")
            
            # Print Action if it's not HOLD
            if action != "HOLD":
                 print(f"DEBUG: Signal Received at {time_str}: {action}")

            if action == "ENTER_SHORT":
                current_sl = signal.get("sl") # High of trigger candle
                entry_price = target_candle[4] # Close
                
                print(f"TRADE SIGNAL (ENTRY): {time_str} | Price: {entry_price} | SL: {current_sl} | RSI: {target_rsi:.2f}")
                current_position = "SHORT"
                trades.append({
                    "time": time_str,
                    "price": entry_price,
                    "type": "SELL",
                    "sl": current_sl
                })

    # End of Day Square Off
    if current_position == "SHORT":
         last_close = candles[-1][4]
         ts = candles[-1][0]
         if ts > 9999999999: ts /= 1000
         dt = datetime.datetime.fromtimestamp(ts)
         pnl = entry_price - last_close
         print(f"EXIT MKT: {dt.strftime('%H:%M')} | Price: {last_close} | PnL: {pnl:.2f}")
         trades.append({
             "time": dt.strftime('%H:%M'),
             "price": last_close,
             "type": "EXIT_MKT",
             "pnl": pnl
         })
         
    total_points = sum([t.get('pnl', 0) for t in trades])
    total_pnl_inr = total_points * 65
    print(f"Total Points for {symbol}: {total_points:.2f}")
    print(f"Total P&L (Lot 65) for {symbol}: ₹ {total_pnl_inr:.2f}\n")
    return total_pnl_inr

token = main.load_access_token()
pnl1 = verify_symbol("NSE:NIFTY2620325200PE", token)
pnl2 = verify_symbol("NSE:NIFTY2620324400CE", token)

print(f"--- CUMULATIVE P&L ---")
print(f"Gross P&L: ₹ {((pnl1 or 0) + (pnl2 or 0)):.2f}")
