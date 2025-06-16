#!/usr/bin/env python3
"""
Test the specific vehicle status update that was failing
"""

import requests
import json
import time
import subprocess

def start_server():
    """Start Flask server"""
    print("Starting Flask server...")
    process = subprocess.Popen([
        'python3', '-c', 
        """
import sys
sys.path.append('/workspaces/itowvms')
from app import app
app.run(host='0.0.0.0', port=5002, debug=False)
"""
    ], cwd='/workspaces/itowvms')
    
    time.sleep(3)
    return process

def test_vehicle_status_update():
    """Test updating vehicle status from TOP Generated to RELEASED"""
    print("=== Testing Vehicle Status Update ===")
    
    base_url = 'http://localhost:5002'
    session = requests.Session()
    
    try:
        # Step 1: Login
        print("1. Logging in...")
        login_data = {
            'username': 'admin',
            'password': 'admin123'
        }
        
        response = session.post(f'{base_url}/login', data=login_data)
        if response.status_code != 200:
            print(f"❌ Login failed: {response.status_code}")
            return False
        print("✅ Login successful")
        
        # Step 2: Get vehicles to find one with "TOP Generated" status
        print("2. Fetching vehicles...")
        response = session.get(f'{base_url}/api/vehicles')
        if response.status_code != 200:
            print(f"❌ Failed to fetch vehicles: {response.status_code}")
            return False
        
        vehicles = response.json()
        print(f"✅ Found {len(vehicles)} vehicles")
        
        # Find a vehicle with "TOP Generated" status
        target_vehicle = None
        for vehicle in vehicles:
            if vehicle.get('status') == 'TOP Generated':
                target_vehicle = vehicle
                break
        
        if not target_vehicle:
            print("ℹ️  No vehicle with 'TOP Generated' status found. Creating test scenario...")
            # Find any vehicle and update it to TOP Generated first
            if vehicles:
                target_vehicle = vehicles[0]
                print(f"   Using vehicle: {target_vehicle.get('call_number', 'Unknown')}")
                
                # Update to TOP Generated first
                update_data = target_vehicle.copy()
                update_data['status'] = 'TOP Generated'
                
                response = session.put(
                    f"{base_url}/api/vehicles/{target_vehicle['id']}", 
                    json=update_data,
                    headers={'Content-Type': 'application/json'}
                )
                
                if response.status_code != 200:
                    print(f"❌ Failed to set TOP Generated status: {response.status_code}")
                    print(f"   Response: {response.text}")
                    return False
                print("✅ Set vehicle to 'TOP Generated' status")
            else:
                print("❌ No vehicles found to test with")
                return False
        
        # Step 3: Update status from "TOP Generated" to "RELEASED"
        print("3. Updating vehicle status to RELEASED...")
        
        update_data = target_vehicle.copy()
        update_data['status'] = 'RELEASED'
        
        print(f"   Vehicle ID: {target_vehicle['id']}")
        print(f"   Call Number: {target_vehicle.get('call_number', 'Unknown')}")
        print(f"   Current Status: {target_vehicle.get('status', 'Unknown')}")
        print(f"   Target Status: RELEASED")
        
        response = session.put(
            f"{base_url}/api/vehicles/{target_vehicle['id']}", 
            json=update_data,
            headers={'Content-Type': 'application/json'}
        )
        
        print(f"   Update response status: {response.status_code}")
        print(f"   Update response text: {response.text[:200]}...")
        
        if response.status_code == 200:
            print("✅ Vehicle status update successful!")
            
            # Verify the update
            verification_response = session.get(f"{base_url}/api/vehicles/{target_vehicle['id']}")
            if verification_response.status_code == 200:
                updated_vehicle = verification_response.json()
                if updated_vehicle.get('status') == 'RELEASED':
                    print("✅ Status update verified - vehicle is now RELEASED")
                    return True
                else:
                    print(f"❌ Status verification failed - status is: {updated_vehicle.get('status')}")
                    return False
            else:
                print(f"❌ Verification failed: {verification_response.status_code}")
                return False
        else:
            print(f"❌ Vehicle status update failed: {response.status_code}")
            print(f"   Error details: {response.text}")
            return False
        
    except Exception as e:
        print(f"❌ Test error: {e}")
        return False

def main():
    print("=== Vehicle Status Update Test ===")
    
    server_process = start_server()
    
    try:
        success = test_vehicle_status_update()
        
        if success:
            print("\n🎉 SUCCESS! Vehicle status update is working correctly!")
            print("The authentication error has been resolved.")
        else:
            print("\n❌ FAILED! Vehicle status update still has issues.")
    
    finally:
        print("\nShutting down test server...")
        server_process.terminate()
        server_process.wait()

if __name__ == "__main__":
    main()
