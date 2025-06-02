#!/usr/bin/env python3
"""
Test current authentication issues to identify what errors remain
"""

import requests
import json
import time

def test_current_auth_issues():
    """Test authentication to identify remaining issues"""
    print("=== Testing Current Authentication Issues ===")
    
    base_url = 'http://localhost:5001'
    session = requests.Session()
    
    try:
        # Test 1: Access main page (should redirect to login)
        print("1. Accessing main page...")
        response = session.get(f'{base_url}/')
        print(f"   Status: {response.status_code}")
        print(f"   URL after redirect: {response.url}")
        print(f"   Cookies: {session.cookies}")
        
        # Test 2: Login attempt
        print("\n2. Attempting login...")
        login_data = {
            'username': 'admin',
            'password': 'admin123'
        }
        
        response = session.post(f'{base_url}/login', data=login_data, allow_redirects=False)
        print(f"   Login status: {response.status_code}")
        print(f"   Login headers: {dict(response.headers)}")
        print(f"   Cookies after login: {session.cookies}")
        
        # Check for session cookie specifically
        session_cookie = None
        for cookie in session.cookies:
            if cookie.name == 'session':
                session_cookie = cookie.value
                break
        
        if session_cookie:
            print(f"   ✅ Session cookie found: {session_cookie[:50]}...")
        else:
            print("   ❌ No session cookie found!")
        
        # Test 3: Follow redirect if login was successful
        if response.status_code == 302:
            redirect_url = response.headers.get('Location', '/')
            print(f"\n3. Following redirect to: {redirect_url}")
            
            if redirect_url.startswith('/'):
                redirect_url = base_url + redirect_url
            
            response = session.get(redirect_url)
            print(f"   Redirect status: {response.status_code}")
            print(f"   Final URL: {response.url}")
        
        # Test 4: Try API call that requires authentication
        print("\n4. Testing authenticated API call...")
        api_response = session.get(f'{base_url}/api/vehicles')
        print(f"   API status: {api_response.status_code}")
        
        if api_response.status_code == 401:
            print("   ❌ API call returned 401 Unauthorized")
            print(f"   Response: {api_response.text[:200]}")
            return False
        elif api_response.status_code == 200:
            print("   ✅ API call successful")
            vehicles = api_response.json()
            print(f"   Found {len(vehicles)} vehicles")
        else:
            print(f"   ⚠️ Unexpected API response: {api_response.status_code}")
            print(f"   Response: {api_response.text[:200]}")
        
        # Test 5: Try vehicle status update
        print("\n5. Testing vehicle status update...")
        
        # Get first vehicle for testing
        if api_response.status_code == 200:
            vehicles = api_response.json()
            if vehicles:
                test_vehicle = vehicles[0]
                vehicle_id = test_vehicle['id']
                current_status = test_vehicle.get('status', 'Unknown')
                
                print(f"   Testing with vehicle ID: {vehicle_id}")
                print(f"   Current status: {current_status}")
                
                # Prepare update data
                update_data = test_vehicle.copy()
                update_data['status'] = 'RELEASED'
                
                # Try to update
                update_response = session.put(
                    f'{base_url}/api/vehicles/{vehicle_id}',
                    json=update_data,
                    headers={'Content-Type': 'application/json'}
                )
                
                print(f"   Update status: {update_response.status_code}")
                
                if update_response.status_code == 401:
                    print("   ❌ Vehicle update returned 401 Unauthorized")
                    print(f"   Response: {update_response.text}")
                    return False
                elif update_response.status_code == 200:
                    print("   ✅ Vehicle update successful")
                    return True
                else:
                    print(f"   ⚠️ Unexpected update response: {update_response.status_code}")
                    print(f"   Response: {update_response.text}")
                    return False
        
        return True
        
    except Exception as e:
        print(f"❌ Test error: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    test_current_auth_issues()

if __name__ == "__main__":
    main()
