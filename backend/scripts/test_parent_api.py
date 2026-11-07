"""Test parent API endpoint."""

import asyncio
import httpx

async def test_parent_api():
    # Login as parent
    async with httpx.AsyncClient(timeout=30.0) as client:
        login_response = await client.post(
            "http://127.0.0.1:8000/api/auth/login",
            json={"email": "veli@demo.com", "password": "Admin123*"}
        )
        
        if login_response.status_code != 200:
            print(f"Login failed: {login_response.status_code}")
            print(login_response.text)
            return
        
        token_data = login_response.json()
        print(f"Full response: {token_data}")
        
        # Check if data is nested
        if "data" in token_data:
            token = token_data["data"].get("access_token")
        else:
            token = token_data.get("access_token")
        
        if not token:
            print("No token in response")
            return
        
        print(f"Login successful! Token: {token[:20]}...")
        
        # Get children
        headers = {"Authorization": f"Bearer {token}"}
        children_response = await client.get(
            "http://127.0.0.1:8000/api/parent/my-children",
            headers=headers
        )
        
        print(f"\nChildren response status: {children_response.status_code}")
        print(f"Children response: {children_response.text}")
        
        # Get children data
        children_data = children_response.json()
        if children_data.get("success") and children_data.get("data"):
            student_id = children_data["data"][0]["student_id"]
            print(f"\nTesting with student_id: {student_id}")
            
            # Test today-status endpoint
            today_status_response = await client.get(
                f"http://127.0.0.1:8000/api/parent/child/{student_id}/today-status",
                headers=headers
            )
            print(f"\nToday status response status: {today_status_response.status_code}")
            print(f"Today status response: {today_status_response.text}")


if __name__ == "__main__":
    asyncio.run(test_parent_api())
