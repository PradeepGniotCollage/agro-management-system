import requests
import json
import time

BASE_URL = "http://127.0.0.1:8000/api/v1"

def test_soil_test():
    # 1. Login (assuming admin user from seeding)
    login_data = {
        "username": "9838000000",
        "password": "1234"
    }
    
    print("Logging in...")
    try:
        response = requests.post(f"{BASE_URL}/auth/login", data=login_data)
        if response.status_code != 200:
            print(f"Login failed: {response.text}")
            return
        
        token = response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print("Login successful.")

        # 2. Start Soil Test
        soil_test_data = {
            "farmer_name": "Test Farmer",
            "whatsapp_number": "9999999999",
            "address": "Test Address",
            "crop_type": "Wheat"
        }
        
        print("Starting soil test...")
        # Note: This might hang if the hardware doesn't respond, so we set a timeout
        response = requests.post(f"{BASE_URL}/soil-tests/start", json=soil_test_data, headers=headers, timeout=10)
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")

    except Exception as e:
        print(f"Error during test: {e}")

if __name__ == "__main__":
    test_soil_test()
