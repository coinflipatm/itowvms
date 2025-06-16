#!/usr/bin/env python3
"""
Test authentication after the database fix
"""
import requests

def test_auth():
    print("="*50)
    print("TESTING AUTHENTICATION")
    print("="*50)
    
    base_url = "http://127.0.0.1:5001"
    
    # Create a session to maintain cookies
    session = requests.Session()
    
    try:
        # 1. Get the login page first (to establish session)
        print("1. Getting login page...")
        login_page = session.get(f"{base_url}/login")
        print(f"   Status: {login_page.status_code}")
        
        # 2. Attempt to login
        print("2. Attempting login...")
        login_data = {
            'username': 'testuser',
            'password': 'password123'
        }
        
        login_response = session.post(f"{base_url}/login", data=login_data, allow_redirects=False)
        print(f"   Login response status: {login_response.status_code}")
        print(f"   Login response headers: {dict(login_response.headers)}")
        
        if login_response.status_code == 302:  # Redirect after successful login
            print("   ✅ Login appears successful (redirect received)")
            
            # 3. Test accessing a protected API endpoint
            print("3. Testing protected API endpoint...")
            api_response = session.get(f"{base_url}/api/vehicles")
            print(f"   API response status: {api_response.status_code}")
            
            if api_response.status_code == 200:
                print("   ✅ API access successful - authentication is working!")
                data = api_response.json()
                print(f"   📊 API returned {len(data)} vehicles")
                return True
            else:
                print(f"   ❌ API access failed: {api_response.status_code}")
                if api_response.headers.get('content-type', '').startswith('application/json'):
                    print(f"   Error details: {api_response.json()}")
        else:
            print(f"   ❌ Login failed or unexpected response")
            print(f"   Response text: {login_response.text[:200]}...")
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False
    
    return False

if __name__ == "__main__":
    success = test_auth()
    if success:
        print("\n🎉 Authentication is working correctly!")
        print("You can now update vehicle info without authentication errors.")
    else:
        print("\n⚠️  Authentication test failed. You may need to:")
        print("1. Check your username/password")
        print("2. Try logging in through the web interface first")
        print("3. Clear your browser cookies")
