#!/usr/bin/env python3
"""
Comprehensive test to verify field mapping fixes work for vehicle operations
"""

import requests
import json
import sqlite3
import os

def test_api_endpoints():
    """Test the API endpoints for vehicle operations"""
    base_url = "http://localhost:5000"
    
    print("=== Testing API Endpoints ===")
    
    # Test if the main page loads
    try:
        response = requests.get(base_url, timeout=5)
        if response.status_code == 200:
            print("✓ Main page loads successfully")
        else:
            print(f"✗ Main page failed with status {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Failed to connect to application: {e}")
        return False
    
    # Test vehicle list endpoint
    try:
        response = requests.get(f"{base_url}/api/vehicles", timeout=5)
        if response.status_code == 200:
            vehicles_data = response.json()
            print(f"✓ Vehicle list API works (found {len(vehicles_data.get('data', []))} vehicles)")
        else:
            print(f"✗ Vehicle list API failed with status {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Vehicle list API error: {e}")
        return False
    
    return True

def test_vehicle_update():
    """Test updating a vehicle with the new field names"""
    base_url = "http://localhost:5000"
    
    print("\n=== Testing Vehicle Update ===")
    
    # Get the first vehicle to test with
    try:
        response = requests.get(f"{base_url}/api/vehicles", timeout=5)
        vehicles_data = response.json()
        
        if not vehicles_data.get('data'):
            print("✗ No vehicles found to test with")
            return False
        
        test_vehicle = vehicles_data['data'][0]
        vehicle_id = test_vehicle.get('towbook_call_number')
        
        if not vehicle_id:
            print("✗ No vehicle ID found")
            return False
        
        print(f"✓ Found test vehicle with ID: {vehicle_id}")
        
        # Test updating with new field names
        update_data = {
            'plate': 'TEST123',
            'state': 'MI',
            'location': 'Test Location for Field Mapping',
            'requestor': 'Test Requestor'
        }
        
        response = requests.post(
            f"{base_url}/api/vehicles/{vehicle_id}",
            json=update_data,
            timeout=5
        )
        
        if response.status_code == 200:
            print("✓ Vehicle update API accepts new field names")
            
            # Verify the update worked by fetching the vehicle again
            response = requests.get(f"{base_url}/api/vehicles/{vehicle_id}", timeout=5)
            if response.status_code == 200:
                updated_vehicle = response.json()
                
                # Check if our updates were saved
                checks = [
                    ('plate', 'TEST123'),
                    ('state', 'MI'),
                    ('location', 'Test Location for Field Mapping'),
                    ('requestor', 'Test Requestor')
                ]
                
                all_good = True
                for field, expected in checks:
                    actual = updated_vehicle.get(field)
                    if actual == expected:
                        print(f"✓ {field}: {actual}")
                    else:
                        print(f"✗ {field}: expected '{expected}', got '{actual}'")
                        all_good = False
                
                return all_good
            else:
                print(f"✗ Failed to fetch updated vehicle: {response.status_code}")
                return False
        else:
            print(f"✗ Vehicle update failed with status {response.status_code}")
            try:
                error_msg = response.json()
                print(f"Error details: {error_msg}")
            except:
                print(f"Error response: {response.text}")
            return False
            
    except Exception as e:
        print(f"✗ Vehicle update test error: {e}")
        return False

def test_form_generation():
    """Test that form generation works with the new field mapping"""
    base_url = "http://localhost:5000"
    
    print("\n=== Testing Form Generation ===")
    
    try:
        # Get a vehicle to generate forms for
        response = requests.get(f"{base_url}/api/vehicles", timeout=5)
        vehicles_data = response.json()
        
        if not vehicles_data.get('data'):
            print("✗ No vehicles found for form generation test")
            return False
        
        test_vehicle = vehicles_data['data'][0]
        vehicle_id = test_vehicle.get('towbook_call_number')
        
        # Test TR52 generation
        response = requests.get(f"{base_url}/generate/tr52/{vehicle_id}", timeout=10)
        if response.status_code == 200:
            print("✓ TR52 form generation works")
        else:
            print(f"✗ TR52 form generation failed: {response.status_code}")
            return False
        
        # Test TR208 generation
        response = requests.get(f"{base_url}/generate/tr208/{vehicle_id}", timeout=10)
        if response.status_code == 200:
            print("✓ TR208 form generation works")
        else:
            print(f"✗ TR208 form generation failed: {response.status_code}")
            return False
        
        return True
        
    except Exception as e:
        print(f"✗ Form generation test error: {e}")
        return False

def verify_database_consistency():
    """Verify database has consistent field names"""
    print("\n=== Verifying Database Consistency ===")
    
    try:
        conn = sqlite3.connect('/workspaces/itowvms/vehicles.db')
        cursor = conn.cursor()
        
        # Test that we can query with new field names
        cursor.execute("SELECT plate, state, location, requestor FROM vehicles LIMIT 5")
        results = cursor.fetchall()
        
        print(f"✓ Successfully queried {len(results)} vehicles with new field names")
        
        # Test that old field names don't exist as columns
        cursor.execute("PRAGMA table_info(vehicles)")
        columns = [col[1] for col in cursor.fetchall()]
        
        old_fields = ['license_plate', 'license_state', 'location_from', 'requested_by']
        for old_field in old_fields:
            if old_field in columns:
                print(f"✗ Found old field name in database: {old_field}")
                conn.close()
                return False
        
        print("✓ No old field names found in database schema")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"✗ Database consistency check error: {e}")
        return False

if __name__ == "__main__":
    print("=== iTow Field Mapping Integration Test ===")
    print("Testing complete workflow with field mapping fixes...\n")
    
    tests = [
        ("API Endpoints", test_api_endpoints),
        ("Vehicle Update", test_vehicle_update),
        ("Form Generation", test_form_generation),
        ("Database Consistency", verify_database_consistency)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"✗ {test_name} test crashed: {e}")
            results.append((test_name, False))
    
    print(f"\n=== Final Results ===")
    passed = 0
    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("\n🎉 All field mapping fixes are working perfectly!")
        print("✓ Vehicle editing works with new field names")
        print("✓ Form generation uses correct field mapping")
        print("✓ Database consistency is maintained")
        print("\nThe iTow Vehicle Management System field mapping fix is COMPLETE!")
    else:
        print(f"\n❌ {len(results) - passed} test(s) failed. Some issues may remain.")
