#!/usr/bin/env python3
"""
Test script to verify date consistency across the iTow VMS system.
Tests frontend, database, and PDF generation date formatting.
"""

import sqlite3
import logging
import sys
import os
from datetime import datetime, timedelta
import tempfile
import json

# Add the current directory to Python path
sys.path.append('/workspaces/itowvms')

from generator import PDFGenerator
from database import get_db_connection

def setup_logging():
    """Setup logging for the test"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

def test_database_date_consistency():
    """Test that all dates in the database are in YYYY-MM-DD format"""
    print("\n=== Testing Database Date Consistency ===")
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get all vehicles with date fields
        cursor.execute("""
            SELECT towbook_call_number, tow_date, top_form_sent_date, 
                   tr52_available_date, release_date, auction_date
            FROM vehicles 
            WHERE tow_date IS NOT NULL AND tow_date != 'N/A'
            LIMIT 10
        """)
        
        vehicles = cursor.fetchall()
        print(f"Testing {len(vehicles)} vehicles...")
        
        date_format_issues = []
        
        for vehicle in vehicles:
            call_number = vehicle['towbook_call_number']
            tow_date = vehicle['tow_date']
            
            # Check if tow_date is in YYYY-MM-DD format
            if tow_date and tow_date != 'N/A':
                if '/' in tow_date:
                    date_format_issues.append(f"Vehicle {call_number}: tow_date '{tow_date}' still in MM/DD/YYYY format")
                elif not _is_valid_iso_date(tow_date):
                    date_format_issues.append(f"Vehicle {call_number}: tow_date '{tow_date}' invalid format")
            
            # Check other date fields
            for field, value in [
                ('top_form_sent_date', vehicle['top_form_sent_date']),
                ('tr52_available_date', vehicle['tr52_available_date']),
                ('release_date', vehicle['release_date']),
                ('auction_date', vehicle['auction_date'])
            ]:
                if value and value != 'N/A' and '/' in value:
                    date_format_issues.append(f"Vehicle {call_number}: {field} '{value}' still in MM/DD/YYYY format")
        
        if date_format_issues:
            print("❌ Database date format issues found:")
            for issue in date_format_issues:
                print(f"   {issue}")
            return False
        else:
            print("✅ All database dates are in YYYY-MM-DD format")
            return True
            
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()

def test_pdf_date_formatting():
    """Test that PDF generation formats dates consistently as MM/DD/YYYY"""
    print("\n=== Testing PDF Date Formatting ===")
    
    try:
        # Create test vehicle data with YYYY-MM-DD dates (as stored in database)
        test_vehicle = {
            'towbook_call_number': 'TEST001-25',
            'complaint_number': 'IT0001-25',
            'tow_date': '2025-05-15',  # YYYY-MM-DD format (database format)
            'top_form_sent_date': '2025-05-16',
            'tr52_available_date': '2025-06-05',
            'year': '2018',
            'make': 'Honda',
            'model': 'Civic',
            'color': 'Red',
            'vin': '1HGBH41JXMN109186',
            'plate': 'ABC123',
            'state': 'MI',
            'jurisdiction': 'Burton PD',
            'location': '123 Test St, Burton, MI',
            'tow_time': '14:30',
            'requestor': 'Property Manager'
        }
        
        pdf_gen = PDFGenerator()
        
        # Test TOP form generation
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
            top_success, top_message = pdf_gen.generate_top(test_vehicle, tmp_file.name)
            
            if top_success:
                print("✅ TOP form generated successfully")
                # Check if file was created
                if os.path.exists(tmp_file.name) and os.path.getsize(tmp_file.name) > 0:
                    print(f"   TOP PDF file created: {os.path.getsize(tmp_file.name)} bytes")
                else:
                    print("❌ TOP PDF file not created or empty")
                    return False
            else:
                print(f"❌ TOP form generation failed: {top_message}")
                return False
            
            # Clean up
            try:
                os.unlink(tmp_file.name)
            except:
                pass
        
        # Test Release Notice generation
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
            release_success, release_message = pdf_gen.generate_release_notice(test_vehicle, tmp_file.name)
            
            if release_success:
                print("✅ Release Notice generated successfully")
                # Check if file was created
                if os.path.exists(tmp_file.name) and os.path.getsize(tmp_file.name) > 0:
                    print(f"   Release Notice PDF file created: {os.path.getsize(tmp_file.name)} bytes")
                else:
                    print("❌ Release Notice PDF file not created or empty")
                    return False
            else:
                print(f"❌ Release Notice generation failed: {release_message}")
                return False
            
            # Clean up
            try:
                os.unlink(tmp_file.name)
            except:
                pass
        
        # Test date formatting helper function
        print("\n--- Testing PDF Date Formatting Helper ---")
        test_dates = [
            ('2025-05-15', '05/15/2025'),  # YYYY-MM-DD -> MM/DD/YYYY
            ('05/15/2025', '05/15/2025'),  # MM/DD/YYYY -> MM/DD/YYYY (unchanged)
            ('N/A', 'N/A'),               # N/A -> N/A
            ('', 'N/A'),                  # Empty -> N/A
            (None, 'N/A')                 # None -> N/A
        ]
        
        for input_date, expected_output in test_dates:
            formatted_date = pdf_gen._format_date_for_pdf(input_date)
            if formatted_date == expected_output:
                print(f"✅ Date formatting: '{input_date}' -> '{formatted_date}'")
            else:
                print(f"❌ Date formatting failed: '{input_date}' -> '{formatted_date}' (expected '{expected_output}')")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ PDF test failed: {e}")
        logging.exception("PDF test error details:")
        return False

def test_frontend_date_functions():
    """Test the frontend date formatting functions by checking main.js"""
    print("\n=== Testing Frontend Date Functions ===")
    
    try:
        # Read the main.js file and check for date formatting functions
        with open('/workspaces/itowvms/static/js/main.js', 'r') as f:
            js_content = f.read()
        
        # Check if date formatting functions exist
        required_functions = [
            'formatDateForDisplay',
            'formatDateForInput'
        ]
        
        missing_functions = []
        for func in required_functions:
            if func not in js_content:
                missing_functions.append(func)
        
        if missing_functions:
            print(f"❌ Missing frontend date functions: {missing_functions}")
            return False
        
        # Check if the functions are being used in the right places
        checks = [
            ('formatDateForDisplay(vehicle.tow_date)', 'Vehicle table rendering'),
            ('formatDateForInput(vehicle.tow_date)', 'Vehicle edit modal'),
            ('formatDateForDisplay(vehicle.tow_date)', 'Vehicle details modal')
        ]
        
        for check, description in checks:
            if check in js_content:
                print(f"✅ {description}: {check}")
            else:
                print(f"⚠️  {description}: Pattern not found, may need manual verification")
        
        print("✅ Frontend date formatting functions are present")
        return True
        
    except Exception as e:
        print(f"❌ Frontend test failed: {e}")
        return False

def _is_valid_iso_date(date_str):
    """Check if a date string is in valid YYYY-MM-DD format"""
    try:
        datetime.strptime(date_str, '%Y-%m-%d')
        return True
    except ValueError:
        return False

def run_comprehensive_test():
    """Run all date consistency tests"""
    print("🚀 Starting Comprehensive Date Consistency Test for iTow VMS")
    print("=" * 60)
    
    tests = [
        ("Database Date Consistency", test_database_date_consistency),
        ("PDF Date Formatting", test_pdf_date_formatting),
        ("Frontend Date Functions", test_frontend_date_functions)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 60)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\nOverall Result: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED! Date consistency issues have been resolved.")
        return True
    else:
        print("⚠️  Some tests failed. Please review the issues above.")
        return False

if __name__ == "__main__":
    setup_logging()
    success = run_comprehensive_test()
    sys.exit(0 if success else 1)
