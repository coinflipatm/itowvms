#!/usr/bin/env python3
"""
Test script to check scraping API functionality
"""

import requests
import json
from datetime import datetime, timedelta

def test_scraping_api():
    """Test the scraping API with different scenarios"""
    base_url = "http://127.0.0.1:5001"
    
    print("=" * 60)
    print("TESTING SCRAPING API")
    print("=" * 60)
    
    # Test 1: Check scraping status
    try:
        response = requests.get(f"{base_url}/scraping-progress")
        print(f"✓ Scraping progress endpoint: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"  Current status: {data.get('status', 'unknown')}")
    except Exception as e:
        print(f"✗ Error checking scraping progress: {e}")
    
    # Test 2: Start real scraping and poll for progress
    import time
    try:
        # Calculate date range (last 30 days)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        scraping_data = {
            "username": "itow05",
            "password": "iTow2023",
            "start_date": start_date.strftime("%Y-%m-%d"),
            "end_date": end_date.strftime("%Y-%m-%d"),
            "test_mode": False
        }
        print(f"\nInitiating real scraping: {scraping_data['start_date']} to {scraping_data['end_date']}")
        resp = requests.post(f"{base_url}/api/start-scraping", json=scraping_data, headers={'Content-Type': 'application/json'})
        print(f"✓ start-scraping response: {resp.status_code}")
        if resp.status_code == 202:
            data = resp.json()
            scraper_id = data.get('scraper_id')
            print(f"  Scraper ID: {scraper_id}")
            # Poll progress
            while True:
                time.sleep(3)
                prog = requests.get(f"{base_url}/api/scraping-progress/{scraper_id}")
                if prog.status_code == 200:
                    progress = prog.json()
                    print(f"  Progress: {progress.get('status')} ({progress.get('percentage')}%)")
                    if not progress.get('is_running'):
                        if progress.get('error'):
                            print(f"  Scraping error: {progress.get('error')}")
                        else:
                            print("  Scraping completed successfully.")
                            print(f"  Final status: {progress.get('status')}")
                        break
                else:
                    print(f"  Error fetching progress: {prog.status_code}")
                    break
        else:
            print(f"  Failed to start scraping: {resp.text}")
    except Exception as e:
        print(f"✗ Error during real scraping test: {e}")
    
    # Test 3: Check if any vehicles were added
    try:
        response = requests.get(f"{base_url}/api/vehicles")
        if response.status_code == 200:
            vehicles = response.json()
            print(f"\n✓ Total vehicles after test: {len(vehicles)}")
            
            # Look for any BMW/Lexus vehicles
            bmw_lexus = [v for v in vehicles if v.get('make', '').upper() in ['BMW', 'LEXUS']]
            print(f"  BMW/Lexus vehicles found: {len(bmw_lexus)}")
            
            if bmw_lexus:
                for vehicle in bmw_lexus[:3]:  # Show first 3
                    print(f"    - {vehicle.get('make')} {vehicle.get('model')} (Call: {vehicle.get('call_number')})")
        else:
            print(f"✗ Error getting vehicles: {response.status_code}")
            
    except Exception as e:
        print(f"✗ Error checking vehicles: {e}")

if __name__ == "__main__":
    test_scraping_api()
