import history
import strategy
import indicators
import datetime
import logging
import sys

# Setup logging to stdout
logging.basicConfig(level=logging.INFO, format='%(message)s')

# Authenticate
try:
    with open('access_token.txt', 'r') as f:
        token = f.read().strip()
except:
    print("No access token")
    sys.exit(1)

today = datetime.date.today().strftime("%Y-%m-%d")
from_date = (datetime.date.today() - datetime.timedelta(days=5)).strftime("%Y-%m-%d")

expiry_str = "26210" # Feb 10
strikes = [26150, 26200, 26250, 26300, 26350, 26400]

print(f"DEBUG: Checking PE Strikes {strikes} (Expiry {expiry_str}) for {today} (with history from {from_date})")

for strike in strikes:
    sym = f"NSE:NIFTY{expiry_str}{strike}PE"
    
    # Fetch Data with Warm-up
    d = history.get_history(token, sym, "2", from_date, today) 
    if not d or not d.get('candles'):
        print(f"Skipping {sym} (No Data)")
        continue
        
    candles = d['candles']
    if not candles: continue

    # Calculate RSI
    rsi_values = indicators.calculate_rsi(candles, period=14)
    
    state = {'trigger_candle': None, 'trigger_rsi': 0, 'steps': 0}
    
    print(f"\nAnalyzing {sym}")
    
    found_today = False
    
    for i in range(len(candles)):
        c = candles[i]
        rsi = rsi_values[i]
        
        ts = c[0]
        if ts > 9999999999: ts /= 1000
        dt = datetime.datetime.fromtimestamp(ts)
        t_str = dt.strftime("%H:%M")
        date_str = dt.strftime("%Y-%m-%d")
        
        if date_str != today:
            continue
            
        found_today = True

        # Capture Trigger State BEFORE processing
        had_trigger = state.get('trigger_candle') is not None
        trigger_price = state.get('trigger_candle')[3] if had_trigger else 0
        
        signal, new_state = strategy.check_rsi_signal(c, rsi, None, state)
        state = new_state
        
        # Focus on 09:15 to 09:35
        if "09:15" <= t_str <= "09:35":
            trigger_info = f"[Trig: Low {trigger_price} (RSI {state.get('trigger_rsi',0):.2f})]" if had_trigger else ""
            print(f"  {t_str} | Close: {c[4]} | RSI: {rsi:.2f} {trigger_info}")
            
            if signal.get("action") == "ENTER_SHORT":
                print(f"  >>> ENTRY SIGNAL at {t_str} (Price: {c[4]}, SL: {signal.get('sl')})")
