"""
Test frontend authentication and medicine requests endpoint
"""
import asyncio
import requests
import json

# First login as superadmin to get token
login_data = {
    "email": "admin@demo.com",
    "password": "Admin123*"
}

try:
    # Login
    response = requests.post("http://127.0.0.1:8000/api/auth/login", json=login_data)
    print(f"Login status: {response.status_code}")
    
    if response.status_code == 200:
        token_data = response.json()
        token = token_data.get("data", {}).get("access_token")
        print(f"Got token: {token[:20]}..." if token else "No token found")
        
        if token:
            # Test the exact endpoint that frontend uses
            headers = {"Authorization": f"Bearer {token}"}
            response = requests.get("http://127.0.0.1:8000/api/infirmary/medicine-requests", headers=headers)
            print(f"\nMedicine requests status: {response.status_code}")
            print(f"Response: {json.dumps(response.json(), indent=2)}")
            
            # Test infirmary visits endpoint too
            response = requests.get("http://127.0.0.1:8000/api/infirmary/infirmary-visits", headers=headers)
            print(f"\nInfirmary visits status: {response.status_code}")
            print(f"Response: {json.dumps(response.json(), indent=2)}")
    else:
        print(f"Login failed: {response.text}")
        
except Exception as e:
    print(f"Error: {e}")
