import requests
import config
import json

def place_order(access_token, order_data):
    """
    Places an order using the Fyers API.
    
    Args:
        access_token (str): Valid access token.
        order_data (dict): Dictionary containing order details.
            Required fields:
            - symbol (str): e.g., "NSE:SBIN-EQ"
            - qty (int): Quantity
            - type (int): 1=Limit, 2=Market
            - side (int): 1=Buy, -1=Sell
            - productType (str): "INTRADAY", "CNC", etc.
            - validity (str): "DAY", "IOC"
            - limitPrice (float): Required for Limit orders
            - stopPrice (float): Required for Stop orders
            
    Returns:
        dict: The API response.
    """
    url = "https://api-t1.fyers.in/api/v3/orders/sync"
    headers = {
        "Authorization": f"{config.CLIENT_ID}:{access_token}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(url, headers=headers, json=order_data, verify=False)
        return response.json()
    except Exception as e:
        return {"s": "error", "message": str(e)}
