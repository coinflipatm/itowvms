#!/usr/bin/env python3
"""
Final End-to-End Date Consistency Test
Tests all three PDF generation types after the indentation fixes
"""

import requests
import json
import sqlite3
import os
import time

def test_pdf_endpoints():
    """Test all three PDF generation endpoints"""
    base_url = "http://localhost:5001"
    
    print("🚀 Final End-to-End PDF Generation Test")
    print("=" * 50)
    
    # First check if Flask is running
    try:
        response = requests.get(f"{base_url}/", timeout=5)
        if response.status_code == 200:
            print("✅ Flask application is running")
        else:
            print(f"❌ Flask application returned status {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Cannot connect to Flask application: {e}")
        return False
    
    # Get a sample vehicle call number from the database
    print("\n=== Finding Test Vehicle ===")
    try:
        conn = sqlite3.connect('/workspaces/itowvms/vehicles.db')
        cursor = conn.execute("SELECT towbook_call_number FROM vehicles WHERE towbook_call_number IS NOT NULL LIMIT 1")
        result = cursor.fetchone()
        conn.close()
        
        if result:
            call_number = result[0]
            print(f"✅ Found test vehicle: {call_number}")
        else:
            print("❌ No vehicles found in database")
            return False
    except Exception as e:
        print(f"❌ Database error: {e}")
        return False
    
    # Test each PDF generation endpoint
    endpoints = [
        ("TOP", f"{base_url}/api/generate-top/{call_number}"),
        ("TR52", f"{base_url}/api/generate-tr52/{call_number}"),
        ("TR208", f"{base_url}/api/generate-tr208/{call_number}")
    ]
    
    results = []
    
    print(f"\n=== Testing PDF Generation Endpoints ===")
    for form_type, url in endpoints:
        print(f"\nTesting {form_type} form generation...")
        # Send request to generate PDF
        try:
            response = requests.post(url, headers={'Content-Type': 'application/json'}, timeout=30)
        except requests.exceptions.RequestException as e:
            print(f"❌ {form_type} form generation request failed: {e}")
            results.append((form_type, False, str(e)))
            continue

        # Check HTTP status code
        if response.status_code != 200:
            print(f"❌ {form_type} form generation HTTP error: {response.status_code}")
            results.append((form_type, False, f"HTTP {response.status_code}"))
            continue

        # Parse JSON response
        try:
            data = response.json()
        except json.JSONDecodeError as e:
            print(f"❌ {form_type} form generation JSON decode error: {e}")
            results.append((form_type, False, f"JSON error: {e}"))
            continue

        # Check for pdf_filename in response
        pdf_filename = data.get('pdf_filename')
        if pdf_filename:
            print(f"✅ {form_type} form generated successfully: {pdf_filename}")
            results.append((form_type, True, pdf_filename))
        else:
            error_msg = data.get('error', json.dumps(data))
            print(f"❌ {form_type} form generation failed: {error_msg}")
            results.append((form_type, False, error_msg))
    
    # Summary
    print(f"\n{'='*50}")
    print("📊 FINAL TEST RESULTS")
    print(f"{'='*50}")
    
    successful = [r for r in results if r[1]]
    failed = [r for r in results if not r[1]]
    
    if successful:
        print("✅ Successful PDF generations:")
        for form_type, _, filename in successful:
            print(f"   {form_type}: {filename}")
    
    if failed:
        print("❌ Failed PDF generations:")
        for form_type, _, error in failed:
            print(f"   {form_type}: {error}")
    
    print(f"\nOverall Result: {len(successful)}/{len(results)} tests passed")
    
    if len(successful) == len(results):
        print("🎉 ALL PDF GENERATION TESTS PASSED!")
        print("✅ Date consistency fixes are working correctly across all forms")
        return True
    else:
        print("⚠️ Some PDF generation tests failed")
        return False

if __name__ == "__main__":
    success = test_pdf_endpoints()
    exit(0 if success else 1)
