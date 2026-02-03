import datetime
import time
import history
import indicators
import orders


# Access Token Handling
try:
    with open('access_token.txt', 'r') as f:
        ACCESS_TOKEN = f.read().strip()
except FileNotFoundError:
    print("Error: access_token.txt not found. Please authenticate.")
    exit()

def get_nifty_spot(date_str):
    """Fetches the latest Nifty 50 Index price for a given date."""
    symbol = "NSE:NIFTY50-INDEX"
    
    # We need just the latest price, let's fetch 1 day 1 minute to get close
    # Or just use quotes if available. History is safer for now.
    data = history.get_history(
        access_token=ACCESS_TOKEN,
        symbol=symbol,
        resolution="1D", 
        range_from=date_str,
        range_to=date_str
    )
    
    if data.get('s') == 'ok' and data.get('candles'):
        last_candle = data['candles'][-1]
        return last_candle[4] # Close price
    return None

def find_options_with_price(spot_price, check_date, price_min=400, price_max=600):
    strike_center = round(spot_price / 50) * 50
    strikes_to_check = []
    for i in range(-15, 16): 
        strikes_to_check.append(strike_center + (i * 50))
        
    found_data = [] # (symbol, price, type)
    
    # Valid Weekly Expiry provided by user: Feb 3 (26203)
    # TODO: Expiry might change for previous days? 
    # Usually we trade current expiry. 
    # If checking last 5 days (Jan 23-30), Jan 23 might have traded Jan 29 expiry?
    # Or Feb 03?
    # Let's Stick to the provided Expiry "26203" for now unless user specified otherwise.
    # Actually, Jan 29 Expiry probably existed. "26129"? (Jan 29). 
    # 26 (Year) 1 (Jan) 29.
    
    # Let's assume we use "26203" for Jan 30 (Fri). And maybe Jan 29 (Thu)?
    # If date is <= Jan 29, maybe use Jan 29 Expiry "26129" or Feb 05?
    # Wait, Feb 03 is odd. Monthly is Usually last Thursday. Jan 29 was likely Monthly Expiry.
    # So for Jan 23-29, we should probably look at "26129".
    # For Jan 30, we look at "26205" (Feb 5) or "26203"? 
    # User showed "26203". Maybe slightly custom.
    
    # Let's just use "26203" if it works, or check context.
    # But if I search "26203" options on Jan 23, they might be illiquid.
    
    # Let's try to detect valid expiry or just use a fixed list for this specific user request.
    first_check_expiry = "26203"
    # Fallback/Alternatives could be checked but sticking to known working one.
    expiry_str = first_check_expiry
    
    # if check_date <= "2026-01-29":
    #      expiry_str = "26129" # INVALID
         
    print(f"Scanning {expiry_str} strikes around {strike_center} for {check_date}...")
    
    for strike in strikes_to_check:
        for opt_type in ["CE", "PE"]:
            symbol = f"NSE:NIFTY{expiry_str}{strike}{opt_type}"
            data = history.get_history(ACCESS_TOKEN, symbol, "1D", check_date, check_date)
            if data.get('s') == 'ok' and data.get('candles'):
                close_price = data['candles'][-1][4]
                if price_max >= close_price >= price_min:
                    found_data.append({'symbol': symbol, 'price': close_price, 'type': opt_type})
    
    return found_data


def run_rsi_strategy(symbol, date_str):
    """
    Runs the RSI strategy on a specific symbol for a specific date.
    Returns the daily P&L.
    """
    print(f"\\nRunning Strategy on {symbol} for {date_str}")
    
    # 1. Fetch Data with Warm-up
    # We need previous candles to calculate RSI(14) correctly for the first candle of the day.
    # Fetching 5 days prior to be safe (inc weekends)
    target_date_obj = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
    from_date_obj = target_date_obj - datetime.timedelta(days=5)
    from_date_str = from_date_obj.strftime("%Y-%m-%d")
    
    print(f"Fetching data from {from_date_str} to {date_str} for warm-up...")
    
    data = history.get_history(
        access_token=ACCESS_TOKEN,
        symbol=symbol,
        resolution="2", # 2 minute resolution
        range_from=from_date_str,
        range_to=date_str
    )
    
    if data.get('s') != 'ok':
        print(f"Error fetching data for {symbol}")
        return 0

    candles = data['candles']
    # candles = [ts, o, h, l, c, v]
    
    # 2. Calculate RSI on FULL data
    rsi_values = indicators.calculate_rsi(candles, period=14)
    
    # 3. Find Start Index for Target Date
    # We only want to trade the target date, but use previous data for Recalculation
    start_index = -1
    for i, c in enumerate(candles):
        c_ts = c[0]
        c_dt = datetime.datetime.fromtimestamp(c_ts if c_ts < 9999999999 else c_ts/1000)
        if c_dt.date() >= target_date_obj:
            start_index = i
            break
            
    if start_index == -1:
        print(f"No data found for target date {date_str}")
        return 0
        
    # Ensure start_index is at least 14 for RSI
    if start_index < 14:
        print("Warning: Not enough warm-up data for accurate RSI. Trading might be affected.")

    # 4. Iterate (Start from trading day)
    # Need to keep track of state
    position = None # 'SHORT'
    entry_price = 0
    stop_loss = 0
    trades = []
    
    # Trigger State
    trigger_candle = None
    trigger_index = -1
    
    current_date_candles = candles[start_index:]
    print(f"Processing trading day starting at index {start_index} ({len(current_date_candles)} candles)...")
    
    for i in range(start_index, len(candles)):
        current_candle = candles[i]
        curr_ts = current_candle[0]
        dt = datetime.datetime.fromtimestamp(curr_ts if curr_ts < 9999999999 else curr_ts/1000)
        curr_time = dt.time()
        
        curr_rsi = rsi_values[i]
        curr_open = current_candle[1]
        curr_high = current_candle[2]
        curr_low = current_candle[3]
        curr_close = current_candle[4]
        
        # 3 PM Exit
        if curr_time >= datetime.time(15, 0):
            if position == 'SHORT':
                pnl = entry_price - curr_close
                trades.append({
                    "time": curr_time,
                    "type": "EXIT_TIME",
                    "price": curr_close,
                    "pnl": pnl
                })
                position = None
            break # End of day
            
        # If In Position
        if position == 'SHORT':
            # Check Stop Loss
            if curr_close >= stop_loss: # Hit SL
                pnl = entry_price - curr_close # Negative
                trades.append({
                    "time": curr_time,
                    "type": "EXIT_SL",
                    "price": curr_close,
                    "pnl": pnl
                })
                position = None
            continue 
        
        # Trigger Logic & Confirmation Check
        
        prev_rsi = rsi_values[i-1]
        
        entered_this_step = False
        
        # Priority 1: Check Entry (Regardless of current RSI)
        # Verify if we have a valid trigger from previous steps
        if position is None and trigger_candle is not None:
             steps_since_trigger = i - trigger_index
             
             if 1 <= steps_since_trigger <= 2:
                # Check Confirmation
                trigger_low = trigger_candle[3]
                if current_candle[4] < trigger_low:
                     # Valid Entry
                     entry_price = current_candle[4]
                     # Stop Loss is High of Trigger Candle
                     stop_loss = trigger_candle[2]
                     
                     position = 'SHORT'
                     trades.append({
                         "time": curr_time,
                         "type": "ENTRY_SHORT",
                         "price": entry_price,
                         "sl": stop_loss,
                         "trigger_rsi": rsi_values[trigger_index],
                         "confirmed_at_step": steps_since_trigger
                     })
                     entered_this_step = True
                     trigger_candle = None # Consumed
             
             elif steps_since_trigger > 2:
                # Expired trigger
                # Don't clear here yet, just don't enter. 
                # Actually if step > 2, it's invalid.
                # But we might set a new trigger below.
                if not (curr_rsi > 70): # Only clear if we aren't about to set a new one?
                    trigger_candle = None
                else:
                    pass # Will be overwritten below

        # Priority 2: Update Trigger (if RSI > 70)
        # Any candle with RSI > 70 becomes the new trigger.
        # IF we didn't just enter.
        if not entered_this_step:
            if curr_rsi > 70:
                if position is None:
                    # Update Trigger
                    trigger_candle = current_candle
                    trigger_index = i

    # Print Results
    daily_pnl = 0
    if not trades:
        print(f"No trades for {symbol}")
    else:
        for t in trades:
            print(t)
            if 'pnl' in t:
                daily_pnl += t['pnl']
                
    return daily_pnl

if __name__ == "__main__":
    # Backtest Days
    dates = ["2026-01-30", "2026-01-29", "2026-01-28", "2026-01-27", "2026-01-23"]
    # holidays = Jan 26. Jan 24/25 weekend.
    
    total_pnl = 0
    
    for d in dates:
        print(f"\n{'='*40}")
        print(f"Running for Date: {d}")
        print(f"{'='*40}")
        
        spot = get_nifty_spot(d)
        if spot:
            print(f"Nifty Spot: {spot}")
            options = find_options_with_price(spot, d)
            
            # Select closest to 500
            target_price = 500
            best_ce = None; best_ce_diff = 9999
            best_pe = None; best_pe_diff = 9999
            
            for opt in options:
                diff = abs(opt['price'] - target_price)
                if opt['type'] == 'CE':
                    if diff < best_ce_diff: best_ce_diff = diff; best_ce = opt
                elif opt['type'] == 'PE':
                    if diff < best_pe_diff: best_pe_diff = diff; best_pe = opt
            
            selected_symbols = []
            if best_ce:
                print(f"Selected Call: {best_ce['symbol']} @ {best_ce['price']}")
                selected_symbols.append(best_ce['symbol'])
            if best_pe:
                print(f"Selected Put: {best_pe['symbol']} @ {best_pe['price']}")
                selected_symbols.append(best_pe['symbol'])
                
            for sym in selected_symbols:
                pnl = run_rsi_strategy(sym, d)
                if pnl:
                    total_pnl += pnl
        
    print(f"\nTotal P&L over 5 days: {total_pnl}")

