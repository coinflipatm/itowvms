#!/usr/bin/env python3
"""
Test script to verify WebDriver functionality
"""

import sys
import os
sys.path.append('/workspaces/itowvms')

from scraper import TowBookScraper

def test_webdriver():
    print("Testing WebDriver initialization...")
    
    try:
        # Create scraper instance with dummy credentials
        scraper = TowBookScraper("test", "test")
        
        # Test headless mode
        print("Testing headless mode...")
        driver = scraper._init_driver(headless=True)
        print("✓ Headless WebDriver initialized successfully")
        
        # Test basic navigation
        driver.get("https://httpbin.org/get")
        print("✓ Basic navigation works")
        
        # Clean up
        driver.quit()
        scraper.driver = None
        
        print("✓ WebDriver test completed successfully")
        return True
        
    except Exception as e:
        print(f"✗ WebDriver test failed: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_webdriver()
    sys.exit(0 if success else 1)
