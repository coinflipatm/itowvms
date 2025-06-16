#!/usr/bin/env python3
"""
Quick test of TowBook scraper initialization only
"""

import os
import sys
import logging
sys.path.append('/workspaces/itowvms')

# Set up logging
logging.basicConfig(level=logging.INFO)

from scraper import TowBookScraper

def quick_test():
    """Quick test of scraper initialization"""
    
    try:
        print("Testing TowBook scraper initialization...")
        
        # Initialize scraper
        scraper = TowBookScraper('itow05', 'iTow2023')
        print("✓ Scraper object created")
        
        # Test driver initialization only
        print("Initializing Chrome WebDriver...")
        driver = scraper._init_driver(headless=True)
        print("✓ WebDriver initialized successfully")
        
        # Test simple navigation
        print("Testing simple navigation...")
        driver.get("https://google.com")
        print(f"✓ Successfully navigated to: {driver.current_url}")
        
        # Clean up
        driver.quit()
        print("✓ WebDriver closed")
        
        return True
        
    except Exception as e:
        print(f"ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = quick_test()
    sys.exit(0 if success else 1)
