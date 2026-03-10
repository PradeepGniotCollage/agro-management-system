import requests
import json
from datetime import date

BASE_URL = "http://127.0.0.1:8000/api/v1"

def run_tests():
    # 1. Login
    login_data = {"username": "9838000000", "password": "1234"}
    try:
        resp = requests.post(f"{BASE_URL}/auth/login", data=login_data)
        resp.raise_for_status()
    except Exception as e:
        print(f"Login failed: {e}. Is the server running?")
        return

    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # Get current user info
    user_me = requests.get(f"{BASE_URL}/auth/me", headers=headers).json()
    user_id = user_me["id"]
    print(f"Logged in as User ID: {user_id}")

    print("\n--- Testing Farmer History Endpoint ---")
    # Using farmer_id 9 from previous successful test
    farmer_id = 9
    resp = requests.get(f"{BASE_URL}/soil-tests/farmer/{farmer_id}", headers=headers)
    print(f"Farmer History Status: {resp.status_code}")
    if resp.status_code == 200:
        reports = resp.json()
        print(f"Result: Found {len(reports)} reports for Farmer {farmer_id}")
        if len(reports) > 0:
            print(f"Latest Report ID: {reports[0]['id']}")
    else:
        print(f"Farmer History Error: {resp.text}")

    print("\n--- Testing User History ---")
    resp = requests.get(f"{BASE_URL}/soil-tests/user/{user_id}", headers=headers)
    print(f"User History Status: {resp.status_code}")
    if resp.status_code == 200:
        print(f"Result: Found {len(resp.json())} reports for User {user_id}")

if __name__ == "__main__":
    run_tests()
