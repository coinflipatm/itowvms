#!/usr/bin/env python3
"""
Simple test to verify JavaScript function presence and basic functionality
"""

import requests
import re

def test_javascript_functions():
    print("🧪 Testing JavaScript Function Definitions")
    print("=" * 50)
    
    try:
        # Get the main.js file
        response = requests.get("http://localhost:5001/static/js/main.js")
        if response.status_code != 200:
            print(f"❌ Failed to load main.js: {response.status_code}")
            return False
            
        js_content = response.text
        print("✅ Successfully loaded main.js")
        
        # Check for required functions
        functions_to_check = [
            "function viewVehicleDetails",
            "function openEditVehicleModal", 
            "async function deleteVehicle",
            "function renderActionButtons",
            "function populateJurisdictionDropdowns",
            "function loadJurisdictions"
        ]
        
        all_functions_found = True
        for func in functions_to_check:
            if func in js_content:
                print(f"✅ Found: {func}")
            else:
                print(f"❌ Missing: {func}")
                all_functions_found = False
        
        # Check for proper calls to loadJurisdictions vs populateJurisdictionDropdowns
        print("\n📋 Checking function calls...")
        
        # Check if there are any bad calls to populateJurisdictionDropdowns()
        bad_calls = re.findall(r'populateJurisdictionDropdowns\(\s*\)', js_content)
        if bad_calls:
            print(f"❌ Found {len(bad_calls)} calls to populateJurisdictionDropdowns() without parameters")
            all_functions_found = False
        else:
            print("✅ No bad calls to populateJurisdictionDropdowns() found")
            
        # Check for good calls to loadJurisdictions()
        good_calls = re.findall(r'loadJurisdictions\(\s*\)', js_content)
        print(f"✅ Found {len(good_calls)} calls to loadJurisdictions()")
        
        # Check safety check in populateJurisdictionDropdowns
        if "if (!jurisdictions || !Array.isArray(jurisdictions))" in js_content:
            print("✅ Safety check found in populateJurisdictionDropdowns")
        else:
            print("❌ Safety check missing in populateJurisdictionDropdowns")
            
        return all_functions_found
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        return False

def test_api_endpoints():
    print("\n🔌 Testing API Endpoints")
    print("=" * 30)
    
    try:
        # Test vehicles API
        response = requests.get("http://localhost:5001/api/vehicles")
        if response.status_code == 200:
            vehicles = response.json()
            print(f"✅ Vehicles API works: {len(vehicles)} vehicles")
        else:
            print(f"❌ Vehicles API failed: {response.status_code}")
            return False
            
        # Test jurisdictions API
        response = requests.get("http://localhost:5001/api/jurisdictions")
        if response.status_code == 200:
            jurisdictions = response.json()
            print(f"✅ Jurisdictions API works: {len(jurisdictions)} jurisdictions")
        else:
            print(f"❌ Jurisdictions API failed: {response.status_code}")
            return False
            
        return True
        
    except Exception as e:
        print(f"❌ API test failed: {str(e)}")
        return False

if __name__ == "__main__":
    js_test = test_javascript_functions()
    api_test = test_api_endpoints()
    
    print("\n" + "=" * 50)
    if js_test and api_test:
        print("🎉 ALL TESTS PASSED!")
        print("✅ JavaScript functions are properly defined")
        print("✅ API endpoints are working")
        print("✅ Edit button should work without JavaScript errors")
    else:
        print("❌ SOME TESTS FAILED!")
        if not js_test:
            print("❌ JavaScript function issues detected")
        if not api_test:
            print("❌ API endpoint issues detected")
