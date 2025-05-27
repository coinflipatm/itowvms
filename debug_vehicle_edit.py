#!/usr/bin/env python3
"""
Test script to debug the edit vehicle modal issue
"""
import requests
import json

def debug_vehicle_edit():
    print("Debugging Vehicle Edit Modal Issue...")
    print("=" * 50)
    
    try:
        # Get a sample vehicle to see the actual field names
        response = requests.get("http://127.0.0.1:5001/api/vehicles?status=active", timeout=10)
        if response.status_code == 200:
            vehicles = response.json()
            if len(vehicles) > 0:
                sample_vehicle = vehicles[0]
                print(f"Sample vehicle fields:")
                for key, value in sample_vehicle.items():
                    if value is not None and value != '':
                        print(f"  {key}: {value}")
                
                print(f"\nCall number for testing: {sample_vehicle.get('towbook_call_number', 'N/A')}")
                
                # Check which location field exists
                location_fields = [k for k in sample_vehicle.keys() if 'location' in k.lower()]
                print(f"Location-related fields: {location_fields}")
                
        else:
            print(f"Failed to get vehicles: {response.status_code}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    debug_vehicle_edit()
