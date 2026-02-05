
import csv
from datetime import datetime

INPUT_FILE = "static/trade_history.csv"
OUTPUT_FILE = "static/trade_history_cleaned.csv"

def parse_time(ts_str):
    try:
        return datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None

def clean_trades():
    with open(INPUT_FILE, 'r') as f:
        reader = list(csv.reader(f))
        
    header = reader[0]
    data_rows = reader[1:]
    
    # Group actions into "Trade Events"
    # We need to link Entries to Exits to define a 'Trade Period'
    # But simpler approach: 
    # Just filter ENTRIES. 
    # If we remove an ENTRY, we must remove its associated EXIT.
    
    # 1. Identify Trades (Symbol, Entry Time, Exit Time)
    # This is tricky because the CSV is a log, not a trade list.
    # We have to parse it linearly.
    
    trades = [] # list of dicts: {'id': i, 'start': dt, 'end': dt, 'side': 'CE/PE', 'rows': [row_indices]}
    
    # We need to track open positions to pair exits
    open_positions = {} # symbol -> trade_obj
    
    # We also need to preserve order and non-trade lines (failures) attached to trades
    
    # Let's map rows to trades
    # We iterate and build 'Trade Objects'.
    # Non-trade rows (failures) attached to an entry time should be grouped with that entry.
    
    all_events = []
    
    # Sort data by timestamp just in case, though usually sorted
    # data_rows.sort(key=lambda x: x[0]) 

    current_open = {} # symbol -> { 'start': dt, 'rows': [], 'side':_ }

    # First Pass: Link Rows to Logical Trades
    # We will identify "Trade Chains".
    rows_to_keep = []
    discard_indices = set()
    
    # We need to process strictly chronologically
    # But multiple symbols can be interleaved.
    
    # Let's organize by Symbol first to pair entries/exits?
    # No, we need global chronology for side constraints.
    
    # Approach:
    # 1. Group rows by Symbol.
    # 2. Within each symbol, pair Entry -> Exit.
    # 3. Create "Trade Intervals" for each symbol.
    # 4. Global sort of all Trade Intervals by Start Time.
    # 5. Filter overlaps.
    # 6. Collect all Row Indices from "Accepted" trades.
    # 7. Write those rows.
    
    symbol_groups = {}
    for i, row in enumerate(data_rows):
        ts = parse_time(row[0])
        sym = row[1]
        action = row[2]
        
        if not ts: continue
        
        if sym not in symbol_groups: symbol_groups[sym] = []
        symbol_groups[sym].append({'idx': i, 'row': row, 'ts': ts, 'action': action})
        
    final_trades = []
    
    for sym, events in symbol_groups.items():
        # Sort events for this symbol
        events.sort(key=lambda x: x['ts'])
        
        i = 0
        while i < len(events):
            e = events[i]
            
            # Identify Start of a Trade
            if 'SELL' in e['action'] or 'ENTRY' in e['action']:
                # Could be a cluster (SELL_FAIL, then SELL)
                # Collect all Start-like events close together
                start_events = [e]
                entry_time = e['ts']
                
                # Check next events for same entry cluster (e.g. SELL_FAIL then SELL same second)
                j = i + 1
                while j < len(events) and (events[j]['ts'] - entry_time).total_seconds() < 2 and ('SELL' in events[j]['action'] or 'ENTRY' in events[j]['action']):
                    start_events.append(events[j])
                    j += 1
                
                # Look for Exit
                exit_time = None
                exit_events = []
                
                k = j
                while k < len(events):
                    if 'EXIT' in events[k]['action']:
                        # Found Exit
                        exit_events.append(events[k])
                        exit_time = events[k]['ts']
                        break # Assume 1 exit closes it
                    k += 1
                
                # If no exit found, it's a RUNNING trade -> End time = Infinity (or now)
                end_time = exit_time if exit_time else datetime.max
                
                side = "CE" if "CE" in sym else "PE"
                
                trade_obj = {
                    'symbol': sym,
                    'side': side,
                    'start': entry_time,
                    'end': end_time,
                    'row_indices': [x['idx'] for x in start_events] + ([x['idx'] for x in exit_events] if exit_events else [])
                }
                final_trades.append(trade_obj)
                
                # Advance i
                if exit_events:
                    i = k + 1 # Skip past exit
                else:
                    i = j # Continue looking (maybe next is another entry? unlikely for same symbol without exit, but possible in buggy logs)
            
            elif 'EXIT' in e['action']:
                # Orphaned exit? Or handled above?
                # If we processed properly, we shouldn't hit standalone exits unless they had no entry.
                # Inspect logic... we jump `i` past exits.
                # So if we hit an EXIT here, it's orphaned. We should probably keep it or discard it? 
                # Better to discard orphaned exits to stay clean.
                i += 1
            else:
                i += 1

    # Now we have all trades. Sort by Start Time.
    final_trades.sort(key=lambda x: x['start'])
    
    # Filter Logic
    accepted_trades = []
    
    last_ce_end = datetime.min
    last_pe_end = datetime.min
    
    print(f"Total Trades Found: {len(final_trades)}")
    
    rows_to_include = set()
    
    for t in final_trades:
        is_overlap = False
        
        if t['side'] == "CE":
            if t['start'] < last_ce_end:
                is_overlap = True
            else:
                last_ce_end = t['end']
        elif t['side'] == "PE":
            if t['start'] < last_pe_end:
                is_overlap = True
            else:
                last_pe_end = t['end']
                
        if is_overlap:
            print(f"Removing Overlap: {t['symbol']} at {t['start']} (Overlaps until {last_ce_end if t['side']=='CE' else last_pe_end})")
        else:
            accepted_trades.append(t)
            for idx in t['row_indices']:
                rows_to_include.add(idx)
                
    # Reconstruct CSV
    # We use the original index to preserve stability
    sorted_indices = sorted(list(rows_to_include))
    
    with open(OUTPUT_FILE, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(header)
        for idx in sorted_indices:
            writer.writerow(data_rows[idx])
            
    print(f"Cleaned CSV written to {OUTPUT_FILE}. Removed {len(final_trades) - len(accepted_trades)} trades.")

if __name__ == "__main__":
    clean_trades()
