#!/usr/bin/env python3
"""
Test complete authentication flow including session persistence
"""

import sys
import os
import requests
import time
import subprocess
import signal
from threading import Thread

def start_flask_server():
    """Start the Flask server in background"""
    print("Starting Flask server...")
    env = os.environ.copy()
    env['PYTHONPATH'] = '/workspaces/itowvms'
    
    # Start the server
    process = subprocess.Popen([
        'python3', '-c', 
        """
import sys
sys.path.append('/workspaces/itowvms')
from app import app
app.run(host='0.0.0.0', port=5001, debug=False)
"""
    ], cwd='/workspaces/itowvms', env=env)
    
    # Wait for server to start
    time.sleep(3)
    
    # Check if server is running
    try:
        response = requests.get('http://localhost:5001', timeout=5)
        print("✅ Flask server started successfully")
        return process
    except:
        print("❌ Flask server failed to start")
        process.kill()
        return None

def test_authentication_flow():
    """Test the complete authentication flow"""
    print("\n=== Testing Authentication Flow ===")
    
    base_url = 'http://localhost:5001'
    session = requests.Session()
    
    try:
        # Step 1: Access login page
        print("1. Accessing login page...")
        response = session.get(f'{base_url}/login')
        if response.status_code == 200:
            print("✅ Login page accessible")
        else:
            print(f"❌ Login page error: {response.status_code}")
            return False
        
        # Step 2: Submit login credentials
        print("2. Submitting login credentials...")
        login_data = {
            'username': 'admin',
            'password': 'admin123'
        }
        
        response = session.post(f'{base_url}/login', data=login_data, allow_redirects=False)
        print(f"   Login response status: {response.status_code}")
        print(f"   Login response headers: {dict(response.headers)}")
        print(f"   Session cookies: {session.cookies}")
        
        if response.status_code in [302, 200]:
            print("✅ Login request processed")
        else:
            print(f"❌ Login failed with status: {response.status_code}")
            return False
        
        # Step 3: Follow redirect to check authentication
        if response.status_code == 302:
            redirect_url = response.headers.get('Location', '/')
            print(f"3. Following redirect to: {redirect_url}")
            
            if redirect_url.startswith('/'):
                redirect_url = base_url + redirect_url
            
            response = session.get(redirect_url)
            print(f"   Redirect response status: {response.status_code}")
            print(f"   Session cookies after redirect: {session.cookies}")
        
        # Step 4: Test authenticated API endpoint
        print("4. Testing authenticated API access...")
        api_response = session.get(f'{base_url}/api/vehicles')
        print(f"   API response status: {api_response.status_code}")
        
        if api_response.status_code == 200:
            print("✅ API access successful - authentication working!")
            return True
        elif api_response.status_code == 401:
            print("❌ API access denied - authentication failed")
            return False
        else:
            print(f"❌ API unexpected status: {api_response.status_code}")
            return False
        
    except Exception as e:
        print(f"❌ Test error: {e}")
        return False

def main():
    print("=== Complete Authentication Test ===")
    
    # Start Flask server
    server_process = start_flask_server()
    if not server_process:
        print("❌ Cannot start server - test aborted")
        return
    
    try:
        # Test authentication
        success = test_authentication_flow()
        
        if success:
            print("\n✅ Authentication flow test PASSED!")
            print("The session persistence issue should be resolved.")
        else:
            print("\n❌ Authentication flow test FAILED!")
            print("Session persistence issues remain.")
    
    finally:
        # Clean up server
        print("\nShutting down test server...")
        server_process.terminate()
        server_process.wait()

if __name__ == "__main__":
    main()
