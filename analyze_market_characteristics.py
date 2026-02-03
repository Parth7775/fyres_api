import history
import indicators
import datetime
import math

stocks_to_compare = [
    "NSE:DIXON-EQ",        # Winner
    "NSE:ADANIGREEN-EQ",   # High Vol Loser
    "NSE:SBIN-EQ",         # High Trend Loser
    "NSE:NIFTYBEES-EQ",    # Index Loser relative to trades
    "NSE:IMFA-EQ"          # Microcap Loser
]

def calculate_efficiency_ratio(candles, period=14):
    """
    Kaufman Efficiency Ratio (ER):
    ER = Change in Price / Sum of individual abs changes
    ER approaches 1.0 for a perfect straight line (clean trend).
    ER approaches 0.0 for pure noise (choppy).
    """
    if len(candles) < period + 1:
        return 0
        
    er_values = []
    
    for i in range(period, len(candles)):
        # Direction: Abs change over period
        start_c = candles[i-period][4]
        end_c = candles[i][4]
        direction = abs(end_c - start_c)
        
        # Volatility: Sum of abs changes
        volatility = 0
        for j in range(i-period+1, i+1):
            curr_c = candles[j][4]
            prev_c = candles[j-1][4]
            volatility += abs(curr_c - prev_c)
            
        if volatility > 0:
            er_values.append(direction / volatility)
        else:
            er_values.append(0)
            
    if not er_values:
        return 0
    return sum(er_values) / len(er_values)

def calculate_atr_percentage(candles, period=14):
    if len(candles) < period + 1:
        return 0
    ratios = []
    for i in range(1, len(candles)):
        curr = candles[i]
        prev = candles[i-1]
        atr = max(curr[2]-curr[3], abs(curr[2]-prev[4]), abs(curr[3]-prev[4]))
        if curr[4] > 0: ratios.append(atr/curr[4])
    if not ratios: return 0
    return (sum(ratios)/len(ratios)) * 100

def analyze_stocks():
    try:
        with open('access_token.txt', 'r') as f:
            access_token = f.read().strip()
    except:
        print("Error reading token")
        return

    # Period: Oct 1 2025 to Nov 30 2025
    date_from, date_to = "2025-10-01", "2025-11-30"
    
    print(f"Analyzing Market Characteristics ({date_from} to {date_to})...\n")
    print(f"{'Stock':<15} | {'ATR %':<8} | {'ADX':<8} | {'Efficiency (Noise)':<15} | {'Verdict'}")
    print("-" * 80)
    
    for symbol in stocks_to_compare:
        try:
            # 1. Daily Data for ATR/ADX
            data_d = history.get_history(access_token, symbol, "1D", date_from, date_to)
            candles_d = data_d.get('candles', [])
            
            if not candles_d: continue
            
            atr_pct = calculate_atr_percentage(candles_d)
            adx_vals = indicators.calculate_adx(candles_d)
            avg_adx = sum(adx_vals)/len(adx_vals) if adx_vals else 0
            
            # 2. Intraday Data (15min) for Efficiency Ratio (Trend Cleanliness)
            # Using 15min to gauge intraday structure
            data_i = history.get_history(access_token, symbol, "15", date_from, date_to)
            candles_i = data_i.get('candles', [])
            
            eff_ratio = calculate_efficiency_ratio(candles_i, period=10)
            
            # Classification
            if atr_pct > 3.0: vol_type = "High"
            elif atr_pct < 1.0: vol_type = "Low"
            else: vol_type = "Med"
            
            if eff_ratio > 0.4: noise = "Clean"
            elif eff_ratio < 0.2: noise = "Noisy"
            else: noise = "Avg"
            
            print(f"{symbol:<15} | {atr_pct:<8.2f} | {avg_adx:<8.2f} | {eff_ratio:<15.3f} ({noise})")
            
        except Exception as e:
            print(f"Error {symbol}: {e}")

if __name__ == "__main__":
    analyze_stocks()
