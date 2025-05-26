#!/usr/bin/env python3
"""
Test TowBook scraper with our fixed Chrome configuration
"""

import os
import sys
import time
from datetime import datetime, timedelta
sys.path.append('/workspaces/itowvms')

from scraper import TowBookScraper

def test_towbook_scraper():
    """Test TowBook scraper functionality"""
    
    # Initialize scraper
    scraper = TowBookScraper('itow05', 'iTow2023')
    
    try:
        print("Testing TowBook scraper...")
        
        # Test driver initialization
        print("1. Initializing Chrome WebDriver...")
        driver = scraper._init_driver(headless=True)
        print("✓ WebDriver initialized successfully")
        
        # Test TowBook login
        print("2. Testing TowBook login...")
        success = scraper.login()
        if success:
            print("✓ Successfully logged into TowBook")
        else:
            print("✗ Failed to login to TowBook")
            return False
        
        # Test navigation to call analysis
        print("3. Testing navigation to call analysis...")
        success = scraper.navigate_to_call_analysis()
        if success:
            print("✓ Successfully navigated to call analysis")
        else:
            print("✗ Failed to navigate to call analysis")
            return False
        
        # Test PPI account selection
        print("4. Testing PPI account selection...")
        success = scraper.select_ppi_account()
        if success:
            print("✓ Successfully selected PPI account")
        else:
            print("✗ Failed to select PPI account")
            return False
        
        # Test date range setting (small range for testing)
        print("5. Testing date range setting...")
        end_date = datetime.now()
        start_date = end_date - timedelta(days=3)  # Small 3-day range for testing
        
        success = scraper.set_date_range(
            start_date.strftime('%Y-%m-%d'),
            end_date.strftime('%Y-%m-%d')
        )
        if success:
            print(f"✓ Successfully set date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        else:
            print("✗ Failed to set date range")
            return False
        
        # Test update button click
        print("6. Testing update button...")
        success = scraper.click_update_button()
        if success:
            print("✓ Successfully clicked update button")
        else:
            print("✗ Failed to click update button")
            return False
        
        print("\n✓ All TowBook scraper tests passed!")
        return True
        
    except Exception as e:
        print(f"ERROR: {str(e)}")
        return False
    finally:
        # Clean up
        try:
            if scraper.driver:
                scraper.driver.quit()
                print("✓ WebDriver closed")
        except:
            pass

if __name__ == "__main__":
    success = test_towbook_scraper()
    sys.exit(0 if success else 1)
