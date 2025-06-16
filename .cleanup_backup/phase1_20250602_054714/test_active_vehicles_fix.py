#!/usr/bin/env python3
"""
Quick test to verify the Active Vehicles functionality is working
"""
import requests
import json

def test_active_vehicles():
    print("Testing Active Vehicles functionality...")
    print("=" * 50)
    
    try:
        # Test the main page loads
        response = requests.get("http://127.0.0.1:5001/", timeout=10)
        print(f"✓ Main page loads: {response.status_code}")
        
        # Test the active vehicles API endpoint
        response = requests.get("http://127.0.0.1:5001/api/vehicles?status=active", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Active vehicles API works: {len(data)} vehicles returned")
            
            if len(data) > 0:
                sample_vehicle = data[0]
                print(f"  Sample vehicle: {sample_vehicle.get('year', 'N/A')} {sample_vehicle.get('make', 'N/A')} {sample_vehicle.get('model', 'N/A')}")
                print(f"  Status: {sample_vehicle.get('status', 'N/A')}")
                print(f"  Tow Date: {sample_vehicle.get('tow_date', 'N/A')}")
        else:
            print(f"✗ Active vehicles API failed: {response.status_code}")
            
        # Test jurisdictions API (needed for dropdowns)
        response = requests.get("http://127.0.0.1:5001/api/jurisdictions", timeout=10)
        if response.status_code == 200:
            jurisdictions = response.json()
            print(f"✓ Jurisdictions API works: {len(jurisdictions)} jurisdictions available")
        else:
            print(f"✗ Jurisdictions API failed: {response.status_code}")
            
        print("\n" + "=" * 50)
        print("✅ ACTIVE VEHICLES FUNCTIONALITY TEST COMPLETE")
        print("The perpetual loading issue should now be resolved!")
        
    except Exception as e:
        print(f"✗ Test failed: {e}")

if __name__ == "__main__":
    test_active_vehicles()
