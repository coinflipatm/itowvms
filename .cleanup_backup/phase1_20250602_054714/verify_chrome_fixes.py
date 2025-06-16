#!/usr/bin/env python3
"""
Simple Chrome WebDriver verification test
"""

import sys
import os
sys.path.append('/workspaces/itowvms')

from scraper import TowBookScraper
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def test_chrome_webdriver_initialization():
    """Test Chrome WebDriver initialization"""
    
    print("🔧 Testing Chrome WebDriver Initialization")
    print("=" * 50)
    
    try:
        # Create scraper instance
        scraper = TowBookScraper('test', 'test', test_mode=True)
        
        print("1. Initializing Chrome WebDriver...")
        driver = scraper._init_driver(headless=True)
        
        if driver:
            print("✅ Chrome WebDriver initialized successfully!")
            
            # Test basic navigation
            print("2. Testing basic navigation...")
            driver.get("https://httpbin.org/headers")
            
            if "httpbin.org" in driver.current_url:
                print("✅ Navigation test successful!")
                print(f"   Current URL: {driver.current_url}")
                
                # Test page title
                title = driver.title
                print(f"   Page title: {title}")
                
                # Clean up
                driver.quit()
                print("✅ WebDriver closed successfully")
                
                return True
            else:
                print("❌ Navigation test failed")
                driver.quit()
                return False
        else:
            print("❌ Chrome WebDriver initialization failed")
            return False
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

def test_scraper_test_mode():
    """Test scraper in test mode"""
    
    print("\n🧪 Testing Scraper Test Mode")
    print("=" * 50)
    
    try:
        # Create scraper in test mode
        scraper = TowBookScraper('itow05', 'iTow2023', test_mode=True)
        
        print("1. Running scraper in test mode...")
        success, message = scraper.scrape_data('2025-05-25', '2025-05-25')
        
        if success:
            print("✅ Test mode scraping successful!")
            print(f"   Message: {message}")
            
            # Check progress
            progress = scraper.get_progress()
            print(f"   Status: {progress.get('status', 'Unknown')}")
            print(f"   Processed: {progress.get('processed', 0)}")
            
            return True
        else:
            print(f"❌ Test mode scraping failed: {message}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

if __name__ == "__main__":
    print("🔍 Chrome WebDriver Fix Verification")
    print("Testing the fixes we implemented...")
    print()
    
    # Test 1: Chrome WebDriver initialization
    test1_success = test_chrome_webdriver_initialization()
    
    # Test 2: Scraper test mode
    test2_success = test_scraper_test_mode()
    
    print("\n" + "=" * 50)
    print("📊 FINAL RESULTS")
    print("=" * 50)
    
    if test1_success:
        print("✅ Chrome WebDriver initialization: WORKING")
    else:
        print("❌ Chrome WebDriver initialization: FAILED")
    
    if test2_success:
        print("✅ Scraper test mode: WORKING")
    else:
        print("❌ Scraper test mode: FAILED")
    
    overall_success = test1_success and test2_success
    
    if overall_success:
        print("\n🎉 SUCCESS: All Chrome WebDriver fixes are working!")
        print("✅ ChromeDriver is properly installed and configured")
        print("✅ Chrome options are optimized for container environment")
        print("✅ TowBook scraper can initialize WebDriver successfully")
        print("✅ Test mode functionality is working")
        print("\nThe iTow vehicle management system is ready for TowBook scraping!")
    else:
        print("\n❌ FAILURE: Some issues remain with Chrome WebDriver setup")
    
    exit(0 if overall_success else 1)
