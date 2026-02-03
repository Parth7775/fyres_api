import history
import datetime

try:
    with open('access_token.txt', 'r') as f:
        ACCESS_TOKEN = f.read().strip()
except:
    print("No token")
    exit()

def check(symbol):
    print(f"Checking {symbol}")
    data = history.get_history(ACCESS_TOKEN, symbol, "1D", "2026-01-30", "2026-01-30")
    print(data)

# Test Weekly Feb 5
# Format: NIFTY YY M DD Strike OPT
# 26 2 05 -> 26205
check("NSE:NIFTY2620525300CE") 

# maybe it's 26FEB05 (Usually checks for Month Chars)
check("NSE:NIFTY26FEB0525300CE")

# maybe it's 26205 (Feb 5) but maybe strike 25300 doesn't exist? Try a round one.
check("NSE:NIFTY2620525000CE")

# Try to find Previous Weekly (Jan 29) just to see format
# 26 1 29# User Provided: Feb 3 Expiry?
check("NSE:NIFTY2620325500PE")


# Try to find Previous Weekly (Jan 29) just to see format
# 26 1 29
check("NSE:NIFTY2612925300CE")
check("NSE:NIFTY2612925000CE")

# Try 'O' (Oct), 'N' (Nov) style?
# Feb is 2.
# Maybe '2' is not used for Feb?
# 1,2,3,4,5,6,7,8,9,O,N,D.
# So Feb is 2.

# What if next weekly is NOT Feb 5?
# Today Jan 31 (Sat). Next Thurs Feb 5.
# Is it possible Feb 5 is considered Monthly? No, Monthly is last Thurs (Feb 26).

# Try BankNifty format?
# NSE:BANKNIFTY2620548000CE
check("NSE:NIFTY2612925300CE")
check("NSE:NIFTY2612925000CE")
check("NSE:NIFTY2620425300CE")
check("NSE:NIFTY2620425000CE")
