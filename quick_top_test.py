#!/usr/bin/env python3
"""
Quick TOP test
"""
import subprocess
import sys

def quick_test():
    print("Testing TOP generation with curl...")
    
    # First login to get session cookie
    login_cmd = [
        'curl', '-c', 'cookies.txt', '-X', 'POST',
        'http://127.0.0.1:5001/login',
        '-d', 'username=testuser',
        '-d', 'password=password123',
        '-L'  # Follow redirects
    ]
    
    print("1. Logging in...")
    result = subprocess.run(login_cmd, capture_output=True, text=True)
    print(f"Login status: {result.returncode}")
    
    # Get a vehicle to test with
    vehicles_cmd = [
        'curl', '-b', 'cookies.txt',
        'http://127.0.0.1:5001/api/vehicles?status=active'
    ]
    
    print("2. Getting vehicles...")
    result = subprocess.run(vehicles_cmd, capture_output=True, text=True)
    if result.returncode == 0:
        try:
            import json
            vehicles = json.loads(result.stdout)
            if vehicles:
                test_vehicle = vehicles[0]
                call_number = test_vehicle.get('towbook_call_number')
                print(f"3. Testing TOP generation for {call_number}...")
                
                # Test TOP generation
                top_cmd = [
                    'curl', '-b', 'cookies.txt', '-X', 'POST',
                    f'http://127.0.0.1:5001/api/generate-top/{call_number}'
                ]
                
                result = subprocess.run(top_cmd, capture_output=True, text=True)
                print(f"TOP generation status: {result.returncode}")
                print(f"Response: {result.stdout[:500]}...")
                
                if "TOP form generated successfully" in result.stdout:
                    print("✅ TOP generation working!")
                else:
                    print("❌ TOP generation failed")
                    print(f"Error output: {result.stderr}")
            else:
                print("No vehicles found")
        except Exception as e:
            print(f"Error parsing response: {e}")
    else:
        print(f"Failed to get vehicles: {result.stderr}")

if __name__ == "__main__":
    quick_test()
