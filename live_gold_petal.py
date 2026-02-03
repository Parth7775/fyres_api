import history
import datetime
import time
import os

def fetch_and_update():
    try:
        # Read access token
        with open("access_token.txt", "r") as f:
            access_token = f.read().strip()
    except Exception as e:
        print(f"Error reading access token: {e}")
        return

    symbol = "MCX:GOLDPETAL26FEBFUT"
    csv_filename = "gold_petal_data.csv"

    while True:
        try:
            today = datetime.date.today().strftime("%Y-%m-%d")
            
            # Fetch 3 minute data
            data = history.get_history(
                access_token=access_token,
                symbol=symbol,
                resolution="3",
                range_from=today,
                range_to=today,
                date_format=1,
                cont_flag=1
            )
            
            if data.get('s') == 'ok':
                candles = data.get('candles', [])
                
                if candles:
                    # Calculate VWAP
                    cum_pv = 0.0
                    cum_vol = 0.0
                    csv_data = []
                    
                    for c in candles:
                        ts, open_p, high, low, close, vol = c[0], c[1], c[2], c[3], c[4], c[5]
                        
                        typical_price = (high + low + close) / 3
                        pv = typical_price * vol
                        
                        cum_pv += pv
                        cum_vol += vol
                        
                        if cum_vol > 0:
                            vwap = cum_pv / cum_vol
                        else:
                            vwap = 0
                        
                        dt = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
                        csv_data.append([dt, open_p, high, low, close, vol, vwap])
                    
                    # Update CSV (Atomic write mostly, but simple write here)
                    # To be safe, maybe write to temp and rename, but simple write is fine for now
                    with open(csv_filename, "w") as f:
                        f.write("timestamp,open,high,low,close,volume,vwap\n")
                        for row in csv_data:
                            f.write(f"{row[0]},{row[1]},{row[2]},{row[3]},{row[4]},{row[5]},{row[6]:.2f}\n")
                    
                    last_candle = csv_data[-1]
                    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] Updated {csv_filename}. {len(candles)} candles. Last Clos: {last_candle[4]}, VWAP: {last_candle[6]:.2f}")
                else:
                    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] No candles data received.")
            else:
                print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] API Error: {data}")
        
        except Exception as e:
            print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] Exception: {e}")
            
        time.sleep(60) # Wait for 1 minute

if __name__ == "__main__":
    print("Starting Live Gold Petal Data Polling...")
    fetch_and_update()
