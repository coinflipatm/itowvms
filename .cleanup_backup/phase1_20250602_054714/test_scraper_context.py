#!/usr/bin/env python3
"""
Test script to verify Flask application context fix for TowBook scraper
"""
import os
import sys
import time
import requests
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def test_scraper_api():
    """Test the scraper API with test mode to verify context fix"""
    base_url = "http://localhost:5001"
    
    # Test data
    test_data = {
        "username": "test_user",
        "password": "test_pass", 
        "start_date": "2024-01-15",
        "end_date": "2024-01-16",
        "test_mode": True  # This will run the test mode which creates test vehicles
    }
    
    try:
        # Start scraping in test mode
        print("🚀 Starting scraper in test mode...")
        response = requests.post(f"{base_url}/api/start-scraping", 
                               json=test_data, 
                               headers={'Content-Type': 'application/json'})
        
        if response.status_code != 202:
            print(f"❌ Failed to start scraper: {response.status_code} - {response.text}")
            return False
            
        response_data = response.json()
        scraper_id = response_data.get('scraper_id')
        print(f"✅ Scraper started with ID: {scraper_id}")
        print(f"✅ Test mode: {response_data.get('test_mode')}")
        
        # Monitor progress
        print("\n📊 Monitoring progress...")
        max_attempts = 30  # 30 seconds max
        attempt = 0
        
        while attempt < max_attempts:
            try:
                progress_response = requests.get(f"{base_url}/api/scraping-progress/{scraper_id}")
                if progress_response.status_code == 200:
                    progress = progress_response.json()
                    
                    print(f"⏳ Progress: {progress['percentage']}% - {progress['status']}")
                    print(f"   Processed: {progress['processed']}/{progress['total']}")
                    
                    if progress.get('error'):
                        print(f"❌ Scraper error: {progress['error']}")
                        return False
                        
                    if not progress['is_running']:
                        if 'Completed' in progress['status'] or 'completed' in progress['status'].lower():
                            print(f"✅ Scraping completed successfully!")
                            print(f"   Final status: {progress['status']}")
                            return True
                        else:
                            print(f"⚠️  Scraping stopped: {progress['status']}")
                            return False
                            
                else:
                    print(f"❌ Failed to get progress: {progress_response.status_code}")
                    
            except requests.exceptions.RequestException as e:
                print(f"❌ Request error: {e}")
                
            time.sleep(1)
            attempt += 1
            
        print("⏰ Timeout waiting for scraper to complete")
        return False
        
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        return False

def verify_test_vehicles():
    """Verify that test vehicles were stored in the database"""
    try:
        print("\n🔍 Verifying test vehicles were stored...")
        response = requests.get("http://localhost:5001/api/vehicles")
        
        if response.status_code == 200:
            vehicles = response.json()
            test_vehicles = [v for v in vehicles if v.get('towbook_call_number', '').startswith('TEST')]
            
            if test_vehicles:
                print(f"✅ Found {len(test_vehicles)} test vehicles in database:")
                for vehicle in test_vehicles:
                    print(f"   - {vehicle.get('towbook_call_number')}: {vehicle.get('make')} {vehicle.get('model')} ({vehicle.get('status')})")
                return True
            else:
                print("❌ No test vehicles found in database")
                return False
        else:
            print(f"❌ Failed to fetch vehicles: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error verifying vehicles: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Testing TowBook Scraper Flask Application Context Fix")
    print("=" * 60)
    
    # Test the scraper API
    scraper_success = test_scraper_api()
    
    if scraper_success:
        # Verify vehicles were stored
        storage_success = verify_test_vehicles()
        
        if storage_success:
            print("\n🎉 SUCCESS: Flask application context fix is working!")
            print("   - Scraper runs without application context errors")
            print("   - Test vehicles are successfully stored in database")
            sys.exit(0)
        else:
            print("\n⚠️  PARTIAL SUCCESS: Scraper ran but vehicles not stored")
            sys.exit(1)
    else:
        print("\n❌ FAILURE: Scraper failed to run")
        sys.exit(1)
