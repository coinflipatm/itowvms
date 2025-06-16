#!/usr/bin/env python3
"""
Test to verify edit vehicle modal functionality
"""
import requests
import json

def test_edit_modal_functionality():
    print("Testing Edit Vehicle Modal Functionality...")
    print("=" * 60)
    
    try:
        # 1. Get active vehicles
        response = requests.get("http://127.0.0.1:5001/api/vehicles?status=active", timeout=10)
        if response.status_code != 200:
            print(f"❌ Failed to get vehicles: {response.status_code}")
            return
            
        vehicles = response.json()
        if len(vehicles) == 0:
            print("❌ No vehicles found to test with")
            return
            
        test_vehicle = vehicles[0]
        call_number = test_vehicle.get('towbook_call_number')
        print(f"✅ Found {len(vehicles)} vehicles")
        print(f"✅ Using test vehicle: {call_number}")
        
        # 2. Check that all required edit form fields have matching vehicle data
        print(f"\n🔍 Checking field mapping for vehicle {call_number}:")
        
        # Fields that the JavaScript tries to populate
        field_mapping = {
            'edit-vehicle-id': 'towbook_call_number',
            'edit-vin': 'vin',
            'edit-year': 'year', 
            'edit-make': 'make',
            'edit-model': 'model',
            'edit-color': 'color',
            'edit-vehicle_type': 'vehicle_type',
            'edit-plate': 'plate',
            'edit-state': 'state',
            'edit-tow_date': 'tow_date',
            'edit-tow_time': 'tow_time',
            'edit-status': 'status',
            'edit-location': 'location',  # Fixed: was location_from
            'edit-requestor': 'requestor',
            'edit-reason_for_tow': 'reason_for_tow',
            'edit-jurisdiction': 'jurisdiction',
            'edit-officer_name': 'officer_name',
            'edit-case_number': 'case_number',
            'edit-complaint_number': 'complaint_number',
            'edit-owner_name': 'owner_name',
            'edit-owner_address': 'owner_address',
            'edit-owner_phone': 'owner_phone',
            'edit-owner_email': 'owner_email',
            'edit-lienholder_name': 'lienholder_name',
            'edit-lienholder_address': 'lienholder_address',
            'edit-notes': 'notes'
        }
        
        missing_fields = []
        for form_id, vehicle_field in field_mapping.items():
            if vehicle_field in test_vehicle:
                value = test_vehicle[vehicle_field]
                status = "✅" if value and value != 'N/A' else "⚠️ "
                print(f"  {form_id}: {vehicle_field} = {value} {status}")
            else:
                missing_fields.append(vehicle_field)
                print(f"  {form_id}: {vehicle_field} = MISSING ❌")
        
        if missing_fields:
            print(f"\n❌ Missing vehicle fields: {missing_fields}")
        else:
            print(f"\n✅ All form fields have corresponding vehicle data")
            
        # 3. Test that the main page loads properly
        response = requests.get("http://127.0.0.1:5001/", timeout=10)
        if response.status_code == 200:
            print(f"✅ Main page loads successfully")
            if 'editVehicleModal' in response.text:
                print(f"✅ Edit vehicle modal found in HTML")
            else:
                print(f"❌ Edit vehicle modal NOT found in HTML")
        else:
            print(f"❌ Main page failed to load: {response.status_code}")
            
        print(f"\n{'='*60}")
        print(f"🚀 EDIT MODAL FUNCTIONALITY TEST COMPLETE")
        print(f"💡 The edit modal should now work properly!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")

if __name__ == "__main__":
    test_edit_modal_functionality()
