#!/usr/bin/env python3
"""
Test script to investigate authentication error during vehicle status updates
"""
import requests
import json

def test_auth_status_update():
    print("Testing Authentication During Vehicle Status Update")
    print("=" * 60)
    
    base_url = "http://127.0.0.1:5001"
    
    # Create a session to maintain cookies
    session = requests.Session()
    
    try:
        # Step 1: Login first
        print("1. Testing login...")
        login_data = {
            'username': 'admin',
            'password': 'admin123'
        }
        
        login_response = session.post(
            f"{base_url}/login",
            data=login_data,
            allow_redirects=False
        )
        
        print(f"   Login status: {login_response.status_code}")
        print(f"   Login cookies: {session.cookies}")
        
        if login_response.status_code not in [200, 302]:
            print("❌ Login failed - cannot proceed with test")
            return
            
        # Step 2: Get a sample vehicle to test with
        print("\n2. Getting sample vehicle...")
        vehicles_response = session.get(f"{base_url}/api/vehicles?status=active")
        
        if vehicles_response.status_code != 200:
            print(f"❌ Failed to get vehicles: {vehicles_response.status_code}")
            return
            
        vehicles = vehicles_response.json()
        if not vehicles:
            print("❌ No vehicles found to test with")
            return
            
        test_vehicle = vehicles[0]
        call_number = test_vehicle['towbook_call_number']
        current_status = test_vehicle['status']
        
        print(f"   Test vehicle: {call_number}")
        print(f"   Current status: {current_status}")
        
        # Step 3: Test status update from "TOP Generated" to "Released"
        print("\n3. Testing status update...")
        
        # First, ensure the vehicle is in "TOP Generated" status
        if current_status != "TOP Generated":
            print(f"   Setting vehicle to 'TOP Generated' first...")
            update_data = {"status": "TOP Generated"}
            
            update_response = session.put(
                f"{base_url}/api/vehicles/{call_number}",
                json=update_data,
                headers={'Content-Type': 'application/json'}
            )
            
            print(f"   Pre-update status: {update_response.status_code}")
            if update_response.status_code != 200:
                print(f"   Pre-update failed: {update_response.text}")
                return
        
        # Now test the actual problematic transition: "TOP Generated" to "Released"
        print(f"\n4. Testing transition from 'TOP Generated' to 'Released'...")
        
        release_data = {
            "status": "Released",
            "release_reason": "Released to Owner",
            "release_date": "2024-01-15"
        }
        
        release_response = session.put(
            f"{base_url}/api/vehicles/{call_number}",
            json=release_data,
            headers={'Content-Type': 'application/json'}
        )
        
        print(f"   Release update status: {release_response.status_code}")
        print(f"   Response headers: {dict(release_response.headers)}")
        
        if release_response.status_code == 200:
            print("✅ Status update successful!")
            result = release_response.json()
            print(f"   Response: {result}")
        elif release_response.status_code == 401:
            print("❌ Authentication error detected!")
            print(f"   Response: {release_response.text}")
            print(f"   Session cookies: {session.cookies}")
            
            # Check if session is still valid
            print("\n5. Checking session validity...")
            session_check = session.get(f"{base_url}/api/diagnostic")
            print(f"   Session check status: {session_check.status_code}")
            
        else:
            print(f"❌ Unexpected error: {release_response.status_code}")
            print(f"   Response: {release_response.text}")
            
        # Step 6: Test with direct authentication headers
        print("\n6. Testing with explicit authentication...")
        
        # Get current session cookies
        cookies_dict = dict(session.cookies)
        print(f"   Using cookies: {cookies_dict}")
        
        auth_test_response = session.put(
            f"{base_url}/api/vehicles/{call_number}",
            json={"status": "TOP Generated"},  # Reset to original status
            headers={
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            }
        )
        
        print(f"   Auth test status: {auth_test_response.status_code}")
        
        # Step 7: Check server logs for any errors
        print("\n7. Testing auth diagnostics endpoint...")
        
        diag_response = session.get(f"{base_url}/auth-diagnostics")
        print(f"   Diagnostics page status: {diag_response.status_code}")
        
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_auth_status_update()
