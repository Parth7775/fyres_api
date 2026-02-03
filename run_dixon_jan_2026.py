import history
import indicators
import strategy
import datetime

# 1. Setup
try:
    with open('access_token.txt', 'r') as f:
        access_token = f.read().strip()
except FileNotFoundError:
    print("Error: access_token.txt not found")
    exit(1)

symbol = "NSE:DIXON-EQ"
resolution = "3"
date_from = "2026-01-01"
date_to = "2026-01-31"

print(f"Fetching data for {symbol} from {date_from} to {date_to}...")

# 2. Fetch Data
try:
    data = history.get_history(
        access_token=access_token,
        symbol=symbol,
        resolution=resolution,
        range_from=date_from,
        range_to=date_to
    )
except Exception as e:
    print(f"Error fetching data: {e}")
    exit(1)

if data.get('s') != 'ok':
    print(f"API Error: {data}")
    exit(1)

candles = data.get('candles', [])
print(f"Fetched {len(candles)} candles.")

if not candles:
    print("No candles found.")
    exit(0)

# 3. Calculate VWAP
# candles format from Fyers history is [timestamp, open, high, low, close, volume]
# indicators.calculate_vwap expects the same
vwap_values = indicators.calculate_vwap(candles)

# 4. Run Strategy
trades = strategy.backtest_vwap_strategy(candles, vwap_values)

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
