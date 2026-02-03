import ssl
# --- SSL CERTIFICATE FIX FOR MACOS ---
try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    pass
else:
    ssl._create_default_https_context = _create_unverified_https_context
    if hasattr(ssl, 'create_default_context'):
        ssl.create_default_context = _create_unverified_https_context
# -------------------------------------

import time
import datetime
import logging
import json
import traceback
import threading
import ssl
import os
import csv
import ssl
import concurrent.futures
from fyers_apiv3.FyersWebsocket.data_ws import FyersDataSocket



# Import our modules
import history
import indicators
import strategy
import portfolio
import orders
import config
import option_selector
import market_data
import json

# Configure Logging
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler("live_trading.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("LiveTrader")

# GLOBAL VARIABLES
LTP_CACHE = {} # {symbol: ltp}
GLOBAL_SCAN_RESULTS = []
GLOBAL_BEST_CE = None
GLOBAL_BEST_PE = None

TRADE_LOCK = threading.Lock() # Thread Safety

# GLOBAL SETTINGS
TIMEFRAME = "2" # 2 Minute candles for RSI
QTY = 65
DRY_RUN = False  # Set to False to place real orders
SLEEP_INTERVAL = 1.0 # Reduced frequency to avoid Rate Limits

# REAL-TIME DATA STATE
SOCKET_CONNECTED = False

def get_token():
    """Reads access token from file directly."""
    try:
        with open("access_token.txt", "r") as f:
            return f.read().strip()
    except Exception as e:
        logger.error(f"Error reading access_token.txt: {e}")
        return None

# Initialize Symbols
tokens = get_token()
TRADING_INSTRUMENTS = []

logger.info("Auto-Selecting Multiple CE/PE Options (Range 350-650)...")
logger.info("Auto-Selecting Multiple CE/PE Options (Range 350-650)...")

for attempt in range(3):
    try:
        selected_symbols = option_selector.select_multiple_options(tokens, min_price=350, max_price=650, count_per_type=6)
        if selected_symbols:
            break
        logger.warning(f"Selection Attempt {attempt+1} returned no symbols. Retrying...")
    except Exception as e:
        logger.error(f"Selection Error: {e}")
    time.sleep(2)

TRADING_INSTRUMENTS = []
if selected_symbols:
    for sym in selected_symbols:
        # Determine Type
        opt_type = "CE" if "CE" in sym else "PE"
        TRADING_INSTRUMENTS.append({
            "symbol": sym,
            "type": opt_type,
            "state": {'trigger_candle': None, 'trigger_rsi': 0, 'steps': 0}
        })
        logger.info(f"Monitoring {opt_type}: {sym}")
else:
    logger.critical("FAILED TO SELECT ANY OPTIONS after retries. Manual Intervention Required.")
    # fallback to a hardcoded generic ATM if absolutely needed, but safer to do nothing.
    # TRADING_INSTRUMENTS = [] (Empty list means no trading)
    pass

def get_position_from_cache(all_positions, symbol):
    """
    Parses cached position list.
    """
    if isinstance(all_positions, list):
        for p in all_positions:
            if p.get('symbol') == symbol:
                net_qty = int(p.get('netQty', 0))
                if net_qty > 0:
                    return "LONG", net_qty
                elif net_qty < 0:
                    return "SHORT", net_qty
    return None, 0

GLOBAL_SCAN_RESULTS = []
GLOBAL_BEST_CE = None
GLOBAL_BEST_PE = None

def onmessage(message):
    global LTP_CACHE
    # logger.info(f"Socket Response: {message}") # Very verbose
    if message.get('type') == 'cn' and message.get('s') == 'ok':
         # Connection established
         pass
    
    if message.get('symbol') and message.get('ltp'):
        # Single Ticks ? Fyers v3 socket usually sends a list or dict
        pass

def on_data_handler(message):
    """
    Custom data handler for FyersDataSocket
    """
    global LTP_CACHE
    # message is list of dicts: [{'symbol': '...', 'ltp': ...}, ...]
    try:
        pass
    except:
        pass

# -----------------
# FAST LANE EXECUTION REMOVED (Strict Close Logic Enforced)
# -----------------

# WEBSOCKET HELPERS
def fyers_socket_running(access_token, symbols_list):
    def on_message(message):
        global LTP_CACHE
        # logger.info(f"Tick: {message}")
        if isinstance(message, dict) and 'symbol' in message and 'ltp' in message:
             sym = message['symbol']
             ltp_val = message['ltp']
             LTP_CACHE[sym] = ltp_val
             # FAST LANE DISABLED
             
        elif isinstance(message, list):
            for m in message:
                if 'symbol' in m and 'ltp' in m:
                    sym = m['symbol']
                    ltp_val = m['ltp']
                    LTP_CACHE[sym] = ltp_val
                    # FAST LANE DISABLED

    def on_error(message):
        logger.error(f"Socket Error: {message}")

    def on_close(message):
        logger.warning(f"Socket Closed: {message}")

    def on_open():
        logger.info("Socket Connection Opened")

    # Create Socket
    # symbol format: ["NSE:NIFTY2620324400CE", ...]
    # data_type="SymbolUpdate"
    
    fyers = FyersDataSocket(
        access_token=access_token,
        log_path=".",
        litemode=False, # Full Mode for potentially faster/unthrottled TBT
        write_to_file=False,
        reconnect=True,
        on_connect=on_open,
        on_close=on_close,
        on_error=on_error,
        on_message=on_message
    )
    
    fyers.connect()
    fyers.subscribe(symbols=symbols_list, data_type="SymbolUpdate")
    
def start_websocket_thread(token, symbols):
    t = threading.Thread(target=fyers_socket_running, args=(token, symbols))
    t.daemon = True
    t.start()
    logger.info("WebSocket Thread Started")

def log_trade_csv(symbol, action, price, qty, product_type):
    """Logs trade to CSV for historical monitoring."""
    try:
        # Sanitize product_type to prevent commas breaking CSV
        safe_product = str(product_type).replace(",", " |")
        
        file_exists = False
        try:
            with open("static/trade_history.csv", "r") as f:
                file_exists = True
        except FileNotFoundError:
            pass
            
        with open("static/trade_history.csv", "a") as f:
            if not file_exists:
                f.write("Timestamp,Symbol,Action,Price,Qty,Product\n")
            
            ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"{ts},{symbol},{action},{price},{qty},{safe_product}\n")
    except Exception as e:
        logger.error(f"Failed to log to CSV: {e}")

def json_updater_loop():
    """
    Updates algo_status.json every 1 second with latest LTPs
    """
    global GLOBAL_SCAN_RESULTS, GLOBAL_BEST_CE, GLOBAL_BEST_PE, LTP_CACHE
    while True:
        try:
            # Update API Status JSON
            if GLOBAL_SCAN_RESULTS:
                # Update LTPs in Scan Results
                for item in GLOBAL_SCAN_RESULTS:
                    sym = item['symbol']
                    if sym in LTP_CACHE:
                        item['ltp'] = LTP_CACHE[sym] # Update Live Price
            
            status_data = {
                "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "scan_results": GLOBAL_SCAN_RESULTS,
                "active_ce": GLOBAL_BEST_CE,
                "active_pe": GLOBAL_BEST_PE
            }
            
            with open("static/algo_status.json", "w") as f:
                json.dump(status_data, f)
                    
        except Exception as e:
            # logger.error(f"JSON Update Error: {e}")
            pass
            
        time.sleep(1.0) # Update memory almost instantly (1Hz sufficient for UI)

def start_json_updater():
    t = threading.Thread(target=json_updater_loop)
    t.daemon = True
    t.start()
    logger.info("JSON Updater Thread Started")


def run_trading_loop():
    global GLOBAL_SCAN_RESULTS, GLOBAL_BEST_CE, GLOBAL_BEST_PE
    logger.info(f"Starting RSI Algo Trader for {len(TRADING_INSTRUMENTS)} Instruments")
    logger.info(f"Timeframe: {TIMEFRAME}m | DRY RUN: {DRY_RUN} | Strict Close Mode")
    
    token = get_token()
    if not token:
        logger.error("No access token found. Please login via main.py first.")
        return

    # Initialize Paper Positions
    paper_positions = []
    try:
        with open("static/paper_positions.json", "r") as f:
            paper_positions = json.load(f)
    except:
        paper_positions = []
        
    # Start Real-Time Data Socket
    all_symbols = [i['symbol'] for i in TRADING_INSTRUMENTS]
    start_websocket_thread(token, all_symbols)
    start_json_updater()

    # Reuse Executor for Performance (Avoids setup overhead)
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=20)
    
    # --- HISTORY DATA INITIALIZATION ---
    history_map = {}
    last_history_full_update = 0
    
    def fetch_process(inst):
        sym = inst['symbol']
        today = datetime.date.today()
        from_date = today - datetime.timedelta(days=5)
        try:
            # logger.info(f"Fetching {sym}...")
            d = history.get_history(token, sym, TIMEFRAME, from_date.strftime("%Y-%m-%d"), today.strftime("%Y-%m-%d"))
            return sym, d
        except Exception as e:
            logger.error(f"Async Fetch Error {sym}: {e}")
            return sym, {}

    logger.info("Initializing History Data (This may take a few seconds)...")
    futures = [executor.submit(fetch_process, inst) for inst in TRADING_INSTRUMENTS]
    for future in concurrent.futures.as_completed(futures):
        s, d = future.result()
        if d: history_map[s] = d
    logger.info("History Data Initialized.")
    last_history_full_update = time.time()
    # -----------------------------------

    while True:
        try:
            now = datetime.datetime.now()
            
            # 1. Market Hours Check (9:15 to 15:30)
            # 1. Market Hours Check (9:15 to 15:00)
            if now.hour < 9 or (now.hour == 9 and now.minute < 15):
                logger.info("Market not open yet. Waiting...")
                time.sleep(60)
                continue
            if now.hour >= 15 and now.minute >= 0:
                logger.info("Market closed (3:00 PM). Auto-Closing Open Positions.")
                
                # A. Auto-Close PAPER Positions
                for p_pos in paper_positions:
                    if p_pos.get('isOpen', True):
                        symbol = p_pos['symbol']
                        close_price = LTP_CACHE.get(symbol, p_pos['ltp'])
                        p_pos['isOpen'] = False
                        p_pos['exitPrice'] = close_price
                        p_pos['exitTime'] = now.strftime("%H:%M:%S")
                        
                        # Calculate final PnL
                        final_pl = round((close_price - p_pos['avgPrice']) * p_pos['netQty'], 2)
                        p_pos['pl'] = final_pl
                        
                        logger.info(f"MARKET CLOSE EXIT (PAPER): {symbol} at {close_price} | PnL: {final_pl}")
                        log_trade_csv(symbol, "EXIT_MKT", close_price, p_pos['netQty'], f"SIMULATED | PnL: {final_pl}")

                # Save final paper state
                with open("static/paper_positions.json", "w") as f:
                    json.dump(paper_positions, f)

                # B. Auto-Close REAL Positions (If Enabled)
                if not DRY_RUN:
                    try:
                        real_positions = portfolio.get_positions(token)
                        if real_positions:
                            logger.info(f"Checking {len(real_positions)} Real Positions for Square-off...")
                            for pos in real_positions:
                                net_qty = int(pos.get('netQty', 0))
                                if net_qty != 0:
                                    symbol = pos['symbol']
                                    logger.info(f"Squaring off REAL position: {symbol} Qty: {net_qty}")
                                    
                                    # Place Counter Order (Market)
                                    side = -1 if net_qty > 0 else 1 # If Long(+), Sell(-). If Short(-), Buy(+)
                                    qty = abs(net_qty)
                                    
                                    exit_order = {
                                        "symbol": symbol,
                                        "qty": qty,
                                        "type": 2, # Market
                                        "side": side, 
                                        "productType": pos.get("productType", "INTRADAY"), # Match product type
                                        "validity": "DAY"
                                    }
                                    
                                    res = orders.place_order(token, exit_order)
                                    logger.info(f"Square-off Response for {symbol}: {res}")
                                    if res.get("s") == "ok":
                                        logger.info(f"Successfully Squared Off {symbol}")
                                    else:
                                        logger.error(f"Failed to Square Off {symbol}: {res}")
                                        
                        else:
                            logger.info("No Open Real Positions found to square off.")
                            
                    except Exception as e:
                        logger.error(f"Error during Real Position Square-off: {e}")

                logger.info("Market closed. Stopping loop.")

                # --- DAILY DATA DUMP START ---
                try:
                    today_str = datetime.date.today().strftime("%Y-%m-%d")
                    logger.info(f"Starting Daily Data Dump for {today_str}...")
                    
                    # 1. Save Candles
                    candles_base_dir = "daily_data/candles"
                    day_candle_dir = os.path.join(candles_base_dir, today_str)
                    os.makedirs(day_candle_dir, exist_ok=True)
                    
                    for instrument in TRADING_INSTRUMENTS:
                        sym = instrument['symbol']
                        logger.info(f"Saving candles for {sym}...")
                        try:
                            # Fetch Full Day
                            data = history.get_history(token, sym, TIMEFRAME, today_str, today_str)
                            candles = data.get("candles", [])
                            if candles:
                                safe_sym = sym.replace(":", "_")
                                file_path = os.path.join(day_candle_dir, f"{safe_sym}.csv")
                                with open(file_path, "w", newline='') as f:
                                    writer = csv.writer(f)
                                    writer.writerow(["Timestamp", "Open", "High", "Low", "Close", "Volume"])
                                    writer.writerows(candles)
                        except Exception as e:
                            logger.error(f"Failed to save candles for {sym}: {e}")

                    # 2. Save Trades (Copy from trade_history.csv)
                    trades_dir = "daily_data/trades"
                    os.makedirs(trades_dir, exist_ok=True)
                    daily_trade_file = os.path.join(trades_dir, f"{today_str}_trades.csv")
                    
                    if os.path.exists("static/trade_history.csv"):
                         with open("static/trade_history.csv", "r") as f_in, open(daily_trade_file, "w", newline='') as f_out:
                             reader = csv.reader(f_in)
                             writer = csv.writer(f_out)
                             headers = next(reader, None)
                             if headers:
                                 writer.writerow(headers)
                                 for row in reader:
                                     # Check if row belongs to today? 
                                     # Timestamp format: 2026-02-02 11:15:08
                                     if row and len(row) > 0 and row[0].startswith(today_str):
                                          writer.writerow(row)
                    
                    logger.info("Daily Data Dump Completed.")
                    
                except Exception as e:
                    logger.error(f"Daily Data Dump Failed: {e}")
                # --- DAILY DATA DUMP END ---

                break

            # THROTTLING: API Calls shouldn't run every 0.1s
            # Only fetch positions/quotes every 2 seconds
            should_fetch_api = False
            if 'last_api_fetch' not in locals():
                last_api_fetch = 0
            
            if time.time() - last_api_fetch > 2.0:
                 should_fetch_api = True
                 last_api_fetch = time.time()

            # FETCH POSITIONS (Throttle)
            cached_positions = []
            if should_fetch_api:
                cached_positions = portfolio.get_positions(token)
            else:
                # Keep using previous positions if not fetching
                if 'cached_positions' not in locals(): cached_positions = []

            # IDENTIFY BEST STRIKES (Dynamic Active Selection)
            # Only run this if API fetch is allowed
            if should_fetch_api:
                try:
                    all_syms = [i['symbol'] for i in TRADING_INSTRUMENTS]
                    sym_str = ",".join(all_syms)
                    quotes = market_data.get_quotes(token, sym_str)
                
                    # Find Best CE and Best PE
                    best_ce_sym = None
                    best_pe_sym = None
                    min_diff_ce = 99999
                    min_diff_pe = 99999
                    
                    if quotes.get('d'):
                        for item in quotes['d']:
                            price = item['v'].get('lp')
                            sym = item['n']
                            if price is None: continue
                            
                            LTP_CACHE[sym] = price # Seed Cache
                            
                            diff = abs(price - 500)
                            
                            if "CE" in sym:
                                if diff < min_diff_ce:
                                    min_diff_ce = diff
                                    best_ce_sym = sym
                            elif "PE" in sym:
                                if diff < min_diff_pe:
                                    min_diff_pe = diff
                                    best_pe_sym = sym
                                    
                    GLOBAL_BEST_CE = best_ce_sym
                    GLOBAL_BEST_PE = best_pe_sym
                    
                    # logger.info(f"LTP Map Populated with {len(ltp_map)} items.") # Verbose
                    logger.info(f"ACTIVE TRADING TARGETS (Closest to 500): CE={best_ce_sym} | PE={best_pe_sym}")
                except Exception as e:
                    if "API_RATE_LIMIT" in str(e):
                         logger.critical("RATE LIMIT DETECTED (429/403). Pausing for 15 minutes...")
                         time.sleep(900)
                    else:
                        logger.error(f"Error fetching quotes: {e}. Defaulting to allowing all.")
                    
                    best_ce_sym = None
                    best_pe_sym = None

            
            # PHASE 1: SCAN ALL INSTRUMENTS
            scan_results = []
            
            # Periodic History Refresh (Every 60s) used to align data
            if time.time() - last_history_full_update > 60:
                # logger.info("Refreshing History Data (60s Interval)...")
                # We can do this asynchronously without blocking
                for inst in TRADING_INSTRUMENTS:
                    executor.submit(fetch_process, inst).add_done_callback(
                        lambda f: history_map.update({f.result()[0]: f.result()[1]}) if f.result()[1] else None
                    )
                last_history_full_update = time.time()
            
            # SERIAL ANALYZE
            for instrument in TRADING_INSTRUMENTS:
                symbol = instrument['symbol']
                opt_type = instrument['type'] # "CE" or "PE"
                strategy_state = instrument['state']
                
                # Check for Active Strike (Just for logging)
                is_active = (best_ce_sym and symbol == best_ce_sym) or (best_pe_sym and symbol == best_pe_sym)
                prefix = "[ACTIVE]" if is_active else "[TRACKING]"
                
                # logger.info(f"--- Processing {symbol} {prefix} ---")
                
                # Get Data from Map
                data = history_map.get(symbol, {})
                
                if not data.get("candles"):
                    logger.warning(f"No candle data for {symbol}. Retrying fetch...")
                    
                    # Retry Fetch (Throttled)
                    now_ts = time.time()
                    last_retry = data.get("_last_retry", 0)
                    if now_ts - last_retry > 5.0: # Retry every 5 seconds
                        data["_last_retry"] = now_ts
                        try:
                             # Submit background job to update map
                             executor.submit(fetch_process, instrument).add_done_callback(
                                 lambda f: history_map.update({symbol: f.result()[1]})
                             )
                        except Exception as e:
                             logger.error(f"Retry submission failed for {symbol}: {e}")

                    # Fallback to keep row in UI
                    ltp = LTP_CACHE.get(symbol, 0)
                    scan_results.append({
                        "symbol": symbol,
                        "type": opt_type,
                        "action": "WAIT (No Data)",
                        "sl": None,
                        "last_candle_high": 0,
                        "rsi": 0,
                        "is_active": is_active,
                        "ltp": ltp
                    })
                    continue
                    
                candles = data["candles"]
                
                # --- LIVE CANDLE UPDATE (Simulate Real-Time RSI) ---
                if candles and symbol in LTP_CACHE:
                     lp = LTP_CACHE[symbol]
                     if lp > 0:
                         last_c = candles[-1]
                         # Update High, Low, Close
                         last_c[2] = max(last_c[2], lp)
                         last_c[3] = min(last_c[3], lp)
                         last_c[4] = lp
                # ---------------------------------------------------

                rsi_values = indicators.calculate_rsi(candles, period=14)
                
                last_candle = candles[-1]
                last_rsi = rsi_values[-1]
                
                # Target Calculation
                ts = last_candle[0]
                if ts > 9999999999: ts /= 1000
                candle_time = datetime.datetime.fromtimestamp(ts)
                candle_close_time = candle_time + datetime.timedelta(minutes=int(TIMEFRAME))
                
                target_candle = None
                target_rsi = 0
                
                # Latest Close Price (USE CACHE)
                ltp = LTP_CACHE.get(symbol, last_candle[4])

                # Update Paper Positions
                for p_pos in paper_positions:
                    if p_pos['symbol'] == symbol and p_pos.get('isOpen', True):
                        p_pos['ltp'] = ltp
                        # Short Position PnL: (Entry - LTP) * Qty
                        # If netQty is negative (Short), formula: (ltp - avgPrice) * netQty = (ltp - entry) * (-qty) => (entry - ltp) * qty.
                        p_pos['pl'] = round((ltp - p_pos['avgPrice']) * p_pos['netQty'], 2)
                        
                        # Check SL
                        sl_price = p_pos.get('sl_price', 0)
                        if sl_price > 0 and ltp >= sl_price:
                            logger.info(f"PAPER TRADE SL HIT: {symbol} at {ltp} (SL: {sl_price})")
                            p_pos['isOpen'] = False
                            p_pos['exitPrice'] = ltp
                            p_pos['exitTime'] = datetime.datetime.now().strftime("%H:%M:%S")
                            
                            # Log Exit PnL to History
                            log_trade_csv(symbol, "EXIT_SL", ltp, p_pos['netQty'], f"SIMULATED | PnL: {p_pos['pl']}")

                if now < candle_close_time:
                    if len(candles) < 2: continue
                    target_candle = candles[-2]
                    target_rsi = rsi_values[-2]
                    t_ts = target_candle[0]
                    if t_ts > 9999999999: t_ts /= 1000
                    logger.info(f"Completed Candle: {datetime.datetime.fromtimestamp(t_ts)} | RSI: {target_rsi:.2f}")
                else:
                    target_candle = last_candle
                    target_rsi = last_rsi
                    logger.info(f"Completed Candle: {candle_time} | RSI: {target_rsi:.2f}")

                # Check Position (Real + Paper)
                current_side, net_qty = get_position_from_cache(cached_positions, symbol)
                
                # Check Paper Position
                paper_qty = 0
                for p in paper_positions:
                    if p['symbol'] == symbol and p.get('isOpen', True):
                        paper_qty += p['netQty']
                
                if paper_qty != 0: 
                    logger.info(f"Position: {current_side} (Real: {net_qty}, Paper: {paper_qty})")
                else:
                    logger.info(f"Position: {current_side} (Qty: {net_qty})")

                # Check Signal
                eff_side = "SHORT" if paper_qty < 0 else current_side 
                
                # DEBUG LOGGING for 24450CE or general
                if "24450" in symbol or "24500" in symbol:
                     logger.info(f"DEBUG: Checking {symbol} | RSI: {target_rsi:.2f} | Side: {eff_side} | Trigger: {strategy_state.get('trigger_candle') is not None}")
                
                signal, new_state = strategy.check_rsi_signal(target_candle, target_rsi, eff_side, strategy_state)
                instrument['state'] = new_state
                
                if new_state['trigger_candle']:
                    logger.info(f"WATCH: Trigger Active (RSI {new_state['trigger_rsi']:.2f}). Waiting for breakdown.")
                    if "24450" in symbol:
                        logger.info(f"DEBUG: Trigger Details: {new_state['trigger_candle']}")
                
                action = signal.get("action")
                sl = signal.get("sl")
                
                if action == "ENTER_SHORT":
                    logger.info(f"SIGNAL DETECTED on {symbol}! (Breakdown Confirmed)")
                
                # Store Result
                scan_results.append({
                    "symbol": symbol,
                    "type": opt_type,
                    "action": action,
                    "sl": sl,
                    "last_candle_high": target_candle[2] if target_candle else 0, # High is index 2
                    "rsi": round(target_rsi, 2),
                    "is_active": is_active,
                    "ltp": ltp
                })

            # PHASE 2: EXECUTION LOGIC (Proxy Trigger)
            def execute_trade_on(target_sym, sl_price, trigger_source_sym):
                logger.info(f"EXECUTING Trade on ACTIVE {target_sym} (Triggered by {trigger_source_sym})")
                
                # Check valid SL
                if not sl_price or sl_price <= 0:
                     logger.warning("Invalid Stop Loss Price. Skipping.")
                     return

                # Check if already open (Paper State)
                already_open = any(p['symbol'] == target_sym and p.get('isOpen', True) for p in paper_positions)
                if already_open:
                    logger.info(f"Position already open for {target_sym}. Skipping duplicate.")
                    return

                # 1. ATTEMPT REAL ORDER (If not Dry Run)
                if not DRY_RUN:
                    # Place Order
                    order_data = {
                        "symbol": target_sym,
                        "qty": QTY,
                        "type": 2, # Market
                        "side": -1, # Sell
                        "productType": "INTRADAY",
                        "validity": "DAY"
                    }
                    res = orders.place_order(token, order_data)
                    logger.info(f"Order Response: {res}")
                    
                    if res.get("s") != "ok":
                         logger.error(f"CRITICAL: Real Order Failed. Error: {res.get('message')}")
                         # Log failure to CSV for audit
                         log_trade_csv(target_sym, "SELL_FAIL", 0, QTY, f"ERROR: {res.get('message')}")
                         # Proceed to record paper trade anyway (as per user preference)
                         
                    else:
                        log_trade_csv(target_sym, "SELL", 0, QTY, "REAL_ORDER_SENT") # Price 0 as market order

                        # Place SL (Fire and Forget)
                        sl_order = {
                            "symbol": target_sym,
                            "qty": QTY,
                            "type": 4, # SL-M
                            "side": 1, # Buy to Cover
                            "stopPrice": sl_price,
                            "productType": "INTRADAY",
                            "validity": "DAY"
                        }
                        logger.info(f"Placing SL Order at {sl_price}")
                        threading.Thread(target=orders.place_order, args=(token, sl_order)).start()

                else:
                    logger.info(f"[DRY RUN] SOLD {target_sym} at Market. SL: {sl_price}")

                # 2. RECORD PAPER TRADE (Only if we reached here)
                # Fallback to LTP_CACHE if not in scan_results
                ltp_est = next((r['ltp'] for r in scan_results if r['symbol'] == target_sym), 0)
                if ltp_est <= 0:
                    ltp_est = LTP_CACHE.get(target_sym, 0)
                    
                # Force record even if price 0 (signal happened)
                paper_positions.append({
                    "symbol": target_sym,
                    "netQty": -QTY, 
                    "avgPrice": ltp_est if ltp_est > 0 else 0,
                    "ltp": ltp_est,
                    "pl": 0.0,
                    "productType": "PAPER",
                    "sl_price": sl_price,
                    "isOpen": True,
                    "ENTRY_TIME": datetime.datetime.now().strftime("%H:%M:%S")
                })
                logger.info(f"PAPER TRADE RECORDED: Sell {target_sym} at {ltp_est}")
                log_trade_csv(target_sym, "SELL", ltp_est, QTY, "SIMULATED")

            # Check CE Signals
            ce_signals = [r for r in scan_results if "CE" in r['symbol'] and r['action'] == "ENTER_SHORT"]
            if ce_signals:
                trigger = ce_signals[0] # Take first one
                if best_ce_sym:
                    active_data = next((r for r in scan_results if r['symbol'] == best_ce_sym), None)
                    if active_data:
                        final_sl = active_data['sl'] if active_data['action'] == "ENTER_SHORT" else active_data['last_candle_high']
                        execute_trade_on(best_ce_sym, final_sl, trigger['symbol'])
                    else:
                        logger.warning(f"Active CE {best_ce_sym} not found in scan results!")
                else:
                     logger.warning("No Active CE identified to trade!")

            # Check PE Signals
            pe_signals = [r for r in scan_results if "PE" in r['symbol'] and r['action'] == "ENTER_SHORT"]
            if pe_signals:
                trigger = pe_signals[0]
                if best_pe_sym:
                    active_data = next((r for r in scan_results if r['symbol'] == best_pe_sym), None)
                    if active_data:
                        final_sl = active_data['sl'] if active_data['action'] == "ENTER_SHORT" else active_data['last_candle_high']
                        execute_trade_on(best_pe_sym, final_sl, trigger['symbol'])
                    else:
                        logger.warning(f"Active PE {best_pe_sym} not found in scan results!")
                else:
                     logger.warning("No Active PE identified to trade!")
            
            # UPDATE GLOBAL STATE (JSON Updater thread handles writing algo_status.json)
            if scan_results:
                GLOBAL_SCAN_RESULTS = scan_results
            
            # EXPORT PAPER POSITIONS (Critical State)
            try:
                with open("static/paper_positions.json", "w") as f:
                    json.dump(paper_positions, f)
            except Exception as e:
                logger.error(f"Failed to write paper JSON: {e}")

            logger.debug(f"Strategy Loop: Waiting {SLEEP_INTERVAL}s...") 
            time.sleep(SLEEP_INTERVAL)

        except Exception as e:
            logger.error(f"Error in trading loop: {e}")
            logger.error(traceback.format_exc())

def validate_token(token):
    """
    Checks if token is valid by making a lightweight API call (e.g. Profile).
    If invalid, tries to re-login (if automated) or just logs fatal.
    """
    try:
        # Simple check: Get Positions or Profile
        portfolio.get_positions(token)
        return True
    except Exception as e:
        logger.error(f"Token Validation Failed: {e}")
        return False

if __name__ == "__main__":
    RESTART_COUNT = 0
    MAX_RESTARTS = 50
    
    while True:
        try:
            logger.info(f"--- Starting Live Trader (Session {RESTART_COUNT+1}) ---")
            run_trading_loop()
            
            # If run_trading_loop returns naturally (e.g. Market Closed), exit loop
            logger.info("Trading loop finished normally. Exiting.")
            break
            
        except KeyboardInterrupt:
            logger.info("User stopped the script.")
            break
            
        except Exception as e:
            logger.critical(f"CRITICAL CRASH: {e}")
            logger.critical(traceback.format_exc())
            
            RESTART_COUNT += 1
            if RESTART_COUNT > MAX_RESTARTS:
                logger.critical("Too many restarts. Stopping permanently to prevent loops.")
                break
                
            logger.info("Restarting in 900 seconds (15 minutes) to allow Rate Limits to reset...")
            time.sleep(900)
            
            # validate token before restart
            try:
                token = get_token()
                if not validate_token(token):
                    logger.critical("Token is invalid. Please re-login via main.py")
            except:
                pass
