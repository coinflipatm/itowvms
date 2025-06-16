#!/usr/bin/env python3
"""
Comprehensive TOP generation diagnostics
"""
import requests
import json
import os

def comprehensive_top_test():
    print("="*60)
    print("COMPREHENSIVE TOP GENERATION DIAGNOSTICS")
    print("="*60)
    
    base_url = "http://127.0.0.1:5001"
    session = requests.Session()
    
    try:
        # 1. Check if server is responding
        print("1. Checking server connectivity...")
        response = session.get(f"{base_url}/")
        if response.status_code == 200:
            print("✅ Server is responding")
        else:
            print(f"❌ Server not responding: {response.status_code}")
            return False
        
        # 2. Check authentication
        print("\n2. Testing authentication...")
        login_data = {'username': 'testuser', 'password': 'password123'}
        login_response = session.post(f"{base_url}/login", data=login_data, allow_redirects=False)
        
        if login_response.status_code == 302:
            print("✅ Authentication successful")
        else:
            print(f"❌ Authentication failed: {login_response.status_code}")
            return False
        
        # 3. Check API access
        print("\n3. Testing API access...")
        api_response = session.get(f"{base_url}/api/vehicles")
        if api_response.status_code == 200:
            vehicles = api_response.json()
            print(f"✅ API access successful - {len(vehicles)} vehicles found")
        else:
            print(f"❌ API access failed: {api_response.status_code}")
            return False
        
        # 4. Check directories
        print("\n4. Checking required directories...")
        required_dirs = [
            'static/generated_pdfs',
            'static/uploads/vehicle_photos',
            'static/uploads/documents'
        ]
        
        for dir_path in required_dirs:
            if os.path.exists(dir_path):
                print(f"✅ {dir_path} exists")
            else:
                print(f"❌ {dir_path} missing - creating...")
                os.makedirs(dir_path, exist_ok=True)
                print(f"✅ {dir_path} created")
        
        # 5. Test PDF generation dependencies
        print("\n5. Testing PDF generation dependencies...")
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.platypus import SimpleDocTemplate
            print("✅ ReportLab is available")
        except ImportError as e:
            print(f"❌ ReportLab not available: {e}")
            return False
        
        # 6. Find a test vehicle
        print("\n6. Finding test vehicle...")
        test_vehicles = [v for v in vehicles if v.get('status') in ['New', 'TR52 Ready']]
        if not test_vehicles:
            test_vehicles = vehicles[:3]  # Just use first 3 vehicles
        
        if not test_vehicles:
            print("❌ No vehicles available for testing")
            return False
        
        print(f"📊 Testing with {len(test_vehicles)} vehicles:")
        
        # 7. Test TOP generation for each vehicle
        success_count = 0
        for i, vehicle in enumerate(test_vehicles, 1):
            call_number = vehicle.get('towbook_call_number')
            status = vehicle.get('status')
            make_model = f"{vehicle.get('make', 'N/A')} {vehicle.get('model', 'N/A')}"
            
            print(f"\n7.{i} Testing TOP generation for {call_number}:")
            print(f"    Vehicle: {make_model}")
            print(f"    Current Status: {status}")
            
            # Test TOP generation
            top_response = session.post(f"{base_url}/api/generate-top/{call_number}")
            
            print(f"    Response Status: {top_response.status_code}")
            
            if top_response.status_code == 200:
                result = top_response.json()
                print(f"    ✅ SUCCESS - {result.get('message')}")
                print(f"    📄 PDF: {result.get('pdf_filename')}")
                success_count += 1
            else:
                print(f"    ❌ FAILED")
                try:
                    error_data = top_response.json()
                    print(f"    Error: {error_data.get('error')}")
                    print(f"    Details: {error_data.get('details')}")
                except:
                    print(f"    Raw response: {top_response.text[:200]}...")
        
        print(f"\n" + "="*60)
        print(f"SUMMARY: {success_count}/{len(test_vehicles)} TOP generations successful")
        
        if success_count == len(test_vehicles):
            print("🎉 All TOP generations working correctly!")
            return True
        elif success_count > 0:
            print("⚠️  Some TOP generations working, some failing")
            return False
        else:
            print("❌ All TOP generations failing")
            return False
            
    except Exception as e:
        print(f"❌ Diagnostic failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    comprehensive_top_test()
