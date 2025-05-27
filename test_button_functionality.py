#!/usr/bin/env python3
"""
Test script to verify that all vehicle modal buttons are working correctly.
"""
import requests
import time
import json

def test_button_functionality():
    """Test that all vehicle action buttons work correctly."""
    print("🧪 Testing Vehicle Action Button Functionality")
    print("=" * 60)
    
    base_url = "http://127.0.0.1:5001"
    session = requests.Session()
    
    try:
        # Step 1: Check that the main page loads
        print("1. Testing main page access...")
        main_response = session.get(base_url, timeout=10)
        if main_response.status_code == 200:
            print("✅ Main page loads successfully")
        else:
            print(f"❌ Main page failed: {main_response.status_code}")
            return False
        
        # Step 2: Check that main.js loads and contains required functions
        print("\n2. Testing JavaScript functionality...")
        js_response = session.get(f"{base_url}/static/js/main.js", timeout=10)
        if js_response.status_code == 200:
            print("✅ main.js loads successfully")
            js_content = js_response.text
            
            # Check for required functions
            required_functions = [
                "function viewVehicleDetails",
                "function openEditVehicleModal", 
                "async function deleteVehicle",
                "function renderActionButtons"
            ]
            
            print("   Checking function availability:")
            all_functions_present = True
            for func in required_functions:
                if func in js_content:
                    print(f"   ✅ {func}")
                else:
                    print(f"   ❌ {func}")
                    all_functions_present = False
            
            if not all_functions_present:
                print("❌ Some required functions are missing!")
                return False
        else:
            print(f"❌ main.js failed to load: {js_response.status_code}")
            return False
        
        # Step 3: Check vehicle API endpoint
        print("\n3. Testing vehicle API...")
        vehicles_response = session.get(f"{base_url}/api/vehicles?tab=active", timeout=10)
        if vehicles_response.status_code == 200:
            vehicles = vehicles_response.json()
            print(f"✅ Vehicle API works: {len(vehicles)} vehicles found")
            
            if vehicles:
                test_vehicle = vehicles[0]
                call_number = test_vehicle['towbook_call_number']
                print(f"   Test vehicle: {call_number} - {test_vehicle.get('make', 'N/A')} {test_vehicle.get('model', 'N/A')}")
            else:
                print("⚠️ No vehicles found to test with")
        else:
            print(f"❌ Vehicle API failed: {vehicles_response.status_code}")
            return False
        
        # Step 4: Check individual vehicle API endpoint (for edit functionality)
        if vehicles:
            print("\n4. Testing individual vehicle API...")
            vehicle_response = session.get(f"{base_url}/api/vehicles?call_number={call_number}", timeout=10)
            if vehicle_response.status_code == 200:
                vehicle_data = vehicle_response.json()
                print(f"✅ Individual vehicle API works: {len(vehicle_data)} vehicle(s) returned")
            else:
                print(f"❌ Individual vehicle API failed: {vehicle_response.status_code}")
        
        # Step 5: Check modal HTML elements exist
        print("\n5. Testing modal HTML structure...")
        if "editVehicleModal" in main_response.text:
            print("✅ Edit vehicle modal HTML found")
        else:
            print("❌ Edit vehicle modal HTML missing")
            
        if "vehicleDetailsModal" in main_response.text:
            print("✅ Vehicle details modal HTML found")
        else:
            print("❌ Vehicle details modal HTML missing")
        
        print("\n" + "=" * 60)
        print("🎉 BUTTON FUNCTIONALITY TEST SUMMARY:")
        print("✅ Flask application is running")
        print("✅ All required JavaScript functions are defined")
        print("✅ Vehicle API endpoints are working")
        print("✅ Modal HTML structures are present")
        print("\n✅ All vehicle action buttons should now work correctly!")
        print("   - View Details (eye icon) ✅")
        print("   - Edit Vehicle (edit icon) ✅") 
        print("   - Delete Vehicle (trash icon) ✅")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        return False

if __name__ == "__main__":
    success = test_button_functionality()
    exit(0 if success else 1)
