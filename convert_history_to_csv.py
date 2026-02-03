
import csv
import re
import datetime
import os
import ast

INPUT_FILE = "last_5_days_trades.txt"
OUTPUT_FILE = "static/trade_history.csv"

def parse_txt_to_csv():
    print(f"Reading from {INPUT_FILE}...")
    
    if not os.path.exists(INPUT_FILE):
        print(f"Error: {INPUT_FILE} not found.")
        return

    # specific mappings
    # We need to track the current date context from the file
    current_date = None
    current_symbol = None
    
    # regex patterns
    date_pattern = re.compile(r"Running for Date: (\d{4}-\d{2}-\d{2})")
    symbol_pattern = re.compile(r"Running Strategy on (NSE:\S+) for")
    dict_pattern = re.compile(r"({'time':.*})")
    
    trades_to_add = []

    with open(INPUT_FILE, "r") as f:
        lines = f.readlines()
        
    for line in lines:
        line = line.strip()
        
        # Check Date
        m_date = date_pattern.search(line)
        if m_date:
            current_date = m_date.group(1)
            # print(f"Context Date: {current_date}")
            continue
            
        # Check Symbol
        m_sym = symbol_pattern.search(line)
        if m_sym:
            current_symbol = m_sym.group(1)
            # print(f"Context Symbol: {current_symbol}")
            continue
            
        # Check Trade Dict
        m_dict = dict_pattern.search(line)
        if m_dict:
            try:
                # safe parsing of dict string
                # The string has "datetime.time(13, 47)" which is not valid JSON
                # We need to handle that.
                raw_dict_str = m_dict.group(1)
                
                # Replace datetime.time(H, M) with a string representation or similar
                # Regex to find datetime.time(h, m)
                # This is a bit hacky but works for the known format
                
                # Replace "datetime.time(13, 47)" -> "'13:47:00'"
                # Use a regex sub
                def time_replacer(match):
                    h = match.group(1)
                    m = match.group(2)
                    return f"'{int(h):02d}:{int(m):02d}:00'"
                
                clean_str = re.sub(r"datetime\.time\((\d+),\s*(\d+)\)", time_replacer, raw_dict_str)
                
                data = ast.literal_eval(clean_str)
                
                # Now construct CSV Row
                # CSV Format: Timestamp,Symbol,Action,Price,Qty,Product
                
                # Construct proper timestamp: Date + Time
                if current_date and 'time' in data:
                    full_ts = f"{current_date} {data['time']}"
                else:
                    full_ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                action = data.get('type', 'UNKNOWN')
                price = data.get('price', 0)
                qty = 65 # Hardcoded based on known strategy qty, or we can assume 1 lot
                
                # PnL or SL info in Product column
                info = []
                if 'pnl' in data:
                    info.append(f"PnL: {data['pnl']}")
                if 'sl' in data:
                    info.append(f"SL: {data['sl']}")
                if 'trigger_rsi' in data:
                    info.append(f"RSI: {data['trigger_rsi']:.2f}")
                    
                product_str = "BACKTEST"
                if info:
                    product_str += " | " + " | ".join(info)

                trades_to_add.append({
                    "Timestamp": full_ts,
                    "Symbol": current_symbol if current_symbol else "UNKNOWN",
                    "Action": action,
                    "Price": price,
                    "Qty": qty,
                    "Product": product_str
                })
                
            except Exception as e:
                print(f"Failed to parse line: {line} -> {e}")

    print(f"Found {len(trades_to_add)} trades to add.")
    
    # Append to CSV
    # Check existing to avoid dupes?
    existing_keys = set()
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Key: Timestamp + Symbol
                key = f"{row['Timestamp']}_{row['Symbol']}_{row['Action']}"
                existing_keys.add(key)
    else:
        # Create header
        with open(OUTPUT_FILE, "w") as f:
            f.write("Timestamp,Symbol,Action,Price,Qty,Product\n")

    added_count = 0
    with open(OUTPUT_FILE, "a") as f:
        # writer = csv.DictWriter(f, fieldnames=["Timestamp","Symbol","Action","Price","Qty","Product"])
        # writer not used blindly to ensure format matches exact custom CSV style if needed
        # but standard csv module is fine.
        
        for t in trades_to_add:
            key = f"{t['Timestamp']}_{t['Symbol']}_{t['Action']}"
            if key not in existing_keys:
                # Write line
                line = f"{t['Timestamp']},{t['Symbol']},{t['Action']},{t['Price']},{t['Qty']},{t['Product']}\n"
                f.write(line)
                added_count += 1
                
    print(f"Successfully added {added_count} new trades to {OUTPUT_FILE}.")

if __name__ == "__main__":
    parse_txt_to_csv()
