#!/usr/bin/env python3
"""
Test to debug the edit modal functionality by checking the vehicle data structure
"""

import sqlite3
import json

def test_vehicle_data_structure():
    """Check what fields are actually available in the vehicle data"""
    print("=== Testing Vehicle Data Structure ===")
    
    conn = sqlite3.connect('/workspaces/itowvms/vehicles.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Get a sample vehicle
    cursor.execute("SELECT * FROM vehicles WHERE towbook_call_number = '18463' LIMIT 1")
    vehicle = cursor.fetchone()
    
    if vehicle:
        print("\nActual database fields and values:")
        vehicle_dict = dict(vehicle)
        for key in sorted(vehicle_dict.keys()):
            value = vehicle_dict[key]
            print(f"  {key}: {value}")
        
        print("\nChecking key fields used in JavaScript:")
        js_fields = [
            'towbook_call_number', 'vin', 'vehicle_year', 'year', 'make', 'model', 
            'color', 'vehicle_type', 'plate', 'state', 'tow_date', 'tow_time', 
            'status', 'location', 'requestor', 'reason_for_tow', 'jurisdiction',
            'officer_name', 'case_number', 'complaint_number', 'owner_name',
            'owner_address', 'owner_phone', 'owner_email', 'lienholder_name',
            'lienholder_address', 'notes'
        ]
        
        for field in js_fields:
            value = vehicle_dict.get(field, 'FIELD NOT FOUND')
            status = "✓" if field in vehicle_dict else "✗"
            print(f"  {status} {field}: {value}")
    else:
        print("No vehicle found with call number 18463")
    
    conn.close()

if __name__ == "__main__":
    test_vehicle_data_structure()
