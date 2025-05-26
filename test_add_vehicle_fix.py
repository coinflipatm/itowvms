#!/usr/bin/env python3
"""
Test the Add Vehicle functionality after fixing log_action parameters
"""

import requests
import json

def test_add_vehicle():
    """Test adding a vehicle via API"""
    url = "http://127.0.0.1:5001/api/vehicles/add"
    
    # Test vehicle data
    test_vehicle = {
        "towbook_call_number": "TEST-2025-001",
        "make": "Ford",
        "model": "Explorer",
        "year": "2023",
        "color": "Blue",
        "plate": "ABC123",
        "state": "CA",
        "vin": "1FMHK8F87NGA12345",
        "vehicle_type": "SUV",
        "tow_date": "2025-05-26",
        "tow_time": "14:30",
        "status": "New",
        "location": "123 Main St",
        "requestor": "Officer Smith",
        "reason_for_tow": "Illegally parked",
        "jurisdiction": "City Police",
        "notes": "Test vehicle for log_action fix verification"
    }
    
    try:
        # First login (assuming we need authentication)
        login_data = {
            'username': 'admin',
            'password': 'admin123'
        }
        
        session = requests.Session()
        login_response = session.post('http://127.0.0.1:5001/login', data=login_data)
        print(f"Login response: {login_response.status_code}")
        
        # Try to add the vehicle
        response = session.post(url, 
                               json=test_vehicle,
                               headers={'Content-Type': 'application/json'})
        
        print(f"Add vehicle response: {response.status_code}")
        print(f"Response text: {response.text}")
        
        if response.status_code in [200, 201]:
            result = response.json()
            print("✅ Vehicle added successfully!")
            print(f"Vehicle ID: {result.get('vehicle_id', 'Unknown')}")
            return True
        else:
            print(f"❌ Failed to add vehicle: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing add vehicle: {str(e)}")
        return False

if __name__ == "__main__":
    print("Testing Add Vehicle functionality after log_action fix...")
    success = test_add_vehicle()
    print(f"\nTest result: {'PASSED' if success else 'FAILED'}")
