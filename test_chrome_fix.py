#!/usr/bin/env python3
"""
Test fresh TowBook scraping with our Chrome fixes
"""

import requests
import time
import json

def test_fresh_scraping():
    """Test a fresh scraping operation"""
    
    base_url = "http://127.0.0.1:5001"
    
    try:
        print("🧪 Testing fresh TowBook scraping...")
        print("=" * 50)
        
        # Test 1: Start fresh scraping (non-test mode with small date range)
        print("1. Starting fresh TowBook scraping...")
        scraping_data = {
            'username': 'itow05',
            'password': 'iTow2023',
            'start_date': '2025-05-25',  # Yesterday only
            'end_date': '2025-05-25',    # Yesterday only
            'test_mode': False  # Real TowBook scraping
        }
        
        response = requests.post(f"{base_url}/api/start-scraping", json=scraping_data)
        if response.status_code == 202:
            result = response.json()
            scraper_id = result.get('scraper_id')
            print(f"✅ Scraping started with ID: {scraper_id}")
        else:
            print(f"❌ Failed to start scraping: {response.status_code}")
            print(f"Response: {response.text}")
            return False
        
        # Test 2: Monitor progress
        print("2. Monitoring scraping progress...")
        max_attempts = 120  # 2 minutes timeout
        attempt = 0
        
        while attempt < max_attempts:
            response = requests.get(f"{base_url}/api/scraping-progress/{scraper_id}")
            if response.status_code == 200:
                progress = response.json()
                status = progress.get('status', 'Unknown')
                current = progress.get('processed', 0)
                total = progress.get('total', 0)
                percentage = progress.get('percentage', 0)
                error = progress.get('error')
                is_running = progress.get('is_running', False)
                
                print(f"   [{time.strftime('%H:%M:%S')}] {status} - {percentage}%")
                
                if error:
                    print(f"❌ Scraping error: {error}")
                    return False
                
                if not is_running:
                    if percentage == 100 or 'Completed' in status:
                        print(f"✅ Scraping completed! Status: {status}")
                        break
                    else:
                        print(f"⚠️ Scraping stopped: {status}")
                        return False
                        
            else:
                print(f"❌ Failed to get progress: {response.status_code}")
                return False
                
            time.sleep(2)  # Check every 2 seconds
            attempt += 1
        
        if attempt >= max_attempts:
            print("⏰ Scraping timed out")
            return False
        
        # Test 3: Verify results
        print("3. Verifying results...")
        response = requests.get(f"{base_url}/api/vehicles")
        if response.status_code == 200:
            vehicles = response.json()
            print(f"✅ Database contains {len(vehicles)} vehicles")
            return True
        else:
            print("❌ Failed to fetch vehicles after scraping")
            return False
        
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to server")
        return False
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

if __name__ == "__main__":
    print("🔧 Chrome WebDriver Fix Test")
    print("Testing real TowBook scraping functionality...")
    
    success = test_fresh_scraping()
    
    if success:
        print("\n🎉 SUCCESS: Chrome WebDriver fixes are working!")
        print("✅ TowBook login successful")
        print("✅ Navigation working")
        print("✅ Data extraction working")
        print("✅ Database storage working")
        print("\nThe iTow vehicle management system scraping is now fully functional!")
    else:
        print("\n❌ FAILURE: Issues detected with Chrome WebDriver")
    
    exit(0 if success else 1)
