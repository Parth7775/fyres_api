
def check_restriction(paper_positions, target_sym):
    print(f"\nChecking trade for {target_sym}...")
    
    # Logic copied from live_trader.py for testing
    already_open = any(p['symbol'] == target_sym and p.get('isOpen', True) for p in paper_positions)
    if already_open:
        print("Result: BLOCKED (Duplicate)")
        return

    target_type = "CE" if "CE" in target_sym else "PE"
    same_side_open = any(
        (target_type in p['symbol']) and p.get('isOpen', True) 
        for p in paper_positions
    )
    if same_side_open:
         print(f"Result: BLOCKED ({target_type} already open)")
    else:
         print("Result: ALLOWED")

# Test Cases
print("--- TEST SUITE ---")

# Case 1: Existing CE Open, Try New CE -> Should Block
positions_1 = [{'symbol': 'NSE:NIFTY24FEB24000CE', 'isOpen': True}]
print("Context: One CE Open")
check_restriction(positions_1, "NSE:NIFTY24FEB24100CE") 

# Case 2: Existing CE Open, Try New PE -> Should Allow
print("Context: One CE Open")
check_restriction(positions_1, "NSE:NIFTY24FEB24000PE")

# Case 3: Existing PE Open, Try New PE -> Should Block
positions_2 = [{'symbol': 'NSE:NIFTY24FEB24000PE', 'isOpen': True}]
print("Context: One PE Open")
check_restriction(positions_2, "NSE:NIFTY24FEB24100PE")

# Case 4: No Positions -> Should Allow
print("Context: Empty")
check_restriction([], "NSE:NIFTY24FEB24000CE")
