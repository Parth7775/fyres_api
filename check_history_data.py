
import history
import datetime

# Access Token
try:
    with open('access_token.txt', 'r') as f:
        ACCESS_TOKEN = f.read().strip()
except:
    print("No token")
    exit()

def check():
    # 1. Check Jan 23 Spot
    print("--- Check Jan 23 Spot ---")
    data = history.get_history(ACCESS_TOKEN, "NSE:NIFTY50-INDEX", "1D", "2026-01-23", "2026-01-23")
    print(data)
    
    # 2. Check Jan 29 Option
    # Spot on Jan 29 was 25418.
    # Check 25000 CE (Deep ITM)
    sym = "NSE:NIFTY2612925000CE"
    print(f"\n--- Check {sym} on Jan 29 ---")
    data = history.get_history(ACCESS_TOKEN, sym, "1D", "2026-01-29", "2026-01-29")
    print(data)

    # 3. Check Jan 29 Option with Feb 3 Expiry? (26203)
    sym2 = "NSE:NIFTY2620325400CE"
    print(f"\n--- Check {sym2} on Jan 29 ---")
    data = history.get_history(ACCESS_TOKEN, sym2, "1D", "2026-01-29", "2026-01-29")
    print(data)

if __name__ == "__main__":
    check()
