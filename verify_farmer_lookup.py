import requests

BASE_URL = "http://localhost:8000/api/v1"
TOKEN = "YOUR_TOKEN_HERE"

def test_lookup_api():
    headers = {"Authorization": f"Bearer {TOKEN}"}
    whatsapp_number = "9876543210"
    
    print(f"\n--- Testing Farmer Lookup: {whatsapp_number} ---")
    response = requests.get(f"{BASE_URL}/farmers/lookup/{whatsapp_number}", headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        print(f"Success! Name: {data['farmer_name']}, Address: {data['address']}")
    elif response.status_code == 404:
        print("Farmer not found (Expected if not created yet)")
    else:
        print(f"Failed! Status Code: {response.status_code}")
        print(response.text)

if __name__ == "__main__":
    test_lookup_api()
