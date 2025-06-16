#!/usr/bin/env python3
"""
Comprehensive test for the complete delete vehicle functionality.
Tests the entire flow: authentication → get vehicle list → delete vehicle → verify deletion
"""

import requests
import sqlite3
import json
import time
from requests.sessions import Session

# Configuration
BASE_URL = "http://localhost:5001"
LOGIN_URL = f"{BASE_URL}/login"
API_BASE = f"{BASE_URL}/api"
VEHICLES_URL = f"{API_BASE}/vehicles"

# Test credentials (from previous analysis)
ADMIN_USERNAME = "test_admin"
ADMIN_PASSWORD = "test123"

def create_test_vehicle():
    """Create a test vehicle for deletion testing"""
    conn = sqlite3.connect('/workspaces/itowvms/vehicles.db')
    cursor = conn.cursor()
    
    # Create a test vehicle with a unique call number
    test_call_number = "9999"
    cursor.execute("""
        INSERT OR REPLACE INTO vehicles (
            towbook_call_number, invoice_number, plate, make, model, color, year,
            tow_date, tow_time, status, jurisdiction
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        test_call_number, "TEST001", "TEST123", "Toyota", "Camry", "Blue", "2020",
        "2024-01-15", "14:30", "New", "Test Jurisdiction"
    ))
    
    conn.commit()
    conn.close()
    print(f"✅ Created test vehicle with call number: {test_call_number}")
    return test_call_number

def check_vehicle_exists(call_number):
    """Check if a vehicle exists in the database"""
    conn = sqlite3.connect('/workspaces/itowvms/vehicles.db')
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM vehicles WHERE towbook_call_number = ?", (call_number,))
    count = cursor.fetchone()[0]
    
    conn.close()
    return count > 0

def test_authentication():
    """Test authentication flow and return session with cookies"""
    print("\n🔐 Testing Authentication...")
    
    session = Session()
    
    # First, get the login page to establish session
    try:
        response = session.get(LOGIN_URL, timeout=10)
        print(f"Login page status: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ Login page accessible")
            print(f"Session cookies after GET: {session.cookies}")
        else:
            print(f"❌ Login page returned status {response.status_code}")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Error accessing login page: {e}")
        return None
    
    # Try to login with form data
    login_data = {
        'username': ADMIN_USERNAME,
        'password': ADMIN_PASSWORD
    }
    
    try:
        response = session.post(LOGIN_URL, data=login_data, timeout=10, allow_redirects=True)
        print(f"Login POST status: {response.status_code}")
        print(f"Final URL after login: {response.url}")
        print(f"Session cookies after POST: {session.cookies}")
        
        # Check if we were redirected (successful login usually redirects)
        if response.status_code == 302 or 'dashboard' in response.url or response.status_code == 200:
            print("✅ Login appears successful")
            
            # Test that we can access a protected page
            main_page_response = session.get(f"{BASE_URL}/", timeout=10)
            print(f"Main page access test: {main_page_response.status_code}")
            
            return session
        else:
            print(f"❌ Login failed - Status: {response.status_code}")
            print(f"Response URL: {response.url}")
            print(f"Response text preview: {response.text[:200]}...")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Error during login: {e}")
        return None

def test_get_vehicles(session):
    """Test getting the vehicle list via API"""
    print("\n📋 Testing Vehicle List API...")
    
    try:
        response = session.get(VEHICLES_URL, timeout=10)
        print(f"Vehicles API status: {response.status_code}")
        
        if response.status_code == 200:
            try:
                vehicles = response.json()
                print(f"✅ Got {len(vehicles)} vehicles from API")
                return vehicles
            except json.JSONDecodeError:
                print("❌ Invalid JSON response from vehicles API")
                print(f"Response content: {response.text[:200]}...")
                return None
        else:
            print(f"❌ Vehicles API failed - Status: {response.status_code}")
            print(f"Response: {response.text[:200]}...")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Error accessing vehicles API: {e}")
        return None

def test_delete_vehicle(session, call_number):
    """Test deleting a vehicle via API"""
    print(f"\n🗑️ Testing Vehicle Deletion (Call Number: {call_number})...")
    
    delete_url = f"{VEHICLES_URL}/{call_number}"
    print(f"DELETE URL: {delete_url}")
    print(f"Session cookies: {session.cookies}")
    
    # Add explicit headers to ensure session is maintained
    headers = {
        'Content-Type': 'application/json',
        'X-Requested-With': 'XMLHttpRequest'
    }
    
    try:
        response = session.delete(delete_url, headers=headers, timeout=10)
        print(f"Delete API status: {response.status_code}")
        print(f"Delete response headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            try:
                result = response.json()
                print(f"✅ Delete API response: {result}")
                return result.get('success', False)
            except json.JSONDecodeError:
                print("✅ Delete successful (non-JSON response)")
                return True
        elif response.status_code == 401:
            print("❌ Authentication failed for DELETE request")
            print(f"Response: {response.text[:200]}...")
            
            # Let's try to re-authenticate and retry
            print("🔄 Attempting to re-authenticate...")
            test_auth = test_authentication()
            if test_auth:
                print("🔄 Retrying delete with fresh session...")
                retry_response = test_auth.delete(delete_url, headers=headers, timeout=10)
                print(f"Retry delete status: {retry_response.status_code}")
                if retry_response.status_code == 200:
                    result = retry_response.json()
                    print(f"✅ Delete successful on retry: {result}")
                    return result.get('success', False)
            
            return False
        elif response.status_code == 404:
            print("❌ Vehicle not found")
            return False
        else:
            print(f"❌ Delete failed - Status: {response.status_code}")
            print(f"Response: {response.text[:200]}...")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Error during delete: {e}")
        return False

def main():
    """Run the complete delete functionality test"""
    print("🚀 Starting Complete Delete Functionality Test")
    print("=" * 50)
    
    # Step 1: Create test vehicle
    test_call_number = create_test_vehicle()
    
    # Verify test vehicle exists
    if not check_vehicle_exists(test_call_number):
        print("❌ Failed to create test vehicle")
        return False
    
    # Step 2: Test authentication
    session = test_authentication()
    if not session:
        print("❌ Authentication failed - cannot continue")
        return False
    
    # Step 3: Test vehicle list API
    vehicles = test_get_vehicles(session)
    if vehicles is None:
        print("❌ Vehicle list API failed - cannot continue")
        return False
    
    # Check if our test vehicle is in the list
    test_vehicle_found = any(v.get('towbook_call_number') == test_call_number for v in vehicles)
    if test_vehicle_found:
        print(f"✅ Test vehicle {test_call_number} found in API response")
    else:
        print(f"⚠️ Test vehicle {test_call_number} not found in API response")
    
    # Step 4: Test vehicle deletion
    delete_success = test_delete_vehicle(session, test_call_number)
    
    # Step 5: Verify deletion in database
    if delete_success:
        time.sleep(1)  # Give a moment for database to update
        if not check_vehicle_exists(test_call_number):
            print(f"✅ Vehicle {test_call_number} successfully deleted from database")
            print("\n🎉 COMPLETE DELETE FUNCTIONALITY TEST PASSED!")
            return True
        else:
            print(f"❌ Vehicle {test_call_number} still exists in database after API delete")
            return False
    else:
        print("❌ Delete API call failed")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
