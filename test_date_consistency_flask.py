#!/usr/bin/env python3
"""
Comprehensive Date Consistency Test for iTow VMS - Flask Context Version
This script tests date consistency across frontend, database, and PDF generation.
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import Flask app and create application context
from app import app, get_db_connection
from generator import PDFGenerator
import tempfile
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)

def test_database_dates():
    """Test database date consistency"""
    print("=== Testing Database Date Consistency ===")
    try:
        with app.app_context():
            conn = get_db_connection()
            
            # Check for mixed date formats
            cursor = conn.execute("""
                SELECT towbook_call_number, tow_date, 
                       CASE 
                           WHEN tow_date LIKE '____-__-__' THEN 'YYYY-MM-DD'
                           WHEN tow_date LIKE '__/__/____' THEN 'MM/DD/YYYY'
                           ELSE 'OTHER'
                       END as date_format
                FROM vehicles 
                WHERE tow_date IS NOT NULL AND tow_date != ''
                ORDER BY date_format, towbook_call_number
                LIMIT 10
            """)
            
            sample_dates = cursor.fetchall()
            
            # Count by format
            format_counts = conn.execute("""
                SELECT 
                    CASE 
                        WHEN tow_date LIKE '____-__-__' THEN 'YYYY-MM-DD'
                        WHEN tow_date LIKE '__/__/____' THEN 'MM/DD/YYYY'
                        ELSE 'OTHER'
                    END as date_format,
                    COUNT(*) as count
                FROM vehicles 
                WHERE tow_date IS NOT NULL AND tow_date != ''
                GROUP BY 1
            """).fetchall()
            
            print("✅ Database connection successful")
            print("📊 Date Format Distribution:")
            for row in format_counts:
                print(f"   {row['date_format']}: {row['count']} records")
            
            print("\n📋 Sample Date Records:")
            for row in sample_dates[:5]:  # Show first 5
                print(f"   {row['towbook_call_number']}: {row['tow_date']} ({row['date_format']})")
            
            conn.close()
            return True, "Database dates checked successfully"
            
    except Exception as e:
        return False, f"Database test failed: {e}"

def test_pdf_generation():
    """Test PDF generation with date formatting"""
    print("\n=== Testing PDF Date Formatting ===")
    
    # Sample test data with different date formats
    test_data = {
        'towbook_call_number': 'TEST001-25',
        'tow_date': '2025-01-15',  # Database format
        'tow_time': '14:30',
        'year': '2020',
        'make': 'Ford',
        'model': 'Focus',
        'color': 'Blue',
        'vin': '1FAFP34N64W123456',
        'plate': 'ABC1234',
        'state': 'MI',
        'jurisdiction': 'Clio Police',
        'location': '123 Main St',
        'requestor': 'Property Owner',
        'complaint_number': 'CP-2025-001',
        'top_form_sent_date': '2025-01-16'
    }
    
    pdf_gen = PDFGenerator()
    results = []
    
    # Test TOP form
    try:
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            success, error = pdf_gen.generate_top(test_data, tmp.name)
            if success:
                size = os.path.getsize(tmp.name)
                print(f"✅ TOP form generated successfully")
                print(f"   TOP PDF file created: {size} bytes")
                results.append(("TOP", True, None))
            else:
                print(f"❌ TOP form generation failed: {error}")
                results.append(("TOP", False, error))
            os.unlink(tmp.name)  # Clean up
    except Exception as e:
        print(f"❌ TOP form generation failed: {e}")
        results.append(("TOP", False, str(e)))
    
    # Test TR52 form
    try:
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            success, error = pdf_gen.generate_tr52_form(test_data, tmp.name)
            if success:
                size = os.path.getsize(tmp.name)
                print(f"✅ TR52 form generated successfully")
                print(f"   TR52 PDF file created: {size} bytes")
                results.append(("TR52", True, None))
            else:
                print(f"❌ TR52 form generation failed: {error}")
                results.append(("TR52", False, error))
            os.unlink(tmp.name)  # Clean up
    except Exception as e:
        print(f"❌ TR52 form generation failed: {e}")
        results.append(("TR52", False, str(e)))
    
    # Test TR208 form
    try:
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            success, error = pdf_gen.generate_tr208_form(test_data, tmp.name)
            if success:
                size = os.path.getsize(tmp.name)
                print(f"✅ TR208 form generated successfully")
                print(f"   TR208 PDF file created: {size} bytes")
                results.append(("TR208", True, None))
            else:
                print(f"❌ TR208 form generation failed: {error}")
                results.append(("TR208", False, error))
            os.unlink(tmp.name)  # Clean up
    except Exception as e:
        print(f"❌ TR208 form generation failed: {e}")
        results.append(("TR208", False, str(e)))
    
    # Summary
    successful = [r for r in results if r[1]]
    failed = [r for r in results if not r[1]]
    
    if failed:
        print(f"\n❌ PDF Generation Results: {len(successful)}/{len(results)} forms generated successfully")
        for form, success, error in failed:
            print(f"   {form}: {error}")
        return False, f"{len(failed)} PDF generation tests failed"
    else:
        print(f"\n✅ PDF Generation Results: All {len(results)} forms generated successfully")
        return True, "All PDF forms generated successfully"

def test_frontend_date_functions():
    """Test that frontend date functions are present in main.js"""
    print("\n=== Testing Frontend Date Functions ===")
    
    try:
        main_js_path = '/workspaces/itowvms/static/js/main.js'
        
        if not os.path.exists(main_js_path):
            return False, "main.js file not found"
        
        with open(main_js_path, 'r') as f:
            content = f.read()
        
        checks = [
            ('formatDateForDisplay function', 'function formatDateForDisplay('),
            ('formatDateForInput function', 'function formatDateForInput('),
            ('Vehicle table date usage', 'formatDateForDisplay(vehicle.tow_date)'),
            ('Vehicle modal date usage', 'formatDateForInput(vehicle.tow_date)'),
        ]
        
        results = []
        for description, pattern in checks:
            if pattern in content:
                print(f"✅ {description}: Found")
                results.append(True)
            else:
                print(f"❌ {description}: Not found")
                results.append(False)
        
        if all(results):
            return True, "All frontend date functions are present"
        else:
            failed_count = len([r for r in results if not r])
            return False, f"{failed_count} frontend checks failed"
            
    except Exception as e:
        return False, f"Frontend test failed: {e}"

def main():
    """Run comprehensive date consistency tests"""
    print("🚀 Starting Comprehensive Date Consistency Test for iTow VMS")
    print("=" * 60)
    
    # Run all tests
    tests = []
    
    # Test database dates
    db_success, db_message = test_database_dates()
    tests.append(("Database Date Consistency", db_success, db_message))
    
    # Test PDF generation
    pdf_success, pdf_message = test_pdf_generation()
    tests.append(("PDF Date Formatting", pdf_success, pdf_message))
    
    # Test frontend functions
    frontend_success, frontend_message = test_frontend_date_functions()
    tests.append(("Frontend Date Functions", frontend_success, frontend_message))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 60)
    
    passed = 0
    for test_name, success, message in tests:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{test_name}: {status}")
        if not success:
            print(f"   Error: {message}")
        if success:
            passed += 1
    
    total = len(tests)
    print(f"\nOverall Result: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Date consistency fixes are working correctly.")
        return 0
    else:
        print("⚠️  Some tests failed. Please review the issues above.")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
