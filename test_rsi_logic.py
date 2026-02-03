
import indicators
import datetime
from rsi_nifty_strategy import run_rsi_strategy 

def verify_logic():
    print("Verifying RSI Logic...")
    
    def make_candle(ts, price):
        return [ts, price, price+2, price-2, price, 1000]

    base_ts = 1600000000
    
    # helper
    def simulate_test(scenario_name, rsi_sequence, price_sequence, expect_trade=False):
        print(f"\n--- {scenario_name} ---")
        
        # We need to construct candies that produce the RSI sequence approx
        # Or simpler: Just inject the RSI values directly into the function?
        # The function calculates RSI from candles.
        # It's hard to reverse engineer candles for exact RSI.
        
        # Alternative: We can mock the 'indicators.calculate_rsi' function.
        # But we are running 'simulate_continuous_logic' which takes rsi_values as input!
        # So we can just feed whatever RSI values we want.
        
        candles = []
        for i in range(len(price_sequence)):
            candles.append(make_candle(base_ts + (i*60), price_sequence[i]))
            
        # We pad RSI values 
        rsi_values = []
        if len(rsi_sequence) < len(price_sequence):
            rsi_values = [50] * (len(price_sequence) - len(rsi_sequence)) + rsi_sequence
        else:
            rsi_values = rsi_sequence
            
        simulate_continuous_logic(candles, rsi_values, scenario_name)

    # ---------------------------------------------------------
    # Scenario 3: High RSI but Valid Breakdown
    # ---------------------------------------------------------
    # Index 14: RSI 80. Price 100. (Trigger)
    # Index 15: RSI 75. Price 95. (Breakdown < 98).
    # Expect: ENTRY.
    
    prices = [100] * 14 + [100, 95]
    rsi_vals = [50] * 14 + [80, 75] 
    # Note: index 14 is 15th element.
    # We loop from 14.
    
    simulate_test("Scenario 3: High RSI Breakdown", rsi_vals, prices, expect_trade=True)


def simulate_continuous_logic(candles, rsi_values, name):
    print(f"Simulating {name}...")
    position = None
    trigger_candle = None
    trigger_index = -1
    
    trades = []
    
    for i in range(14, len(candles)):
        current_candle = candles[i]
        curr_rsi = rsi_values[i]
        prev_rsi = rsi_values[i-1]
        dt = datetime.datetime.fromtimestamp(current_candle[0])
        curr_time = dt.time()
        
        entered_this_step = False
        
        # Priority 1: Check Entry
        if position is None and trigger_candle is not None:
             steps_since_trigger = i - trigger_index
             
             if 1 <= steps_since_trigger <= 2:
                trigger_low = trigger_candle[3]
                if current_candle[4] < trigger_low:
                     print(f"  [TRADE] ENTRY at Index {i} (Step {steps_since_trigger}). RSI {curr_rsi:.2f}. Price {current_candle[4]} < TrigLow {trigger_low}")
                     position = 'SHORT'
                     trades.append(i)
                     entered_this_step = True
                     trigger_candle = None
             
             elif steps_since_trigger > 2:
                # Expired trigger check
                if not (curr_rsi > 70):
                    print(f"  [INFO] Index {i}: Trigger Expired (Step {steps_since_trigger}). RSI {curr_rsi:.2f}")
                    trigger_candle = None
                else:
                    pass 

        # Priority 2: Update Trigger
        if not entered_this_step:
            if curr_rsi > 70:
                if position is None:
                    trigger_candle = current_candle
                    trigger_index = i
                    print(f"  [UPD] Trigger Updated to Index {i} (RSI {curr_rsi:.2f}). Low: {trigger_candle[3]}")
    
    if not trades:
        print("  Result: NO TRADES")
    else:
        print(f"  Result: {len(trades)} TRADES")

if __name__ == "__main__":
    verify_logic()
