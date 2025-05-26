#!/usr/bin/env python3
"""
Test TowBook scraping through the API endpoints
"""

import requests
import time
import json

def test_scraping_api():
    """Test the scraping API endpoints"""
    
    base_url = "http://127.0.0.1:5001"
    
    try:
        # Test 1: Check if the server is responding
        print("1. Testing server connectivity...")
        response = requests.get(f"{base_url}/")
        if response.status_code == 200:
            print("✓ Server is responding")
        else:
            print(f"✗ Server returned status {response.status_code}")
            return False
        
        # Test 2: Start scraping with test mode
        print("2. Starting scraping in test mode...")
        scraping_data = {
            'username': 'itow05',
            'password': 'iTow2023',
            'start_date': '2025-05-23',  # 3 days ago
            'end_date': '2025-05-26',    # today
            'test_mode': True
        }
        
        response = requests.post(f"{base_url}/api/start-scraping", json=scraping_data)
        if response.status_code == 200:
            result = response.json()
            scraper_id = result.get('scraper_id')
            print(f"✓ Scraping started with ID: {scraper_id}")
        else:
            print(f"✗ Failed to start scraping: {response.status_code}")
            print(f"Response: {response.text}")
            return False
        
        # Test 3: Monitor scraping progress
        print("3. Monitoring scraping progress...")
        max_attempts = 30  # 30 seconds timeout
        attempt = 0
        
        while attempt < max_attempts:
            response = requests.get(f"{base_url}/api/scraping-progress/{scraper_id}")
            if response.status_code == 200:
                progress = response.json()
                status = progress.get('status', 'Unknown')
                current = progress.get('current', 0)
                total = progress.get('total', 0)
                error = progress.get('error')
                
                print(f"   Status: {status}, Progress: {current}/{total}")
                
                if error:
                    print(f"✗ Scraping error: {error}")
                    return False
                
                if status in ['Completed', 'Failed']:
                    break
                    
            time.sleep(1)
            attempt += 1
        
        if attempt >= max_attempts:
            print("✗ Scraping timed out")
            return False
        
        if status == 'Completed':
            print(f"✓ Scraping completed successfully! Processed {current} vehicles")
        else:
            print(f"✗ Scraping failed with status: {status}")
            return False
        
        # Test 4: Check if vehicles were added (if not in test mode)
        print("4. Checking vehicles in database...")
        response = requests.get(f"{base_url}/api/vehicles")
        if response.status_code == 200:
            vehicles = response.json()
            print(f"✓ Found {len(vehicles)} vehicles in database")
        else:
            print("✗ Failed to fetch vehicles")
            return False
        
        return True
        
    except requests.exceptions.ConnectionError:
        print("✗ Cannot connect to server. Make sure Flask app is running on port 5001")
        return False
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_scraping_api()
    if success:
        print("\n🎉 All scraping API tests passed!")
    else:
        print("\n❌ Scraping API tests failed!")
    
    exit(0 if success else 1)
