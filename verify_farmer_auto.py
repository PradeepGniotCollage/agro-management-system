import requests
import json

BASE_URL = "http://localhost:8000/api/v1"

# Manual token for testing (you might need to get a fresh one)
TOKEN = "YOUR_TOKEN_HERE" 

def test_create_invoice_auto_farmer():
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json"
    }
    
    # Test Data
    payload = {
        "customer_name": "Test Farmer Auto",
        "mobile_number": "9876543210",
        "address": "Auto Street 123",
        "invoice_date": "2026-03-12",
        "items": [
            {
                "item_name": "Soil Test Kit",
                "quantity": 2,
                "rate": 500
            }
        ]
    }
    
    print("\n--- Testing Invoice Creation with Auto-Farmer ---")
    response = requests.post(f"{BASE_URL}/invoice/create", headers=headers, json=payload)
    
    if response.status_code == 201:
        data = response.json()
        print(f"Success! Invoice ID: {data['id']}")
        print(f"Farmer ID assigned: {data['invoice_meta']['farmer_id']}")
        
        # Verify farmer exists
        farmer_id = data['invoice_meta']['farmer_id']
        farmer_resp = requests.get(f"{BASE_URL}/farmers", headers=headers)
        if farmer_resp.status_code == 200:
            farmers = farmer_resp.json()['farmers']
            found = any(f['id'] == farmer_id for f in farmers)
            print(f"Verified: Farmer {farmer_id} exists in /farmers list: {found}")
    # Test Case: Auto-detect name and address for existing farmer
    payload_auto = {
        "mobile_number": "9876543210", # This farmer was created in previous step
        "invoice_date": "2026-03-12",
        "items": [
            {
                "item_name": "NPK Fertilizer",
                "quantity": 1,
                "rate": 1200
            }
        ]
    }
    
    print("\n--- Testing Invoice Creation with Auto-Detection (Mobile Only) ---")
    response_auto = requests.post(f"{BASE_URL}/invoice/create", headers=headers, json=payload_auto)
    
    if response_auto.status_code == 201:
        data = response_auto.json()
        print(f"Success! Invoice ID: {data['id']}")
        print(f"Detected Name: {data['invoice_meta']['customer_name']}")
        print(f"Detected Address: {data['invoice_meta']['address']}")
    else:
        print(f"Failed! Status Code: {response_auto.status_code}")
        print(response_auto.text)

if __name__ == "__main__":
    print("Note: Ensure the local server is running and UPDATE the TOKEN in the script.")
    test_create_invoice_auto_farmer()
