#!/usr/bin/env python3
"""
Debug script to test TowBook scraper and see exactly what's happening
"""
import os
import sys
import logging
from datetime import datetime

# Add the current directory to Python path
sys.path.insert(0, '/workspaces/itowvms')

# Set up detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('/workspaces/itowvms/scraper_debug.log')
    ]
)

from scraper import TowBookScraper

def test_scraper():
    print("="*60)
    print("TOWBOOK SCRAPER DEBUG TEST")
    print("="*60)
    
    # Check environment variables
    username = os.environ.get('TOWBOOK_USERNAME')
    password = os.environ.get('TOWBOOK_PASSWORD')
    
    print(f"Username from env: {'***' if username else 'NOT SET'}")
    print(f"Password from env: {'***' if password else 'NOT SET'}")
    
    if not username or not password:
        print("\n❌ ERROR: TowBook credentials not found in environment variables")
        print("Please set TOWBOOK_USERNAME and TOWBOOK_PASSWORD")
        return
    
    try:
        print(f"\n🔧 Creating TowBook scraper instance...")
        scraper = TowBookScraper(username, password, test_mode=False)
        
        print(f"📊 Initial progress: {scraper.progress}")
        
        print(f"\n🌐 Initializing WebDriver...")
        scraper._init_driver(headless=True)
        print(f"✅ WebDriver initialized successfully")
        
        print(f"\n🔐 Attempting login...")
        login_result = scraper.login()
        print(f"Login result: {login_result}")
        
        if login_result:
            print(f"✅ Login successful!")
            
            print(f"\n📋 Fetching vehicle list...")
            vehicles = scraper.get_vehicle_list()
            print(f"Found {len(vehicles) if vehicles else 0} vehicles")
            
            if vehicles:
                print(f"\nFirst 3 vehicles from TowBook:")
                for i, vehicle in enumerate(vehicles[:3]):
                    print(f"  {i+1}. Call#: {vehicle.get('call_number', 'N/A')}")
                    print(f"     {vehicle.get('make', 'N/A')} {vehicle.get('model', 'N/A')}")
                    print(f"     Status: {vehicle.get('status', 'N/A')}")
                    print(f"     Date: {vehicle.get('tow_date', 'N/A')}")
                    print()
                
                print(f"\n🔄 Testing full scrape process...")
                result = scraper.scrape_and_save()
                print(f"Scrape result: {result}")
            else:
                print(f"❌ No vehicles found in TowBook")
                
        else:
            print(f"❌ Login failed!")
            
    except Exception as e:
        print(f"❌ ERROR during scraper test: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        try:
            if 'scraper' in locals() and scraper.driver:
                scraper.driver.quit()
                print(f"🔒 WebDriver closed")
        except:
            pass

if __name__ == "__main__":
    test_scraper()
