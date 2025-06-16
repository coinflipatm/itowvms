#!/usr/bin/env python3
"""
Test script for vehicle deletion functionality
"""
import sys
import os
import requests
import json
import sqlite3

# Add the project directory to Python path
sys.path.insert(0, '/workspaces/itowvms')

from database import get_database_path, delete_vehicle_by_call_number
from app import app

def test_database_delete_function():
    """Test the database delete function directly"""
    print("=== Testing Database Delete Function ===")
    
    # Connect directly to SQLite database
    db_path = get_database_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Get a test vehicle (we'll use one that's already released/auctioned)
    cursor.execute("SELECT towbook_call_number FROM vehicles WHERE status IN ('Released', 'Auctioned') LIMIT 1")
    result = cursor.fetchone()
    
    if not result:
        print("No suitable test vehicle found")
        conn.close()
        return False
        
    test_call_number = result['towbook_call_number']
    print(f"Testing deletion of vehicle: {test_call_number}")
    
    # Check vehicle exists before deletion
    cursor.execute("SELECT COUNT(*) as count FROM vehicles WHERE towbook_call_number = ?", (test_call_number,))
    before_count = cursor.fetchone()['count']
    print(f"Vehicle count before deletion: {before_count}")
    
    conn.close()
    
    # Test the delete function within application context
    try:
        with app.app_context():
            success = delete_vehicle_by_call_number(test_call_number)
            print(f"Delete function returned: {success}")
            
            if success:
                # Verify vehicle was deleted
                conn = sqlite3.connect(db_path)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) as count FROM vehicles WHERE towbook_call_number = ?", (test_call_number,))
                after_count = cursor.fetchone()['count']
                print(f"Vehicle count after deletion: {after_count}")
                conn.close()
                
                if after_count == 0:
                    print("✅ Database delete function works correctly!")
                    return True
                else:
                    print("❌ Vehicle still exists after deletion")
                    return False
            else:
                print("❌ Delete function returned False")
                return False
                
    except Exception as e:
        print(f"❌ Error during deletion: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_api_endpoint():
    """Test the API endpoint for deleting vehicles"""
    print("\n=== Testing API Delete Endpoint ===")
    
    # First, we need to login to get session cookies
    base_url = "http://127.0.0.1:5001"
    
    # Create a session to maintain cookies
    session = requests.Session()
    
    try:
        # Get login page to establish session
        login_page = session.get(f"{base_url}/login")
        print(f"Login page status: {login_page.status_code}")
        
        # Try to login (using default admin credentials if they exist)
        login_data = {
            'username': 'admin',
            'password': 'password123'  # This might need to be changed based on actual credentials
        }
        
        login_response = session.post(f"{base_url}/api/login", json=login_data)
        print(f"Login response status: {login_response.status_code}")
        
        if login_response.status_code == 200:
            print("✅ Successfully logged in")
            
            # Get a vehicle to test deletion
            vehicles_response = session.get(f"{base_url}/api/vehicles?tab=released")
            if vehicles_response.status_code == 200:
                vehicles = vehicles_response.json()
                if vehicles and len(vehicles) > 0:
                    test_vehicle = vehicles[0]
                    call_number = test_vehicle['towbook_call_number']
                    print(f"Testing API deletion of vehicle: {call_number}")
                    
                    # Test the delete endpoint
                    delete_response = session.delete(f"{base_url}/api/vehicles/{call_number}")
                    print(f"Delete API response status: {delete_response.status_code}")
                    
                    if delete_response.status_code == 200:
                        response_data = delete_response.json()
                        print(f"Delete API response: {response_data}")
                        print("✅ API delete endpoint works correctly!")
                        return True
                    else:
                        print(f"❌ API delete failed with status: {delete_response.status_code}")
                        try:
                            error_data = delete_response.json()
                            print(f"Error details: {error_data}")
                        except:
                            print(f"Response text: {delete_response.text}")
                        return False
                else:
                    print("❌ No vehicles found to test deletion")
                    return False
            else:
                print(f"❌ Failed to get vehicles: {vehicles_response.status_code}")
                return False
        else:
            print(f"❌ Failed to login: {login_response.status_code}")
            print("Note: You may need to create an admin user or check credentials")
            return False
            
    except Exception as e:
        print(f"❌ Error during API test: {e}")
        return False

def main():
    """Run all delete functionality tests"""
    print("Testing iTow Vehicle Management System - Delete Functionality")
    print("=" * 60)
    
    # Test database function
    db_test_passed = test_database_delete_function()
    
    # Test API endpoint (only if database test passed)
    api_test_passed = False
    if db_test_passed:
        api_test_passed = test_api_endpoint()
    else:
        print("Skipping API test due to database test failure")
    
    print("\n" + "=" * 60)
    print("Test Results Summary:")
    print(f"Database Delete Function: {'✅ PASSED' if db_test_passed else '❌ FAILED'}")
    print(f"API Delete Endpoint: {'✅ PASSED' if api_test_passed else '❌ FAILED'}")
    
    if db_test_passed and api_test_passed:
        print("🎉 All delete functionality tests PASSED!")
        return 0
    else:
        print("❌ Some tests FAILED")
        return 1

if __name__ == "__main__":
    sys.exit(main())
