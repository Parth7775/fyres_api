import history
import datetime

def test_symbol(sym):
    print(f"Testing {sym}...")
    try:
        with open('access_token.txt', 'r') as f:
            token = f.read().strip()
            
        # Get 1 day history
        today = datetime.date.today().strftime("%Y-%m-%d")
        data = history.get_history(token, sym, "1D", "2026-01-30", "2026-01-30")
        
        if data.get('s') == 'ok' and data.get('candles'):
            print(f"SUCCESS: {sym} exists. Close: {data['candles'][-1][4]}")
            return True
        else:
            print(f"FAIL: {data}")
            return False
    except Exception as e:
        print(f"Error: {e}")
        return False

# Weekly Feb 5: 26205 (Expected)
test_symbol("NSE:NIFTY2620525000CE")

# Monthly Feb: 26FEB
test_symbol("NSE:NIFTY26FEB25000CE")

# Weekly Feb 12: 26212
test_symbol("NSE:NIFTY2621225000CE")

# Wrong formatted?
test_symbol("NSE:NIFTY2620525000CE")
