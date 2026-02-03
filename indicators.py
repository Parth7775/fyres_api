from datetime import datetime

def calculate_adx(candles, period=14):
    """
    Calculates the Average Directional Index (ADX) for a list of candles.
    
    Args:
        candles (list): List of candles [timestamp, open, high, low, close, volume].
        period (int): Lookback period (default 14).
        
    Returns:
        list: A list of ADX values corresponding to the candles.
              The first '2 * period - 1' values will be 0 or inaccurate until smoothed.
    """
    if len(candles) < 2 * period:
        return [0] * len(candles)
        
    highs = [c[2] for c in candles]
    lows = [c[3] for c in candles]
    closes = [c[4] for c in candles]
    
    tr_list = []
    dm_plus_list = []
    dm_minus_list = []
    
    # 1. Calculate TR, +DM, -DM
    for i in range(1, len(candles)):
        h = highs[i]
        l = lows[i]
        prev_c = closes[i-1]
        
        tr = max(h - l, abs(h - prev_c), abs(l - prev_c))
        
        up_move = h - highs[i-1]
        down_move = lows[i-1] - l
        
        if up_move > down_move and up_move > 0:
            dm_plus = up_move
        else:
            dm_plus = 0
            
        if down_move > up_move and down_move > 0:
            dm_minus = down_move
        else:
            dm_minus = 0
            
        tr_list.append(tr)
        dm_plus_list.append(dm_plus)
        dm_minus_list.append(dm_minus)
        
    # 2. Smooth Values (Wilder's Smoothing)
    # First value is simple sum
    tr14 = sum(tr_list[:period])
    dm14_plus = sum(dm_plus_list[:period])
    dm14_minus = sum(dm_minus_list[:period])
    
    smooth_tr = [tr14]
    smooth_dm_plus = [dm14_plus]
    smooth_dm_minus = [dm14_minus]
    
    for i in range(period, len(tr_list)):
        curr_tr = tr_list[i]
        curr_dm_plus = dm_plus_list[i]
        curr_dm_minus = dm_minus_list[i]
        
        prev_tr = smooth_tr[-1]
        prev_dm_plus = smooth_dm_plus[-1]
        prev_dm_minus = smooth_dm_minus[-1]
        
        # Wilder's Smoothing: Prev - (Prev/N) + Curr
        next_tr = prev_tr - (prev_tr / period) + curr_tr
        next_dm_plus = prev_dm_plus - (prev_dm_plus / period) + curr_dm_plus
        next_dm_minus = prev_dm_minus - (prev_dm_minus / period) + curr_dm_minus
        
        smooth_tr.append(next_tr)
        smooth_dm_plus.append(next_dm_plus)
        smooth_dm_minus.append(next_dm_minus)
        
    # 3. Calculate DX and ADX
    dx_list = []
    for i in range(len(smooth_tr)):
        di_plus = (smooth_dm_plus[i] / smooth_tr[i]) * 100 if smooth_tr[i] != 0 else 0
        di_minus = (smooth_dm_minus[i] / smooth_tr[i]) * 100 if smooth_tr[i] != 0 else 0
        
        di_sum = di_plus + di_minus
        di_diff = abs(di_plus - di_minus)
        
        dx = (di_diff / di_sum) * 100 if di_sum != 0 else 0
        dx_list.append(dx)
        
    # First ADX is average of first 'period' DX values
    if len(dx_list) < period:
        # Should not happen given initial checks, but safe fallback
        return [0] * len(candles)
        
    adx_start = sum(dx_list[:period]) / period
    adx_values_smooth = [adx_start]
    
    for i in range(period, len(dx_list)):
        curr_dx = dx_list[i]
        prev_adx = adx_values_smooth[-1]
        
        # Smooth ADX: ((Prev * (N-1)) + Curr) / N
        next_adx = ((prev_adx * (period - 1)) + curr_dx) / period
        adx_values_smooth.append(next_adx)
        
    # Pad result to match candles length
    # We lost 1 index at start (diff), then 'period' for smoothing, then 'period' for ADX smoothing
    # Total offset is roughly 2*period
    # We will align the final ADX values to the end of the list
    
    final_adx = [0] * (len(candles) - len(adx_values_smooth)) + adx_values_smooth
    return final_adx

def calculate_rsi(candles, period=14):
    """
    Calculates the Relative Strength Index (RSI) for a list of candles.
    
    Args:
        candles (list): List of candles [timestamp, open, high, low, close, volume].
        period (int): Lookback period (default 14).
        
    Returns:
        list: A list of RSI values corresponding to the candles.
              The first 'period' values will be None or 0.
    """
    if len(candles) < period + 1:
        return [0] * len(candles)
        
    closes = [c[4] for c in candles]
    
    gains = []
    losses = []
    
    # Calculate changes
    for i in range(1, len(closes)):
        change = closes[i] - closes[i-1]
        if change > 0:
            gains.append(change)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(abs(change))
            
    # First Average Gain/Loss
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    
    rsi_list = [0] * period # Pad initial values
    
    if avg_loss == 0:
        rsi_list.append(100)
    else:
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        rsi_list.append(rsi)
        
    # Smooth subsequent values
    for i in range(period, len(gains)):
        current_gain = gains[i]
        current_loss = losses[i]
        
        avg_gain = ((avg_gain * (period - 1)) + current_gain) / period
        avg_loss = ((avg_loss * (period - 1)) + current_loss) / period
        
        if avg_loss == 0:
            rsi = 100
        else:
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
            
        rsi_list.append(rsi)
        
    return rsi_list

