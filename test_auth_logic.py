import asyncio
import os
import sys
import httpx
from app.main import app
from dotenv import load_dotenv

async def verify_logout_logic():
    load_dotenv()
    
    # 1. Internal check: Does the route exist?
    from fastapi.routing import APIRoute
    logout_route = None
    for route in app.routes:
        if isinstance(route, APIRoute) and route.path == "/api/v1/auth/logout":
            logout_route = route
            break
    
    if logout_route:
        print(f"SUCCESS: Logout route found at {logout_route.path}")
        print(f"Methods: {logout_route.methods}")
    else:
        print("FAILURE: Logout route NOT found!")
        return False

    # 2. Integration check: Call it
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        # Test 401
        response = await ac.post("/api/v1/auth/logout")
        print(f"Post-implementation auth check: {response.status_code}")
        
        if response.status_code == 401:
            print("Auth requirement confirmed.")
            return True
        else:
            print(f"Unexpected status: {response.status_code}")
            return False

if __name__ == "__main__":
    success = asyncio.run(verify_logout_logic())
    if not success:
        sys.exit(1)
