import requests
import config
import datetime

def get_history(access_token, symbol, resolution, range_from, range_to, date_format=1, cont_flag=1):
    """
    Fetches historical candle data for the given symbol.
    
    Args:
        access_token (str): Valid access token.
        symbol (str): Symbol in format 'EXCHANGE:SYMBOL' (e.g. 'NSE:DIXON-EQ').
        resolution (str): Candle resolution (e.g. '3' for 3-minute).
        range_from (str): Start date (YYYY-MM-DD if date_format=1).
        range_to (str): End date (YYYY-MM-DD if date_format=1).
        date_format (int): 0 for epoch, 1 for YYYY-MM-DD. Default 1.
        cont_flag (int): 1 for continuous data (handling expiries), 0 otherwise. Default 1.
        
    Returns:
        dict: JSON response containing candle data.
    """
    url = "https://api-t1.fyers.in/data/history"
    headers = {
        "Authorization": f"{config.CLIENT_ID}:{access_token}"
    }
    params = {
        "symbol": symbol,
        "resolution": resolution,
        "date_format": date_format,
        "range_from": range_from,
        "range_to": range_to,
        "cont_flag": cont_flag
    }
    
    response = requests.get(url, headers=headers, params=params, verify=False)
    return response.json()
