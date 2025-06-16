#!/usr/bin/env python3
"""
Test TOP generation functionality
"""
import requests
import json

def test_top_generation():
    print("="*50)
    print("TESTING TOP GENERATION")
    print("="*50)
    
    base_url = "http://127.0.0.1:5001"
    
    # Create a session to maintain cookies
    session = requests.Session()
    
    try:
        # 1. Login first
        print("1. Logging in...")
        login_data = {
            'username': 'testuser',
            'password': 'password123'
        }
        
        login_response = session.post(f"{base_url}/login", data=login_data, allow_redirects=False)
        if login_response.status_code != 302:
            print(f"❌ Login failed: {login_response.status_code}")
            return False
        
        print("✅ Login successful")
        
        # 2. Get list of vehicles to find one to test with
        print("2. Getting vehicle list...")
        vehicles_response = session.get(f"{base_url}/api/vehicles?status=active")
        
        if vehicles_response.status_code != 200:
            print(f"❌ Failed to get vehicles: {vehicles_response.status_code}")
            return False
        
        vehicles = vehicles_response.json()
        print(f"📊 Found {len(vehicles)} vehicles")
        
        if not vehicles:
            print("❌ No vehicles found to test with")
            return False
        
        # Find a vehicle with "New" or "TOP Ready" status for testing
        test_vehicle = None
        for vehicle in vehicles:
            if vehicle.get('status') in ['New', 'TR52 Ready', 'TOP Ready']:
                test_vehicle = vehicle
                break
        
        if not test_vehicle:
            # Just use the first vehicle
            test_vehicle = vehicles[0]
        
        call_number = test_vehicle.get('towbook_call_number')
        print(f"3. Testing TOP generation for vehicle: {call_number}")
        print(f"   Vehicle: {test_vehicle.get('make')} {test_vehicle.get('model')}")
        print(f"   Current Status: {test_vehicle.get('status')}")
        
        # 3. Attempt TOP generation
        top_response = session.post(f"{base_url}/api/generate-top/{call_number}")
        
        print(f"   TOP Generation Response Status: {top_response.status_code}")
        
        if top_response.status_code == 200:
            result = top_response.json()
            print("✅ TOP generation successful!")
            print(f"   Message: {result.get('message')}")
            print(f"   PDF Filename: {result.get('pdf_filename')}")
            print(f"   PDF URL: {result.get('pdf_url')}")
            return True
        else:
            print(f"❌ TOP generation failed!")
            try:
                error_data = top_response.json()
                print(f"   Error: {error_data.get('error')}")
                print(f"   Details: {error_data.get('details')}")
            except:
                print(f"   Response text: {top_response.text[:500]}...")
            return False
            
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_top_generation()
    if success:
        print("\n🎉 TOP generation is working correctly!")
    else:
        print("\n⚠️  TOP generation test failed. Check the logs for more details.")
