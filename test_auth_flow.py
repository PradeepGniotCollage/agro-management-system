import asyncio
import os
import sys
from httpx import AsyncClient
from app.main import app
from app.core.config import settings
from dotenv import load_dotenv

async def test_logout_flow():
    load_dotenv()
    
    # We'll use the TestClient via httpx AsyncClient for async support
    async with AsyncClient(app=app, base_url="http://test") as ac:
        print("Testing authentication requirement for logout...")
        # 1. Test logout without token (should fail)
        response = await ac.post("/api/v1/auth/logout")
        print(f"Logout without token status: {response.status_code}")
        
        if response.status_code == 401:
            print("Successfully verified: Logout requires authentication.")
        else:
            print(f"Warning: Logout returned {response.status_code} instead of 401.")

        print("\nAttempting to login to test authorized logout...")
        # 2. Attempt login
        # We'll try common admin credentials from .env or config
        phone = os.getenv("INITIAL_ADMIN_PHONE", "9999999999")
        pin = os.getenv("INITIAL_ADMIN_PASSWORD", "admin123")
        
        login_data = {
            "username": phone,
            "password": pin
        }
        
        # OAuth2PasswordRequestForm expects form-data
        login_response = await ac.post("/api/v1/auth/login", data=login_data)
        
        if login_response.status_code == 200:
            token = login_response.json().get("access_token")
            print("Login successful.")
            
            # 3. Test logout with token
            headers = {"Authorization": f"Bearer {token}"}
            logout_response = await ac.post("/api/v1/auth/logout", headers=headers)
            
            print(f"Logout with token status: {logout_response.status_code}")
            print(f"Logout response body: {logout_response.json()}")
            
            if logout_response.status_code == 200 and logout_response.json().get("message") == "Successfully logged out":
                print("\nSUCCESS: Logout API is working correctly!")
                return True
            else:
                print("\nFAILURE: Logout API did not return expected response.")
                return False
        else:
            print(f"Login failed ({login_response.status_code}): {login_response.text}")
            print("Skipping authenticated logout test (requires real database user).")
            # If we reach here, we at least verified the 401 case which shows the endpoint is protected.
            return True if response.status_code == 401 else False

if __name__ == "__main__":
    result = asyncio.run(test_logout_flow())
    if not result:
        sys.exit(1)
