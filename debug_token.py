import requests
import config
import ssl
import json

# Force SSL context bypass even for requests if possible (via adapter) 
# but simplest first step is verify=False or verify=certifi.where()

def check_token():
    try:
        with open("access_token.txt", "r") as f:
            token = f.read().strip()
    except FileNotFoundError:
        print("access_token.txt not found.")
        return

    print(f"Token (first 10 chars): {token[:10]}...")
    
    url = "https://api-t1.fyers.in/api/v3/profile"
    headers = {
        "Authorization": f"{config.CLIENT_ID}:{token}"
    }

    try:
        print("\nChecking Profile (verify=True)...")
        response = requests.get(url, headers=headers)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
    except Exception as e:
        print(f"Error (verify=True): {e}")

    try:
        print("\nChecking Profile (verify=False)...")
        response = requests.get(url, headers=headers, verify=False)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
    except Exception as e:
        print(f"Error (verify=False): {e}")

if __name__ == "__main__":
    check_token()
