import requests
import config

def get_quotes(access_token, symbols):
    """
    Fetches market quotes for the given symbols.
    
    Args:
        access_token (str): The valid access token.
        symbols (str): Comma-separated list of symbols (e.g. "NSE:SBIN-EQ,NSE:HDFC-EQ")
        
    Returns:
        dict: The JSON response from the API.
    """
    url = "https://api-t1.fyers.in/data/quotes"
    headers = {
        "Authorization": f"{config.CLIENT_ID}:{access_token}"
    }
    params = {
        "symbols": symbols
    }
    
    response = requests.get(url, headers=headers, params=params, verify=False)
    
    # DEBUG: Check response validity
    if response.status_code != 200:
        print(f"DEBUG: Quote API Failed [{response.status_code}]: {response.text}")
        if response.status_code == 429 or response.status_code == 403:
             raise Exception(f"API_RATE_LIMIT {response.status_code}")
             
    elif not response.text:
        print("DEBUG: Quote API returned EMPTY response")
        raise Exception("API_EMPTY_RESPONSE")
    
    try:
        return response.json()
    except Exception as e:
        print(f"DEBUG: Quote JSON Decode Error: {e} | Content: {response.text[:200]}")
        raise e
