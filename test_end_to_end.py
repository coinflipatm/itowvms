#!/usr/bin/env python3
"""
End-to-end test for scraper integration in test mode
"""
import requests
import time
import json
import sys

def test_scraper_api():
    """Test the complete scraper workflow via API"""
    base_url = "http://localhost:5001"
    
    # Test payload for test mode
    payload = {
        "username": "test_user",
        "password": "test_pass",
        "start_date": "2024-01-01",
        "end_date": "2024-01-31",
        "test_mode": True
    }
    
    print("🚀 Starting end-to-end scraper test in test mode...")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    
    try:
        # Start scraping
        print("\n1️⃣ Starting scraper...")
        response = requests.post(f"{base_url}/api/start-scraping", json=payload)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        
        if response.status_code != 200:
            print("❌ Failed to start scraper")
            return False
        
        result = response.json()
        scraper_id = result.get('scraper_id')
        test_mode = result.get('test_mode')
        
        print(f"✅ Scraper started successfully (Test Mode: {test_mode})")
        print(f"Scraper ID: {scraper_id}")
        
        # Monitor progress
        print("\n2️⃣ Monitoring progress...")
        max_attempts = 10
        attempt = 0
        
        while attempt < max_attempts:
            try:
                progress_response = requests.get(f"{base_url}/api/scraping-progress?scraper_id={scraper_id}")
                if progress_response.status_code == 200:
                    progress_data = progress_response.json()
                    progress = progress_data.get('progress', {})
                    
                    print(f"Progress: {progress.get('percentage', 0)}% - {progress.get('status', 'Unknown')}")
                    
                    if not progress.get('is_running', True):
                        print("✅ Scraper completed")
                        break
                        
                    time.sleep(1)
                else:
                    print(f"❌ Failed to get progress: {progress_response.status_code}")
                    
            except Exception as e:
                print(f"⚠️ Error checking progress: {e}")
                
            attempt += 1
            
        if attempt >= max_attempts:
            print("⚠️ Progress monitoring timed out")
            
        # Verify vehicles were inserted
        print("\n3️⃣ Verifying test vehicles in database...")
        try:
            vehicles_response = requests.get(f"{base_url}/api/vehicles")
            if vehicles_response.status_code == 200:
                vehicles = vehicles_response.json()
                test_vehicles = [v for v in vehicles if v.get('towbook_call_number', '').startswith('TEST')]
                
                print(f"Found {len(test_vehicles)} test vehicles:")
                for vehicle in test_vehicles:
                    print(f"  - {vehicle.get('towbook_call_number')}: {vehicle.get('make')} {vehicle.get('model')} ({vehicle.get('plate')})")
                    
                if len(test_vehicles) >= 2:
                    print("✅ Test vehicles successfully inserted")
                    return True
                else:
                    print("❌ Expected at least 2 test vehicles")
                    return False
            else:
                print(f"❌ Failed to get vehicles: {vehicles_response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Error verifying vehicles: {e}")
            return False
            
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        return False

if __name__ == "__main__":
    # Check if server is running
    try:
        response = requests.get("http://localhost:5001/")
        if response.status_code != 200:
            print("❌ Server is not running on localhost:5001")
            print("Please start the Flask app first: python app.py")
            sys.exit(1)
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to localhost:5001")
        print("Please start the Flask app first: python app.py")
        sys.exit(1)
    
    success = test_scraper_api()
    if success:
        print("\n🎉 End-to-end test completed successfully!")
        sys.exit(0)
    else:
        print("\n💥 End-to-end test failed!")
        sys.exit(1)
