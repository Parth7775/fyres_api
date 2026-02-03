import strategy
import csv
import datetime

def verify_strategy():
    # Load CSV
    csv_file = "gold_petal_data.csv"
    candles = []
    vwap_values = []
    
    try:
        with open(csv_file, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                dt_str = row['timestamp']
                dt_obj = datetime.datetime.strptime(dt_str, '%Y-%m-%d %H:%M:%S')
                ts = dt_obj.timestamp()
                
                # [ts, o, h, l, c, v]
                candle = [
                    ts, 
                    float(row['open']), 
                    float(row['high']), 
                    float(row['low']), 
                    float(row['close']), 
                    float(row['volume'])
                ]
                candles.append(candle)
                vwap_values.append(float(row['vwap']))
                
    except FileNotFoundError:
        print("CSV not found. Please run fetch_gold_petal.py first.")
        return

    print(f"Loaded {len(candles)} candles.")

    # Run Strategy
    trades = strategy.backtest_vwap_strategy(candles, vwap_values, start_index=1)
    
    # Output Trades
    print(f"{'TIME':<20} {'ACTION':<15} {'PRICE':<10} {'PNL':<10} {'NOTES'}")
    print("-" * 80)
    
    total_realized_pnl = 0.0
    
    for t in trades:
        pnl_str = f"{t.get('pnl', 0):.2f}" if 'pnl' in t else "-"
        if 'pnl' in t:
            total_realized_pnl += t['pnl']
        print(f"{t['timestamp']:<20} {t['action']:<15} {t['price']:<10.2f} {pnl_str:<10} {t['notes']}")
    
    print("-" * 80)
    print(f"Total Realized P&L: {total_realized_pnl:.2f}")
    
    # Check Running Trade
    if trades:
        last_trade = trades[-1]
        if "ENTER" in last_trade['action']:
            # Currently in a position
            entry_price = last_trade['price']
            entry_type = "LONG" if "LONG" in last_trade['action'] else "SHORT"
            
            # Get latest market price (last candle close)
            last_candle = candles[-1]
            current_price = last_candle[4]
            current_time = datetime.datetime.fromtimestamp(last_candle[0]).strftime('%Y-%m-%d %H:%M:%S')
            
            if entry_type == "LONG":
                unrealized_pnl = current_price - entry_price
            else:
                unrealized_pnl = entry_price - current_price
            
            print("\n=== CURRENT RUNNING TRADE ===")
            print(f"Type: {entry_type}")
            print(f"Entry Time: {last_trade['timestamp']}")
            print(f"Entry Price: {entry_price:.2f}")
            print(f"Current Price: {current_price:.2f} (at {current_time})")
            print(f"Unrealized P&L: {unrealized_pnl:.2f}")
        else:
             print("\nNo Running Trade (Flat).")

if __name__ == "__main__":
    verify_strategy()
