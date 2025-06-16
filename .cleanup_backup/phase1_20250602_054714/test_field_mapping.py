#!/usr/bin/env python3
"""
Test script to verify field mapping fixes in the iTow Vehicle Management System
"""

import sqlite3
import os

def test_database_fields():
    """Test the actual database field names and verify our mapping is correct"""
    db_path = '/workspaces/itowvms/vehicles.db'
    
    if not os.path.exists(db_path):
        print(f"Database file not found: {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get table schema
        cursor.execute("PRAGMA table_info(vehicles)")
        columns = cursor.fetchall()
        
        print(f"Database has {len(columns)} columns")
        print("\nChecking for key fields:")
        
        column_names = [col[1] for col in columns]
        key_fields = ['plate', 'state', 'location', 'requestor']
        
        for field in key_fields:
            if field in column_names:
                col_index = column_names.index(field) + 1
                print(f"✓ '{field}' found at column {col_index}")
            else:
                print(f"✗ '{field}' NOT FOUND")
        
        # Test querying with new field names
        print("\nTesting query with new field names...")
        cursor.execute("SELECT plate, state, location, requestor FROM vehicles LIMIT 1")
        result = cursor.fetchone()
        
        if result:
            print("✓ Query successful with new field names")
            print(f"Sample record: plate={result[0]}, state={result[1]}, location={result[2]}, requestor={result[3]}")
        else:
            print("✗ Query returned no results")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"Error testing database: {e}")
        return False

def test_insert_function():
    """Test that the insert_vehicle function uses correct field names"""
    try:
        with open('/workspaces/itowvms/database.py', 'r') as f:
            content = f.read()
        
        print("\nChecking insert_vehicle function...")
        
        # Find the insert_vehicle function and check its columns list
        insert_function_start = content.find('def insert_vehicle(')
        if insert_function_start == -1:
            print("✗ Could not find insert_vehicle function")
            return False
        
        # Extract the function content (up to the next function or end)
        next_function = content.find('\ndef ', insert_function_start + 1)
        if next_function == -1:
            function_content = content[insert_function_start:]
        else:
            function_content = content[insert_function_start:next_function]
        
        # Check if old field names are in the function
        old_fields = ['license_plate', 'license_state', 'location_from', 'requested_by']
        found_old_fields = []
        
        for field in old_fields:
            if f"'{field}'" in function_content:
                found_old_fields.append(field)
        
        if found_old_fields:
            print(f"✗ Found old field names in insert_vehicle function: {found_old_fields}")
            return False
        else:
            print("✓ No old field names found in insert_vehicle function")
        
        # Check if new field names are present in function
        new_fields = ['plate', 'state', 'location', 'requestor']
        found_new_fields = []
        
        for field in new_fields:
            if f"'{field}'" in function_content:
                found_new_fields.append(field)
        
        if len(found_new_fields) == len(new_fields):
            print(f"✓ All new field names found in insert_vehicle: {found_new_fields}")
            return True
        else:
            missing = set(new_fields) - set(found_new_fields)
            print(f"✗ Missing new field names in insert_vehicle: {missing}")
            return False
            
    except Exception as e:
        print(f"Error checking insert function: {e}")
        return False

if __name__ == "__main__":
    print("=== iTow Field Mapping Test ===")
    
    db_test = test_database_fields()
    insert_test = test_insert_function()
    
    print(f"\n=== Test Results ===")
    print(f"Database field test: {'PASS' if db_test else 'FAIL'}")
    print(f"Insert function test: {'PASS' if insert_test else 'FAIL'}")
    
    if db_test and insert_test:
        print("\n🎉 All field mapping fixes are working correctly!")
    else:
        print("\n❌ Some issues remain to be fixed.")
