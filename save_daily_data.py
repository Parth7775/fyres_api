
import os
import csv
import datetime
import history
import main

def save_daily_data():
    today_str = "2026-02-02"
    
    # 1. Save Trades
    trades_dir = "daily_data/trades"
    os.makedirs(trades_dir, exist_ok=True)
    
    trades_file = os.path.join(trades_dir, f"{today_str}_trades.csv")
    
    # Verified Trades Data (Corrected)
    trades = [
        {"Time": "11:27", "Symbol": "NSE:NIFTY2620325200PE", "Side": "SHORT", "Qty": 65, "Entry": 495.00, "ExitTime": "15:01", "ExitPrice": 177.60, "PnL": 20631.00},
        {"Time": "11:49", "Symbol": "NSE:NIFTY2620324400CE", "Side": "SHORT", "Qty": 65, "Entry": 477.45, "ExitTime": "12:13", "ExitPrice": 500.00, "PnL": -1465.75},
        {"Time": "12:21", "Symbol": "NSE:NIFTY2620324400CE", "Side": "SHORT", "Qty": 65, "Entry": 499.60, "ExitTime": "12:57", "ExitPrice": 541.65, "PnL": -2733.25},
        {"Time": "13:13", "Symbol": "NSE:NIFTY2620324400CE", "Side": "SHORT", "Qty": 65, "Entry": 557.20, "ExitTime": "13:43", "ExitPrice": 579.00, "PnL": -1417.00}
    ]
    
    # Calculate Cumulative PnL
    cumulative_pnl = 0.0
    for t in trades:
        cumulative_pnl += t["PnL"]
        t["Cumulative PnL"] = cumulative_pnl

    with open(trades_file, "w", newline='') as f:
        writer = csv.DictWriter(f, fieldnames=["Time", "Symbol", "Side", "Qty", "Entry", "ExitTime", "ExitPrice", "PnL", "Cumulative PnL"])
        writer.writeheader()
        writer.writerows(trades)
        
    print(f"Saved Trades to {trades_file}")
    
    # 2. Save Candles
    candles_base_dir = "daily_data/candles"
    day_candle_dir = os.path.join(candles_base_dir, today_str)
    os.makedirs(day_candle_dir, exist_ok=True)
    
    token = main.load_access_token()
    symbols = ["NSE:NIFTY2620325200PE", "NSE:NIFTY2620324400CE"]
    
    for sym in symbols:
        print(f"Fetching candles for {sym}...")
        data = history.get_history(token, sym, "2", today_str, today_str)
        candles = data.get("candles", [])
        
        if candles:
            safe_sym = sym.replace(":", "_")
            file_path = os.path.join(day_candle_dir, f"{safe_sym}.csv")
            
            with open(file_path, "w", newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["Timestamp", "Open", "High", "Low", "Close", "Volume"])
                for c in candles:
                    # Format Timestamp
                    ts = c[0]
                    if ts > 9999999999: ts /= 1000
                    readable_time = datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
                    row = [readable_time, c[1], c[2], c[3], c[4], c[5]]
                    writer.writerow(row)
            print(f"Saved {len(candles)} candles to {file_path}")
        else:
            print(f"No candles found for {sym}")

if __name__ == "__main__":
    save_daily_data()
