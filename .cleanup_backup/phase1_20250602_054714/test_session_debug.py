#!/usr/bin/env python3
"""
Test Flask session configuration directly
"""
import requests
from requests.sessions import Session

def test_session_functionality():
    print("Testing Flask Session Configuration")
    print("=" * 50)
    
    base_url = "http://127.0.0.1:5001"
    session = Session()
    
    # Test 1: Check if session cookies are being set at all
    print("1. Testing basic session cookie setting...")
    
    # Access main page first
    response = session.get(f"{base_url}/")
    print(f"   Main page status: {response.status_code}")
    print(f"   Cookies after main page: {dict(session.cookies)}")
    print(f"   Set-Cookie headers: {response.headers.get('Set-Cookie', 'None')}")
    
    # Test 2: Check login page
    print("\n2. Testing login page...")
    login_response = session.get(f"{base_url}/login")
    print(f"   Login page status: {login_response.status_code}")
    print(f"   Cookies after login page: {dict(session.cookies)}")
    print(f"   Set-Cookie headers: {login_response.headers.get('Set-Cookie', 'None')}")
    
    # Test 3: Test login with correct credentials
    print("\n3. Testing login POST...")
    login_data = {
        'username': 'admin',
        'password': 'admin123'
    }
    
    post_response = session.post(
        f"{base_url}/login", 
        data=login_data, 
        allow_redirects=False
    )
    
    print(f"   Login POST status: {post_response.status_code}")
    print(f"   Cookies after login POST: {dict(session.cookies)}")
    print(f"   Set-Cookie headers: {post_response.headers.get('Set-Cookie', 'None')}")
    print(f"   Location header: {post_response.headers.get('Location', 'None')}")
    
    # Test 4: Follow redirect and check session persistence
    if post_response.status_code in [301, 302]:
        print("\n4. Following redirect...")
        redirect_response = session.get(f"{base_url}/")
        print(f"   Redirect status: {redirect_response.status_code}")
        print(f"   Cookies after redirect: {dict(session.cookies)}")
        
        # Test 5: Try API call with session
        print("\n5. Testing API call with session...")
        api_response = session.get(f"{base_url}/api/diagnostic")
        print(f"   API diagnostic status: {api_response.status_code}")
        
        if api_response.status_code == 200:
            print("   ✅ Session is working - user is authenticated")
        elif api_response.status_code == 401:
            print("   ❌ Session not working - authentication failed")
            print(f"   Response: {api_response.text}")
        else:
            print(f"   ⚠️ Unexpected response: {api_response.status_code}")
    
    # Test 6: Debug the session directly by checking Flask's debug endpoint
    print("\n6. Testing session persistence with vehicle update...")
    
    # Get a vehicle first
    vehicles_response = session.get(f"{base_url}/api/vehicles?status=active")
    print(f"   Vehicles API status: {vehicles_response.status_code}")
    
    if vehicles_response.status_code == 200:
        vehicles = vehicles_response.json()
        if vehicles:
            test_vehicle = vehicles[0]
            call_number = test_vehicle['towbook_call_number']
            
            # Try updating the vehicle status
            update_data = {"status": "TOP Generated", "make": "TEST"}
            update_response = session.put(
                f"{base_url}/api/vehicles/{call_number}",
                json=update_data,
                headers={'Content-Type': 'application/json'}
            )
            
            print(f"   Vehicle update status: {update_response.status_code}")
            if update_response.status_code == 401:
                print("   ❌ Authentication failed on vehicle update")
                print(f"   Response: {update_response.text}")
            elif update_response.status_code == 200:
                print("   ✅ Vehicle update successful - authentication working")
            else:
                print(f"   ⚠️ Unexpected update response: {update_response.status_code}")
                print(f"   Response: {update_response.text}")

if __name__ == "__main__":
    test_session_functionality()
