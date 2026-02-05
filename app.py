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

from flask import Flask, render_template, jsonify, request
import main
import portfolio
import orders
import logging

import json
import os

import threading
import datetime
import live_trader # Import the algo engine

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_token():
    """Helper to get the current access token."""
    return main.load_access_token()

@app.route('/')
def index():
    return render_template('dashboard.html')

# ... (API Positions and Trade routes remain the same) ...

@app.route('/api/live_data', methods=['GET'])
def live_data():
    """Returns real-time algo status from memory (No Disk I/O)"""
    return jsonify({
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "scan_results": live_trader.GLOBAL_SCAN_RESULTS,
        "active_ce": live_trader.GLOBAL_BEST_CE,
        "active_pe": live_trader.GLOBAL_BEST_PE
    })

@app.route('/api/positions', methods=['GET'])
def api_positions():
    token = get_token()
    if not token:
        return jsonify({"s": "error", "message": "No access token found"}), 401
    
    positions = portfolio.get_positions(token)
    if positions is None: positions = []
    
    # Load Paper Positions
    try:
        # Paper positions are still file-based for persistence across restarts
        if os.path.exists("static/paper_positions.json"):
            with open("static/paper_positions.json", "r") as f:
                paper_pos = json.load(f)
                
            for p in paper_pos:
                if p.get("isOpen", True):
                    # Frontend expects specific fields
                    positions.append({
                        "symbol": p["symbol"],
                        "netQty": int(p["netQty"]),
                        "avgPrice": float(p["avgPrice"]),
                        "ltp": float(p["ltp"]),
                        "pl": float(p["pl"]),
                        "productType": "PAPER (Sim)"
                    })
                    
    except Exception as e:
        logger.error(f"Error loading paper positions: {e}")

    return jsonify({"s": "ok", "positions": positions})

@app.route('/api/trade', methods=['POST'])
def api_trade():
    token = get_token()
    if not token:
        return jsonify({"s": "error", "message": "No access token found"}), 401
    
    data = request.json
    logger.info(f"Received trade request: {data}")
    
    # Validate required fields
    required = ['symbol', 'qty', 'side', 'type', 'productType']
    if not all(k in data for k in required):
        return jsonify({"s": "error", "message": "Missing required fields"}), 400
        
    response = orders.place_order(token, data)
    logger.info(f"Fyers API Response: {response}")
    
    if response.get("s") == "ok":
        return jsonify({"status": "success", "data": response})
    else:
        return jsonify({"status": "error", "message": response.get("message", "Unknown error"), "full_response": response})

@app.route('/api/history', methods=['GET'])
def api_history():
    """Returns the trade log from CSV"""
    history = []
    try:
        if os.path.exists("static/trade_history.csv"):
            import csv
            with open("static/trade_history.csv", "r") as f:
                reader = csv.DictReader(f)
                # Filter out rows with None keys and clean data
                clean_history = []
                for row in reader:
                    if row and None not in row:
                        clean_history.append(row)
                history = clean_history
                # Reverse to show latest first
                history.reverse()
    except Exception as e:
        logger.error(f"Error reading history: {e}")
    
    return jsonify({"s": "ok", "history": history})

def start_background_trader():
    """Runs the live trader loop in a separate thread"""
    try:
        logger.info("Starting Background Trading Thread...")
        live_trader.run_trading_loop()
    except Exception as e:
        logger.error(f"Background Thread Crash: {e}")

if __name__ == '__main__':
    print("Starting Dashboard & Algo on http://localhost:5000")
    
    # Start Algo Thread
    t = threading.Thread(target=start_background_trader)
    t.daemon = True
    t.start()
    
    # Disable reloader to prevent double-execution of threads
    app.run(debug=True, port=5000, use_reloader=False)
