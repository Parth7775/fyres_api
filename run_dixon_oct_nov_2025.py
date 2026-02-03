import history
import indicators
import strategy
import datetime
import calendar

# 1. Setup
try:
    with open('access_token.txt', 'r') as f:
        access_token = f.read().strip()
except FileNotFoundError:
    print("Error: access_token.txt not found")
    exit(1)

symbol = "NSE:DIXON-EQ"
resolution = "3" # 3 Minute candles

all_candles = []

# Range: Oct 1, 2025 to Nov 30, 2025
ranges = [
    ("2025-10-01", "2025-10-31"),
    ("2025-11-01", "2025-11-30")
]

print(f"Fetching data for {symbol} from Oct 1, 2025 to Nov 30, 2025...")

# 2. Fetch Data
for date_from, date_to in ranges:
    print(f"Fetching {date_from} to {date_to}...")
    
    try:
        data = history.get_history(
            access_token=access_token,
            symbol=symbol,
            resolution=resolution,
            range_from=date_from,
            range_to=date_to
        )
        
        if data.get('s') == 'ok':
            candles = data.get('candles', [])
            all_candles.extend(candles)
            print(f"  Fetched {len(candles)} candles.")
        else:
            print(f"  API Error for {date_from}: {data}")
            
    except Exception as e:
        print(f"  Error fetching data: {e}")

print(f"Total Fetched Candles: {len(all_candles)}")

if not all_candles:
    print("No candles found.")
    exit(0)

# 3. Calculate VWAP
vwap_values = indicators.calculate_vwap(all_candles)

# 4. Run Strategy
trades = strategy.backtest_vwap_strategy(all_candles, vwap_values)

# 5. Output Results
print("\n--- TRADES ---")
print(f"{'ID':<5} | {'Time':<20} | {'Action':<15} | {'Price':<10} | {'PnL':<10} | {'Notes'}")
total_pnl = 0
for trade in trades:
    pnl_val = trade.get('pnl', 0)
    print(f"{trade['id']:<5} | {trade['timestamp']:<20} | {trade['action']:<15} | {trade['price']:<10.2f} | {pnl_val:<10.2f} | {trade['notes']}")
    total_pnl += pnl_val

print("\n--- SUMMARY ---")
print(f"Total Trades: {len(trades)}")
print(f"Total Cumulative PnL: {total_pnl:.2f}")
