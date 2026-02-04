
import csv
import datetime
import os

strikes = [
    "NSE_NIFTY2620325300CE",
    "NSE_NIFTY2620325350CE",
    "NSE_NIFTY2620325400CE"
]

print(f"{'Symbol':<25} | {'Time':<10} | {'Open':<8} | {'High':<8} | {'Low':<8} | {'Close':<8}")
print("-" * 80)

for symbol in strikes:
    file_path = f"daily_data/candles/2026-02-03/{symbol}.csv"
    if not os.path.exists(file_path):
        continue
        
    with open(file_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            ts = int(row['Timestamp'])
            dt = datetime.datetime.fromtimestamp(ts)
            # Filter for 09:20 to 09:40
            if dt.hour == 9 and 20 <= dt.minute <= 40:
                print(f"{symbol:<25} | {dt.strftime('%H:%M:%S'):<10} | {row['Open']:<8} | {row['High']:<8} | {row['Low']:<8} | {row['Close']:<8}")
