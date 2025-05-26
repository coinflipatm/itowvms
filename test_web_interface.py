#!/usr/bin/env python3
"""
Test the complete web interface workflow to reproduce the authentication issue
"""
import requests

def test_web_interface_workflow():
    """Test the complete web interface workflow"""
    session = requests.Session()
    
    print("Step 1: Login through the web interface...")
    
    # First, get the login page to establish a session
    response = session.get("http://localhost:5001/")
    print(f"Home page status: {response.status_code}")
    
    # Login with form data
    login_data = {
        'username': 'admin',
        'password': 'admin123'
    }
    
    login_response = session.post("http://localhost:5001/login", data=login_data)
    print(f"Login response status: {login_response.status_code}")
    print(f"Login response headers: {dict(login_response.headers)}")
    
    # Check if we got set cookies
    print(f"Session cookies: {session.cookies}")
    
    if login_response.status_code == 302:
        print("✅ Login successful (302 redirect)")
    elif login_response.status_code == 200:
        print("✅ Login successful (200 OK)")
    else:
        print(f"❌ Login failed with status {login_response.status_code}")
        print(f"Response text: {login_response.text[:500]}")
        return False
    
    print("\nStep 2: Test vehicle edit API with session...")
    
    # Now try to update a vehicle using the same session that the web interface would use
    update_data = {
        'make': 'TEST MAKE',
        'model': 'TEST MODEL', 
        'year': '2023',
        'color': 'TEST COLOR',
        'notes': 'Web interface test update'
    }
    
    # Test the actual endpoint that the web interface uses
    update_response = session.post(
        "http://localhost:5001/api/vehicle/edit/17643",
        json=update_data,
        headers={'Content-Type': 'application/json'}
    )
    
    print(f"Update response status: {update_response.status_code}")
    print(f"Update response text: {update_response.text}")
    
    if update_response.status_code == 200:
        print("✅ SUCCESS: Web interface workflow works!")
        return True
    elif update_response.status_code == 401:
        print("❌ FAILED: Authentication error in web interface")
        print("This confirms the issue - session not being maintained properly")
        return False
    else:
        print(f"❌ FAILED: Unexpected response {update_response.status_code}")
        return False

if __name__ == "__main__":
    print("Testing web interface authentication workflow...")
    test_web_interface_workflow()
