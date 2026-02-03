import hashlib
import requests
import webbrowser
from urllib.parse import urlencode
import config

def get_login_url():
    """
    Generates the login URL for Fyers API v3.
    """
    params = {
        "client_id": config.CLIENT_ID,
        "redirect_uri": config.REDIRECT_URI,
        "response_type": config.RESPONSE_TYPE,
        "state": "random_string" # In prod, use a secure random string
    }
    base_url = "https://api-t1.fyers.in/api/v3/generate-authcode"
    return f"{base_url}?{urlencode(params)}"

def generate_app_id_hash(client_id, secret_key):
    """
    Generates the SHA-256 hash of 'client_id:secret_key'.
    """
    data = f"{client_id}:{secret_key}"
    return hashlib.sha256(data.encode('utf-8')).hexdigest()

def generate_access_token(auth_code):
    """
    Exchanges the auth code for an access token.
    """
    app_id_hash = generate_app_id_hash(config.CLIENT_ID, config.SECRET_KEY)
    
    url = "https://api-t1.fyers.in/api/v3/validate-authcode"
    headers = {
        "Content-Type": "application/json"
    }
    payload = {
        "grant_type": config.GRANT_TYPE,
        "appIdHash": app_id_hash,
        "code": auth_code,
    }
    
    response = requests.post(url, json=payload, headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        if data.get("s") == "ok":
            return data.get("access_token")
        else:
            raise Exception(f"Failed to get access token: {data}")
    else:
        raise Exception(f"HTTP Error {response.status_code}: {response.text}")

def get_profile(access_token):
    """
    Fetches the user profile using the access token.
    """
    url = "https://api-t1.fyers.in/api/v3/profile"
    headers = {
        "Authorization": f"{config.CLIENT_ID}:{access_token}"
    }
    response = requests.get(url, headers=headers)
    return response.json()
