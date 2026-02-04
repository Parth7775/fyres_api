import datetime
import csv
import os

# Mock Data for Candles
def test_candle_conversion():
    print("Testing Candle Conversion...")
    # [timestamp, open, high, low, close, volume]
    # 1706853600 = 2024-02-02 00:00:00 (approx)
    mock_candles = [
        [1738563000, 100, 110, 90, 105, 5000],
        [1738563120, 105, 115, 100, 110, 6000]
    ]
    
    formatted_candles = []
    for c in mock_candles:
        ts = c[0]
        # Handle ms if needed (fyers usually sends seconds or ms, code checks for > 9999999999)
        if ts > 9999999999: ts /= 1000
        readable_time = datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
        new_row = [readable_time, c[1], c[2], c[3], c[4], c[5]]
        formatted_candles.append(new_row)
        
    for row in formatted_candles:
        print(f"Converted: {row}")
    
    assert formatted_candles[0][0] == "2025-02-03 11:40:00" # Calculated from 1738563000
    print("Candle Conversion PASS")

# Mock Data for Trade Log
def test_trade_consolidation():
    print("\nTesting Trade Consolidation...")
    
    # Raw log entries (Timestamp, Symbol, Action, Price, Qty, Product)
    raw_log = [
        ["2025-02-03 10:00:00", "NSE:NIFTY25FEB23000CE", "SELL", "100", "50", "SIMULATED"],
        ["2025-02-03 10:05:00", "NSE:NIFTY25FEB23000CE", "EXIT_SL", "110", "50", "SIMULATED | PnL: -500.0"],
        ["2025-02-03 11:00:00", "NSE:NIFTY25FEB23000PE", "SELL", "200", "50", "SIMULATED"],
        ["2025-02-03 11:10:00", "NSE:NIFTY25FEB23000PE", "EXIT_MKT", "150", "50", "SIMULATED | PnL: 2500.0"]
    ]
    
    # Process
    trades = [] # dicts
    open_positions = {} # Symbol -> Entry Data
    
    for row in raw_log:
        ts, sym, action, price, qty, product = row
        price = float(price)
        qty = int(qty)
        
        if action == "SELL":
            open_positions[sym] = {
                "entry_time": ts,
                "entry_price": price,
                "qty": qty,
                "side": "SHORT"
            }
        elif "EXIT" in action:
            if sym in open_positions:
                entry = open_positions.pop(sym)
                
                # Extract PnL from Product string or calculate
                pnl = 0.0
                if "PnL:" in product:
                    try:
                        pnl = float(product.split("PnL:")[1].strip())
                    except:
                        pass
                else:
                    # Fallback Calc for Short
                    pnl = (entry["entry_price"] - price) * qty
                    
                trades.append({
                    "Entry Time": entry["entry_time"],
                    "Symbol": sym,
                    "Side": entry["side"],
                    "Qty": qty,
                    "Entry Price": entry["entry_price"],
                    "Exit Time": ts,
                    "Exit Price": price,
                    "PnL": pnl
                })
    
    # Add Cumulative PnL
    cumulative_pnl = 0
    final_rows = []
    
    # Sort by Exit Time
    trades.sort(key=lambda x: x["Exit Time"])
    
    for t in trades:
        cumulative_pnl += t["PnL"]
        t["Cumulative PnL"] = cumulative_pnl
        final_rows.append(t)
        print(f"Trade: {t}")
        
    assert len(final_rows) == 2
    assert final_rows[0]["PnL"] == -500.0
    assert final_rows[0]["Cumulative PnL"] == -500.0
    assert final_rows[1]["PnL"] == 2500.0
    assert final_rows[1]["Cumulative PnL"] == 2000.0
    
    print("Trade Consolidation PASS")

if __name__ == "__main__":
    test_candle_conversion()
    test_trade_consolidation()
