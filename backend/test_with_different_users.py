"""
Test medicine requests with different user roles
"""
import asyncio
import requests
import json

# Test with different users
users = [
    {"email": "admin@demo.com", "password": "Admin123*", "role": "Super Admin"},
    {"email": "veli@demo.com", "password": "Admin123*", "role": "Parent"},
    {"email": "subeyetkili@demo.com", "password": "Admin123*", "role": "Branch Manager"},
]

for user in users:
    print(f"\n{'='*50}")
    print(f"Testing with {user['role']}: {user['email']}")
    print('='*50)
    
    try:
        # Login
        response = requests.post("http://127.0.0.1:8000/api/auth/login", json={
            "email": user["email"],
            "password": user["password"]
        })
        
        if response.status_code == 200:
            token_data = response.json()
            token = token_data.get("data", {}).get("access_token")
            
            if token:
                # Get medicine requests
                headers = {"Authorization": f"Bearer {token}"}
                response = requests.get("http://127.0.0.1:8000/api/infirmary/medicine-requests", headers=headers)
                print(f"Status: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"Success: {data.get('success')}")
                    print(f"Data count: {len(data.get('data', []))}")
                    if data.get('data'):
                        print(f"First item: {json.dumps(data['data'][0], indent=2)}")
                else:
                    print(f"Error: {response.text}")
            else:
                print("No token received")
        else:
            print(f"Login failed: {response.text}")
            
    except Exception as e:
        print(f"Error: {e}")
