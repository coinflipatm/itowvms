#!/usr/bin/env python3
"""
Test vehicle status update functionality specifically for authentication errors
"""

import requests
import json

def test_auth_and_update():
    """Test authentication and vehicle update"""
    print("=== Testing Authentication and Vehicle Update ===")
    
    base_url = 'http://localhost:5001'
    session = requests.Session()
    
    # Test 1: Login
    print("1. Testing login...")
    login_response = session.post(f'{base_url}/login', data={
        'username': 'admin',
        'password': 'admin123'
    }, allow_redirects=False)
    
    print(f"   Login status: {login_response.status_code}")
    
    # Check for session cookie
    session_found = False
    for cookie in session.cookies:
        if cookie.name == 'session':
            session_found = True
            print(f"   ✅ Session cookie set: {cookie.value[:50]}...")
            break
    
    if not session_found:
        print("   ❌ No session cookie found after login!")
        return
    
    # Test 2: API access
    print("\n2. Testing API access...")
    api_response = session.get(f'{base_url}/api/vehicles')
    print(f"   API status: {api_response.status_code}")
    
    if api_response.status_code == 401:
        print("   ❌ API returns 401 - Authentication failed!")
        print(f"   Response: {api_response.text}")
        return
    elif api_response.status_code != 200:
        print(f"   ⚠️ Unexpected API response: {api_response.status_code}")
        print(f"   Response: {api_response.text}")
        return
    
    print("   ✅ API access successful")
    
    # Test 3: Check available API endpoints
    print("\n3. Checking available endpoints...")
    test_endpoints = [
        '/api/vehicles',
        '/api/vehicle',
        '/update_vehicle_status',
        '/api/update_vehicle'
    ]
    
    for endpoint in test_endpoints:
        test_response = session.get(f'{base_url}{endpoint}')
        print(f"   {endpoint}: {test_response.status_code}")
    
    # Test 4: Get vehicle data structure
    vehicles = api_response.json()
    print(f"\n4. Vehicle data analysis...")
    print(f"   Total vehicles: {len(vehicles)}")
    
    if vehicles:
        first_vehicle = vehicles[0]
        print(f"   Sample vehicle keys: {list(first_vehicle.keys())}")
        
        # Look for vehicles with "TOP Generated" status
        top_generated_vehicles = [v for v in vehicles if v.get('status') == 'TOP Generated']
        print(f"   Vehicles with 'TOP Generated' status: {len(top_generated_vehicles)}")
        
        if top_generated_vehicles:
            test_vehicle = top_generated_vehicles[0]
            print(f"   Test vehicle fields: {test_vehicle}")
            
            # Test status update
            print("\n5. Testing status update...")
            update_data = test_vehicle.copy()
            update_data['status'] = 'RELEASED'
            
            # Check what field to use as ID
            vehicle_id = None
            for id_field in ['id', 'case_number', 'vin', 'plate']:
                if id_field in test_vehicle:
                    vehicle_id = test_vehicle[id_field]
                    print(f"   Using {id_field} as ID: {vehicle_id}")
                    break
            
            if vehicle_id:
                # Try different update methods
                update_methods = [
                    ('PUT', f'/api/vehicles/{vehicle_id}'),
                    ('POST', f'/api/vehicles/{vehicle_id}'),
                    ('PUT', f'/update_vehicle_status'),
                    ('POST', f'/update_vehicle_status')
                ]
                
                for method, endpoint in update_methods:
                    print(f"   Trying {method} {endpoint}...")
                    
                    if method == 'PUT':
                        response = session.put(f'{base_url}{endpoint}', json=update_data)
                    else:
                        response = session.post(f'{base_url}{endpoint}', json=update_data)
                    
                    print(f"   Status: {response.status_code}")
                    
                    if response.status_code == 401:
                        print("   ❌ AUTHENTICATION ERROR FOUND!")
                        print(f"   Response: {response.text}")
                        print(f"   Headers: {dict(response.headers)}")
                        return False
                    elif response.status_code == 200:
                        print("   ✅ Update successful!")
                        return True
                    elif response.status_code == 404:
                        print("   Endpoint not found")
                    else:
                        print(f"   Response: {response.text}")
        else:
            print("   No vehicles with 'TOP Generated' status found for testing")
    
    print("\n✅ No authentication errors found!")
    return True

if __name__ == "__main__":
    test_auth_and_update()
