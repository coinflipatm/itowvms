#!/usr/bin/env python3
"""
Test TowBook scraper login only
"""

import sys
import logging
sys.path.append('/workspaces/itowvms')

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

from scraper import TowBookScraper

def test_login_only():
    """Test TowBook login functionality only"""
    
    scraper = None
    try:
        print("=== Testing TowBook Login ===")
        
        # Initialize scraper
        scraper = TowBookScraper('itow05', 'iTow2023')
        print("✓ Scraper object created")
        
        # Initialize driver
        print("Initializing Chrome WebDriver...")
        driver = scraper._init_driver(headless=True)
        print("✓ WebDriver initialized")
        
        # Test login
        print("Attempting to login to TowBook...")
        success = scraper.login()
        
        if success:
            print("✓ Successfully logged into TowBook!")
            
            # Get current URL to verify we're logged in
            current_url = scraper.driver.current_url
            print(f"Current URL: {current_url}")
            
            if "towbook.com" in current_url and "login" not in current_url.lower():
                print("✓ Login verification successful - not on login page")
                return True
            else:
                print("✗ Login verification failed - still on login page")
                return False
        else:
            print("✗ Login failed")
            return False
        
    except Exception as e:
        print(f"ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Clean up
        if scraper:
            try:
                scraper.close()
                print("✓ Scraper closed")
            except:
                pass

if __name__ == "__main__":
    success = test_login_only()
    print(f"\nTest result: {'PASSED' if success else 'FAILED'}")
    sys.exit(0 if success else 1)
