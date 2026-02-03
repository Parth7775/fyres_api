
import history
import main
import datetime
import strategy
import indicators

token = main.load_access_token()
symbol = "NSE:NIFTY2620325700PE"
date_str = "2026-01-29"

data = history.get_history(token, symbol, "2", date_str, date_str)
candles = data["candles"]
rsi_values = indicators.calculate_rsi(candles)

print(f"--- Debugging {symbol} on {date_str} ---")

state = {'trigger_candle': None, 'trigger_rsi': 0, 'steps': 0}

for i in range(2, len(candles)):
    target_candle = candles[i-1]
    target_rsi = rsi_values[i-1]
    
    ts = target_candle[0]
    dt = datetime.datetime.fromtimestamp(ts if ts < 9999999999 else ts/1000)
    time_str = dt.strftime("%H:%M")
    
    # Focus around 9:50 - 10:10
    if not (9 <= dt.hour <= 10): continue
    if dt.hour == 9 and dt.minute < 40: continue
    if dt.hour == 10 and dt.minute > 15: continue
    
    print(f"{time_str} | Open: {target_candle[1]} | High: {target_candle[2]} | Low: {target_candle[3]} | Close: {target_candle[4]} | RSI: {target_rsi:.2f}")
    
    signal, new_state = strategy.check_rsi_signal(target_candle, target_rsi, None, state)
    state = new_state
    
    if signal.get("action") != "HOLD":
        print(f"*** SIGNAL: {signal.get('action')} at {time_str} ***")
    
    if state['trigger_candle']:
        trig = state['trigger_candle']
        print(f"    [Trigger Active] Trigger Low: {trig[3]}")
