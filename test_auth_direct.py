#!/usr/bin/env python3
"""
Test authentication directly by examining Flask session behavior
"""

import requests
from requests.sessions import Session
import json

BASE_URL = "http://localhost:5001"
LOGIN_URL = f"{BASE_URL}/login"

def test_login_direct():
    """Test login and examine cookies/session behavior"""
    print("🔍 Testing Login Process Directly...")
    
    session = Session()
    
    # First get the login page to see what happens
    print("\n1. Getting login page...")
    response = session.get(LOGIN_URL)
    print(f"   Status: {response.status_code}")
    print(f"   Cookies after GET: {dict(session.cookies)}")
    print(f"   Response headers: {dict(response.headers)}")
    
    # Look for any form tokens or CSRF tokens
    if 'Set-Cookie' in response.headers:
        print(f"   Set-Cookie header: {response.headers['Set-Cookie']}")
    
    # Try to login
    print("\n2. Attempting login...")
    login_data = {
        'username': 'test_admin',
        'password': 'test123'
    }
    
    response = session.post(LOGIN_URL, data=login_data, allow_redirects=False)
    print(f"   Status: {response.status_code}")
    print(f"   Cookies after POST: {dict(session.cookies)}")
    print(f"   Response headers: {dict(response.headers)}")
    print(f"   Response content preview: {response.text[:500]}...")
    
    if 'Location' in response.headers:
        print(f"   Redirect location: {response.headers['Location']}")
    
    if 'Set-Cookie' in response.headers:
        print(f"   Set-Cookie header: {response.headers['Set-Cookie']}")
    
    # Try following the redirect if there is one
    if response.status_code in [301, 302]:
        print("\n3. Following redirect...")
        redirect_url = response.headers['Location']
        if redirect_url.startswith('/'):
            redirect_url = BASE_URL + redirect_url
        response = session.get(redirect_url)
        print(f"   Status: {response.status_code}")
        print(f"   Cookies after redirect: {dict(session.cookies)}")
    
    # Test accessing main page
    print("\n4. Testing main page access...")
    response = session.get(f"{BASE_URL}/")
    print(f"   Status: {response.status_code}")
    print(f"   Final cookies: {dict(session.cookies)}")
    
    # Test the delete API directly
    print("\n5. Testing DELETE API...")
    response = session.delete(f"{BASE_URL}/api/vehicles/9999")
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.text[:200]}...")
    
    return session

if __name__ == "__main__":
    test_login_direct()
