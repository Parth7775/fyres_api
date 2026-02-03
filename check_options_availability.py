import history

def check_options():
    try:
        with open('access_token.txt', 'r') as f:
            access_token = f.read().strip()
    except FileNotFoundError:
        print("Error: access_token.txt not found")
        return

    # Try to find a valid expired option symbol
    # Nifty Spot in Jan 2025 was around 23500-24000
    # Format guesses for Monthly Expiry (assuming Jan 30 2025 expiry?)
    # NSE:NIFTY25JAN24000CE
    
    symbols_to_check = [
        "NSE:NIFTY25JAN24000CE", # Monthly
        "NSE:NIFTY25JAN23500PE",
        "NSE:NIFTY25FEB24000CE"
    ]
    
    print("Checking availability of expired 2025 Options...")
    
    for sym in symbols_to_check:
        print(f"\nChecking {sym}...")
        try:
            # Check for data in Jan 2025
            data = history.get_history(
                access_token=access_token,
                symbol=sym,
                resolution="1D",
                range_from="2025-01-15",
                range_to="2025-01-25"
            )
            
            if data.get('s') == 'ok':
                candles = data.get('candles', [])
                if candles:
                    print(f"SUCCESS: Found {len(candles)} candles.")
                    print(f"Sample: {candles[0]}")
                else:
                    print("EMPTY: No candles returned.")
            else:
                print(f"FAILED: {data.get('message', 'Unknown error')}")
                
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    check_options()
