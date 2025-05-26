#!/usr/bin/env python3
"""
Test script to verify scraper API functionality with test mode
"""

import requests
import time
import json

def test_scraper_with_test_mode():
    """Test the scraper API endpoints with test mode enabled"""
    base_url = "http://127.0.0.1:5001"
    
    print("Testing Scraper API Integration with Test Mode...")
    
    try:
        # Test API health
        response = requests.get(f"{base_url}/api/vehicles")
        print(f"✓ API health check: {response.status_code}")
        
        # Test scraper start endpoint with test mode
        print("\nTesting scraper initialization with test mode...")
        payload = {
            "username": "test_user",
            "password": "test_pass",
            "start_date": "2024-01-01",
            "end_date": "2024-01-02",
            "test_mode": True
        }
        
        response = requests.post(f"{base_url}/api/start-scraping", json=payload)
        print(f"Scraper start response: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"Success Response: {json.dumps(result, indent=2)}")
            
            # Test progress endpoint
            print("\nTesting progress endpoint...")
            progress_response = requests.get(f"{base_url}/api/scraping-progress")
            print(f"Progress response: {progress_response.status_code}")
            
            if progress_response.status_code == 200:
                progress = progress_response.json()
                print(f"Progress: {json.dumps(progress, indent=2)}")
        else:
            print(f"Error response: {response.text}")
            
        # Test vehicles endpoint to see if test data was added
        print("\nChecking for test vehicles in database...")
        vehicles_response = requests.get(f"{base_url}/api/vehicles")
        if vehicles_response.status_code == 200:
            vehicles = vehicles_response.json()
            test_vehicles = [v for v in vehicles.get('vehicles', []) if v.get('towbook_call_number', '').startswith('TEST')]
            print(f"Found {len(test_vehicles)} test vehicles in database:")
            for vehicle in test_vehicles:
                print(f"  - {vehicle.get('towbook_call_number')}: {vehicle.get('make')} {vehicle.get('model')}")
            
    except requests.exceptions.ConnectionError:
        print("✗ Could not connect to Flask application")
        return False
    except Exception as e:
        print(f"✗ Test failed: {str(e)}")
        return False
    
    print("\n✓ Scraper API test mode completed successfully")
    return True

if __name__ == "__main__":
    test_scraper_with_test_mode()
