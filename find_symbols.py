
import history
import main
import datetime

token = main.load_access_token()

dates = ["26129", "26205", "26JAN", "26FEB"]
strikes = range(25000, 25600, 100)
types = ["CE", "PE"]

found = []

for d in dates:
    for s in strikes:
        for t in types:
            symbol = f"NSE:NIFTY{d}{s}{t}"
            try:
                # Fetch 1 minute candle for Jan 28
                data = history.get_history(token, symbol, "1", "2026-01-28", "2026-01-28")
                if data.get("s") == "ok" and data.get("candles"):
                    print(f"FOUND: {symbol}")
                    found.append(symbol)
                    if len(found) > 5: break 
            except:
                pass
        if len(found) > 5: break
    if len(found) > 5: break

print("Done searching.")
