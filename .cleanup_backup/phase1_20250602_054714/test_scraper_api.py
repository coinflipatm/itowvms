#!/usr/bin/env python3
"""
Test script to verify scraper API functionality
"""

import requests
import time
import json

def test_scraper_api():
    """Test the scraper API endpoints"""
    base_url = "http://127.0.0.1:5001"
    
    print("Testing Scraper API Integration...")
    
    try:
        # Test API health
        response = requests.get(f"{base_url}/api/vehicles")
        print(f"✓ API health check: {response.status_code}")
        
        # Test scraper start endpoint
        print("\nTesting scraper initialization...")
        payload = {
            "username": "test_user",
            "password": "test_pass",
            "start_date": "2024-01-01",
            "end_date": "2024-01-02"
        }
        
        response = requests.post(f"{base_url}/api/start-scraping", json=payload)
        print(f"Scraper start response: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"Response: {json.dumps(result, indent=2)}")
            
            # Test progress endpoint
            print("\nTesting progress endpoint...")
            progress_response = requests.get(f"{base_url}/api/scraping-progress")
            print(f"Progress response: {progress_response.status_code}")
            
            if progress_response.status_code == 200:
                progress = progress_response.json()
                print(f"Progress: {json.dumps(progress, indent=2)}")
        else:
            print(f"Error response: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("✗ Could not connect to Flask application")
        return False
    except Exception as e:
        print(f"✗ Test failed: {str(e)}")
        return False
    
    print("\n✓ Scraper API test completed")
    return True

if __name__ == "__main__":
    test_scraper_api()
