import datetime




def check_rsi_signal(candle, rsi_value, current_position_side, state):
    """
    Evaluates RSI Strategy for a SINGLE candle with state persistence.
    
    Args:
        candle: [ts, o, h, l, c, v]
        rsi_value: float
        current_position_side: 'LONG', 'SHORT', None
        state: dict {'trigger_candle': ..., 'trigger_rsi': ..., 'steps': ...}
        
    Returns:
        (dict, dict) -> (Action_Dict, Updated_State)
    """
    close = candle[4]
    
    trigger_candle = state.get('trigger_candle')
    
    action = {"action": "HOLD"}
    
    # 1. Manage Existing SHORT
    if current_position_side == "SHORT":
        # Stop Loss Check is handled by Orders/LiveTrader separately usually?
        # But if we need to signal exit logic here:
        pass
        
    # 2. Check Entry (If No Position)
    elif current_position_side is None:
        
        # A. Check Confirmation of Existing Trigger
        if trigger_candle:
            trigger_low = trigger_candle[3]
            trigger_high = trigger_candle[2]
            print(f"STRATEGY DEBUG: Close {close} < Low {trigger_low}?")
            if close < trigger_low:
                # CONFIRMED BREAKDOWN
                action = {
                    "action": "ENTER_SHORT",
                    "sl": trigger_high,
                    "notes": f"Breakdown of Trigger Low {trigger_low}"
                }
                # Consume trigger
                state['trigger_candle'] = None
                state['trigger_rsi'] = 0
                state['steps'] = 0
                return action, state
            
            # If not confirmed, we continue waiting. 
            # (Caller should manage expiry/steps if needed, or we implement steps logic here)
                
        # B. Check for NEW Trigger (RSI > 70)
        if rsi_value > 70:
            # New Trigger found. Replaces old one.
            state['trigger_candle'] = candle
            state['trigger_rsi'] = rsi_value
            state['steps'] = 0
            
    return action, state
