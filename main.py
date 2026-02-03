import auth
import config
import os
import json
import market_data
import history
import indicators
import orders
import csv
import strategy
from datetime import date, timedelta, datetime

ACCESS_TOKEN_FILE = "access_token.txt"

def load_access_token():
    if os.path.exists(ACCESS_TOKEN_FILE):
        with open(ACCESS_TOKEN_FILE, "r") as f:
            return f.read().strip()
    return None

def save_access_token(token):
    with open(ACCESS_TOKEN_FILE, "w") as f:
        f.write(token)

def main():
    print("Checking for existing access token...")
    access_token = load_access_token()
    
    if not access_token:
        print("No access token found. Initiating login...")
        login_url = auth.get_login_url()
        print(f"Please visit this URL to login:\n{login_url}")
        
        # Optionally open in browser
        # import webbrowser
        # webbrowser.open(login_url)
        
        auth_code = input("\nEnter the auth code from the redirect URL: ").strip()
        
        try:
            print("Generating access token...")
            access_token = auth.generate_access_token(auth_code)
            save_access_token(access_token)
            print("Access token saved successfully.")
        except Exception as e:
            print(f"Error generating token: {e}")
            return

    print("Verifying connection...")
    try:
        profile = auth.get_profile(access_token)
        print("User Profile:")
        print(json.dumps(profile, indent=2))
        
        if profile.get("s") == "error":
             print("Error fetching profile. Token might be expired.")
        else:
            print("\nFetching Quotes for NSE:SBIN-EQ and NSE:HDFC-EQ...")
            quotes = market_data.get_quotes(access_token, "NSE:SBIN-EQ,NSE:HDFC-EQ")
            
            # Format Quote Timestamps
            if quotes.get("d"):
                for q in quotes["d"]:
                    if "v" in q and "tt" in q["v"]:
                        try:
                            ts = int(q["v"]["tt"])
                            # Check if timestamp is in seconds or milliseconds
                            if ts > 9999999999: ts /= 1000
                            q["v"]["tt_formatted"] = datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
                        except ValueError:
                            pass # Skip if timestamp is not a valid number
            
            print(json.dumps(quotes, indent=2))

            print("\nFetching 3-minute candles for NSE:DIXON-EQ (Today)...")
            today = date.today()
            # Set range_from to today to get data only for the current day
            
            candles = history.get_history(
                access_token=access_token,
                symbol="NSE:DIXON-EQ",
                resolution="3",
                range_from=today.strftime("%Y-%m-%d"),
                range_to=today.strftime("%Y-%m-%d")
            )
            
            if candles.get("candles"):
                # Calculate VWAP
                vwap_values = indicators.calculate_vwap(candles["candles"])
                
                print(f"\nCandle Data (Resolution: 3 min) - showing all candles for Today:")
                print(f"{'Timestamp':<25} {'Open':<10} {'High':<10} {'Low':<10} {'Close':<10} {'Volume':<10} {'VWAP':<10}")
                print("-" * 90)
                
                # Get all candles and their corresponding VWAP values
                last_candles = candles["candles"]
                last_vwap = vwap_values
                
                for i, candle in enumerate(last_candles):
                    ts = candle[0]
                    # History API usually returns seconds for resolution < 1D, but let's be safe
                    if ts > 9999999999: ts /= 1000
                    ts_str = datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
                    
                    vwap = last_vwap[i]
                    
                    print(f"{ts_str:<25} {candle[1]:<10} {candle[2]:<10} {candle[3]:<10} {candle[4]:<10} {candle[5]:<10} {vwap:<10.2f}")

                # Check for Strategy Signals (Backtest Mode)
                print("\n" + "="*50)
                print("STRATEGY TRADE LOG (Stateful Backtest)")
                print("="*50)
                trades = strategy.backtest_vwap_strategy(last_candles, last_vwap, start_index=2)
                
                if trades:
                    print(f"{'Time':<20} {'Action':<15} {'Price':<10} {'SL/PnL':<10} {'Notes'}")
                    print("-" * 75)
                    for trade in trades:
                        # Format Price/SL/PnL
                        price_str = f"{trade['price']:.2f}"
                        if 'sl' in trade:
                            extra_str = f"SL: {trade['sl']:.2f}"
                        elif 'pnl' in trade:
                             extra_str = f"PnL: {trade['pnl']:.2f}"
                        else:
                            extra_str = "-"
                            
                        print(f"{trade['timestamp']:<20} {trade['action']:<15} {price_str:<10} {extra_str:<10} {trade.get('notes', '')}")
                else:
                    print("No Trades triggered for today (after 09:21).")

                # Export to CSV for analysis
                csv_filename = "vwap_data.csv"
                print(f"\nExporting detailed data to {csv_filename}...")
                
                with open(csv_filename, mode='w', newline='') as file:
                    writer = csv.writer(file)
                    # Header with detailed calculation fields
                    writer.writerow(["Timestamp", "Open", "High", "Low", "Close", "Volume", "Typical_Price", "PV", "Cum_PV", "Cum_Vol", "VWAP"])
                    
                    # Re-calculate step-by-step for CSV to verify logic
                    cum_vol = 0
                    cum_pv = 0
                    
                    for candle in candles["candles"]:
                        ts, o, h, l, c, v = candle
                        
                        # Timestamp formatting
                        if ts > 9999999999: ts /= 1000
                        ts_str = datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
                        
                        # VWAP Calculation Components
                        tp = (h + l + c) / 3
                        pv = tp * v
                        cum_vol += v
                        cum_pv += pv
                        vwap_calc = cum_pv / cum_vol if cum_vol > 0 else 0
                        
                        writer.writerow([
                            ts_str, o, h, l, c, v, 
                            f"{tp:.2f}", f"{pv:.2f}", f"{cum_pv:.2f}", f"{cum_vol}", 
                            f"{vwap_calc:.2f}"
                        ])
                
                print("Export complete. Please check the CSV file to compare candle data with your chart.")

            else:
                print("No candle data found or error in response.")
                print(candles)

    except Exception as e:
        print(f"Error fetching profile: {e}")

if __name__ == "__main__":
    main()
