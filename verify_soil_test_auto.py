import requests
import json

BASE_URL = "http://localhost:8000/api/v1"

# Manual token for testing (you might need to get a fresh one)
TOKEN = "YOUR_TOKEN_HERE" 

def test_soil_test_auto_farmer():
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json"
    }
    
    # Existing Farmer from previous invoice test
    whatsapp_number = "9876543210"
    
    # Test Case 1: Auto-detect name for existing farmer
    payload_auto = {
        "whatsapp_number": whatsapp_number,
        "crop_type": "Wheat"
    }
    
    print("\n--- Testing Soil Test Start with Auto-Detection (Existing Farmer) ---")
    response_auto = requests.post(f"{BASE_URL}/soil-tests/start", headers=headers, json=payload_auto)
    
    if response_auto.status_code == 201:
        data = response_auto.json()
        print(f"Success! Report ID: {data['report_meta']['report_id']}")
        print(f"Detected Name: {data['report_meta']['farmer_name']}")
    else:
        print(f"Failed! Status Code: {response_auto.status_code}")
        print(response_auto.text)

    # Test Case 2: Multi-field update (address update while starting test)
    payload_update = {
        "whatsapp_number": whatsapp_number,
        "address": "New Wheat Farm Road 456",
        "crop_type": "Rice"
    }
    print("\n--- Testing Soil Test Start with Address Update ---")
    response_update = requests.post(f"{BASE_URL}/soil-tests/start", headers=headers, json=payload_update)
    if response_update.status_code == 201:
        data = response_update.json()
        print(f"Success! New Address: {data['report_meta'].get('address', 'N/A')}") # Schema might not include address in meta, let's check response
        print(f"Report ID: {data['report_meta']['report_id']}")
    else:
        print(f"Failed! Status Code: {response_update.status_code}")
        print(response_update.text)

if __name__ == "__main__":
    print("Note: Ensure the local server is running and UPDATE the TOKEN in the script.")
    test_soil_test_auto_farmer()
