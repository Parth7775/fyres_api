
import history
import main

token = main.load_access_token()

# Search wide range of strikes for Jan
for s in range(24000, 26000, 100):
    sym = f"NSE:NIFTY26JAN{s}CE"
    try:
        data = history.get_history(token, sym, "1", "2026-01-28", "2026-01-28")
        if data.get("s") == "ok" and data.get("candles"):
            print(f"FOUND JAN: {sym}")
            break
    except:
        pass

# Check Feb 05 Weekly
for s in range(24000, 26000, 100):
    sym = f"NSE:NIFTY26205{s}CE"
    try:
        data = history.get_history(token, sym, "1", "2026-01-30", "2026-01-30")
        if data.get("s") == "ok" and data.get("candles"):
            print(f"FOUND FEB05: {sym}")
            break
    except:
        pass
