import datetime
import market_data
import history
import math

def get_nifty_spot(access_token):
    """
    Fetches the latest Nifty 50 Index price.
    Returns float or None.
    """
    symbol = "NSE:NIFTY50-INDEX"
    try:
        # Try getting quote first (faster/lighter)
        quotes = market_data.get_quotes(access_token, symbol)
        if quotes.get('d') and len(quotes['d']) > 0:
            return float(quotes['d'][0]['v']['lp']) # Last Price
            
        # Fallback to history if quote fails (e.g. market closed?)
        today_str = datetime.date.today().strftime("%Y-%m-%d")
        data = history.get_history(access_token, symbol, "1D", today_str, today_str)
        if data.get('candles'):
            return float(data['candles'][-1][4]) # Close
            
    except Exception as e:
        print(f"Error fetching Nifty Spot: {e}")
        
    return None

def get_next_tuesday(current_date):
    """
    Finds the next Tuesday from current_date (including today if it is Tuesday).
    Tuesday is weekday 1.
    """
    days_ahead = 1 - current_date.weekday()
    if days_ahead < 0: # It's Wed-Sun
        days_ahead += 7
    return current_date + datetime.timedelta(days=days_ahead)

def get_expiry_code(expiry_date):
    """
    Converts a date to Fyers Weekly Expiry Code format: YYMDD
    Year: 2 Digits
    Month: 1-9, O, N, D
    Day: 2 Digits
    """
    year = str(expiry_date.year)[2:] # 26
    day = f"{expiry_date.day:02d}"   # 03
    
    month = expiry_date.month
    if month == 10:
        m_str = "O"
    elif month == 11:
        m_str = "N"
    elif month == 12:
        m_str = "D"
    else:
        m_str = str(month)
        
    return f"{year}{m_str}{day}"

def select_best_option(access_token, target_min=400, target_max=600, option_type=None):
    """
    Finds the best option closest to 500 premium.
    option_type: "CE" or "PE". If None, checks both.
    """
    print(f"Selecting Best Option ({option_type if option_type else 'Any'})...")
    
    # 1. Get Spot
    spot = get_nifty_spot(access_token)
    if not spot:
        print("Could not fetch Nifty Spot.")
        return None
        
    print(f"Nifty Spot: {spot}")
    
    # 2. Determine Expiry
    today = datetime.date.today()
    # If today is Tuesday and time is > 3:00 PM, use next week?
    now = datetime.datetime.now()
    if today.weekday() == 1 and now.hour >= 15:
         expiry_date = get_next_tuesday(today + datetime.timedelta(days=1))
    else:
         expiry_date = get_next_tuesday(today)
         
    expiry_code = get_expiry_code(expiry_date)
    print(f"Using Expiry: {expiry_date} (Code: {expiry_code})")
    
    # 3. Generate Candidates
    # Check strikes in a wider range +/- 2000 points
    center_strike = round(spot / 50) * 50
    strikes = []
    for i in range(-40, 41): # +/- 40 steps (*50 = +/-2000 points)
        strikes.append(center_strike + (i * 50))
        
    symbols = []
    for s in strikes:
        if option_type is None or option_type == "CE":
            symbols.append(f"NSE:NIFTY{expiry_code}{s}CE")
        if option_type is None or option_type == "PE":
            symbols.append(f"NSE:NIFTY{expiry_code}{s}PE")
        
    # 4. Fetch Quotes in Batches
    candidates = []
    all_quotes_debug = []
    
    batch_size = 50
    for i in range(0, len(symbols), batch_size):
        batch = symbols[i:i+batch_size]
        batch_str = ",".join(batch)
        
        try:
            q_res = market_data.get_quotes(access_token, batch_str)
            if q_res.get('d'):
                for item in q_res['d']:
                    price = item['v'].get('lp')
                    if price is None: continue
                    sym = item['n']
                    
                    diff = abs(price - 500)
                    item_data = {'symbol': sym, 'price': price, 'diff': diff}
                    all_quotes_debug.append(item_data)
                    
                    if target_min <= price <= target_max:
                        candidates.append(item_data)
        except Exception as e:
            print(f"Error fetching quotes batch: {e}")
            
    # 5. Select Best
    best = None
    if candidates:
        # Sort best candidates by diff
        candidates.sort(key=lambda x: x['diff'])
        best = candidates[0]
        print(f"Found match in range: {best['symbol']} ({best['price']})")
    elif all_quotes_debug:
        print("No options in 400-600 range. Picking closest to 500...")
        all_quotes_debug.sort(key=lambda x: x['diff'])
        best = all_quotes_debug[0]
        print(f"Closest match: {best['symbol']} ({best['price']})")
    else:
        print("No quotes found at all.")
        return None
        
def select_multiple_options(access_token, min_price=350, max_price=650, count_per_type=6):
    """
    Returns a list of CE and PE option symbols within the price range.
    Tries to pick `count_per_type` best matches (closest to middle of range?) or just valid ones.
    """
    print(f"Scanning for options in range {min_price}-{max_price}...")
    
    # 1. Get Spot
    spot = get_nifty_spot(access_token)
    if not spot:
        return []

    # 2. Expiry (Tuesday)
    today = datetime.date.today()
    now = datetime.datetime.now()
    if today.weekday() == 1 and now.hour >= 15:
         expiry_date = get_next_tuesday(today + datetime.timedelta(days=1))
    else:
         expiry_date = get_next_tuesday(today)
         
    expiry_code = get_expiry_code(expiry_date)
    print(f"Spot: {spot} | Expiry: {expiry_code}")
    
    # 3. Generate Wide Range of Candidate Strikes
    # +/- 2000 points covers enough
    center_strike = round(spot / 50) * 50
    strikes = []
    for i in range(-15, 16): 
        strikes.append(center_strike + (i * 50))
        
    symbols_ce = [f"NSE:NIFTY{expiry_code}{s}CE" for s in strikes]
    symbols_pe = [f"NSE:NIFTY{expiry_code}{s}PE" for s in strikes]
    all_symbols = symbols_ce + symbols_pe
    
    # 4. Fetch Quotes
    valid_ce = []
    valid_pe = []
    
    # Helper to check price
    def check_batch(batch):
        try:
            batch_str = ",".join(batch)
            q_res = market_data.get_quotes(access_token, batch_str)
            if q_res.get('d'):
                for item in q_res['d']:
                    price = item['v'].get('lp')
                    if price is None: continue
                    sym = item['n']
                    
                    if min_price <= price <= max_price:
                        # Keep it
                        diff_from_target = abs(price - 500) # Assuming 500 is ideal center
                        
                        if sym.endswith("CE"):
                            valid_ce.append({'symbol': sym, 'price': price, 'diff': diff_from_target})
                        else:
                            valid_pe.append({'symbol': sym, 'price': price, 'diff': diff_from_target})
        except Exception as e:
            print(f"Batch err: {e}")

    # Process CE
    batch_size = 50
    for i in range(0, len(symbols_ce), batch_size):
        check_batch(symbols_ce[i:i+batch_size])
        
    # Process PE
    for i in range(0, len(symbols_pe), batch_size):
        check_batch(symbols_pe[i:i+batch_size])
        
    # Select Best N per type (Closest to 500)
    valid_ce.sort(key=lambda x: x['diff'])
    valid_pe.sort(key=lambda x: x['diff'])
    
    final_list = []
    # CE
    for item in valid_ce[:count_per_type]:
        print(f"Selected CE: {item['symbol']} ({item['price']})")
        final_list.append(item['symbol'])
        
    # PE
    for item in valid_pe[:count_per_type]:
        print(f"Selected PE: {item['symbol']} ({item['price']})")
        final_list.append(item['symbol'])
        
    return final_list
