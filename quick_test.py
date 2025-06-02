#!/usr/bin/env python3
"""
Quick test to verify authentication fix works
"""

import requests
import time
import subprocess
import signal
import os

def test_quick():
    """Quick authentication test"""
    print("=== Quick Authentication Test ===")
    
    # Start server
    print("Starting server...")
    process = subprocess.Popen([
        'python3', 'app.py'
    ], cwd='/workspaces/itowvms')
    
    time.sleep(5)  # Wait for server
    
    try:
        session = requests.Session()
        
        # Test login
        print("Testing login...")
        response = session.post('http://localhost:5000/login', data={
            'username': 'admin',
            'password': 'admin123'
        }, timeout=10)
        
        print(f"Login status: {response.status_code}")
        print(f"Cookies: {session.cookies}")
        
        # Test API access
        print("Testing API access...")
        api_response = session.get('http://localhost:5000/api/vehicles', timeout=10)
        print(f"API status: {api_response.status_code}")
        
        if api_response.status_code == 200:
            print("✅ Authentication is working!")
            return True
        else:
            print("❌ Authentication still failing")
            return False
            
    except Exception as e:
        print(f"Error: {e}")
        return False
    finally:
        process.terminate()
        time.sleep(1)
        process.kill()

if __name__ == "__main__":
    test_quick()
