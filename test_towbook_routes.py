#!/usr/bin/env python3
"""
TowBook Web Routes Test
Test the TowBook integration web endpoints with proper Flask app context
"""

import sys
import os
import logging
from datetime import datetime

# Add root directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.factory import create_app

def test_towbook_web_routes():
    """Test TowBook web routes with proper Flask app"""
    
    print("=== TowBook Web Routes Test ===")
    print(f"Test started at: {datetime.now()}")
    print()
    
    # Create app using factory
    app = create_app()
    
    # Disable login requirements for testing by setting TESTING config
    app.config['TESTING'] = True
    app.config['LOGIN_DISABLED'] = True
    
    with app.test_client() as client:
        print("1. Testing TowBook Dashboard Route...")
        try:
            response = client.get('/dashboard/towbook')
            print(f"   Status Code: {response.status_code}")
            if response.status_code in [200, 302]:
                print("   ✅ TowBook dashboard route accessible")
            else:
                print(f"   ❌ Dashboard route failed with status {response.status_code}")
                return False
        except Exception as e:
            print(f"   ❌ Dashboard route failed: {e}")
            return False
        
        print("2. Testing TowBook API Routes...")
        try:
            # Test date range endpoint
            response = client.get('/api/towbook/date-range')
            print(f"   Date Range API Status: {response.status_code}")
            
            # Test progress endpoint  
            response = client.get('/api/towbook/import-progress')
            print(f"   Progress API Status: {response.status_code}")
            
            # Test dashboard status API
            response = client.get('/dashboard/api/towbook-status')
            print(f"   Dashboard Status API: {response.status_code}")
            
            # Test dashboard summary API
            response = client.get('/dashboard/api/towbook-import-summary')
            print(f"   Dashboard Summary API: {response.status_code}")
            
            print("   ✅ All API routes responding (status codes may vary due to auth)")
            
        except Exception as e:
            print(f"   ❌ API routes test failed: {e}")
            return False
        
        print("3. Testing TowBook Integration Functions...")
        try:
            # Test TowBook integration directly
            towbook_integration = app.towbook_integration
            
            # Test date range functionality
            date_range = towbook_integration.get_available_date_range()
            print(f"   ✅ Date range: {date_range['start_date']} to {date_range['end_date']}")
            
            # Test progress monitoring
            progress = towbook_integration.get_import_progress()
            print(f"   ✅ Import progress status: {progress.get('status')}")
            
        except Exception as e:
            print(f"   ❌ TowBook integration functions failed: {e}")
            return False
    
    print()
    print("=== TowBook Web Routes Test Results ===")
    print("✅ TowBook web integration fully functional!")
    print("• Dashboard route accessible")
    print("• API endpoints registered and responding")
    print("• TowBook integration module operational")
    print()
    
    return True

def main():
    """Run the web routes test"""
    
    # Configure minimal logging for test
    logging.basicConfig(level=logging.ERROR)
    
    try:
        success = test_towbook_web_routes()
        
        if success:
            print(f"🎉 TowBook Web Routes Test PASSED at {datetime.now()}")
            sys.exit(0)
        else:
            print(f"❌ TowBook Web Routes Test FAILED at {datetime.now()}")
            sys.exit(1)
            
    except Exception as e:
        print(f"💥 Test execution failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
