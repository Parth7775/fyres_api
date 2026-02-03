import requests
import config

def get_positions(access_token):
    """
    Fetches the current open positions.
    """
    url = "https://api-t1.fyers.in/api/v3/positions"
    headers = {
        "Authorization": f"{config.CLIENT_ID}:{access_token}"
    }
    
    try:
        # DEBUG: Print token/app_id hash or partial to verify
        # print(f"DEBUG: Positions Token: {access_token[:5]}... AppID: {config.CLIENT_ID}")
        
        response = requests.get(url, headers=headers, verify=False) # SSL Verify False for Mac
        data = response.json()
        if data.get("s") == "ok":
            return data.get("netPositions", [])
        else:
            print(f"Error fetching positions: {data}")
            return []
    except Exception as e:
        print(f"Exception in get_positions: {e}")
        return []

def get_holdings(access_token):
    """
    Fetches the current holdings.
    """
    url = "https://api-t1.fyers.in/api/v3/holdings"
    headers = {
        "Authorization": f"{config.CLIENT_ID}:{access_token}"
    }
    
    try:
        response = requests.get(url, headers=headers)
        data = response.json()
        if data.get("s") == "ok":
            return data.get("holdings", [])
        else:
            print(f"Error fetching holdings: {data}")
            return []
    except Exception as e:
        print(f"Exception in get_holdings: {e}")
        return []
