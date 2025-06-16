#!/usr/bin/env python3
"""
Debug script to test TowBook scraping and see what vehicles would be imported
"""

import sys
import os
from datetime import datetime, timedelta

# Add the project directory to Python path
sys.path.insert(0, '/workspaces/itowvms')

from scraper import TowBookScraper
import sqlite3

def main():
    print("=== TowBook Scraping Debug Tool ===\n")
    
    # Get TowBook credentials
    username = input("TowBook Username: ")
    password = input("TowBook Password: ")
    
    # Set date range (last 7 days by default)
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    
    print(f"\nDate range: {start_date} to {end_date}")
    custom_dates = input("Use custom dates? (y/n): ").lower().strip()
    
    if custom_dates == 'y':
        start_date = input("Start date (YYYY-MM-DD): ")
        end_date = input("End date (YYYY-MM-DD): ")
    
    print(f"\nUsing date range: {start_date} to {end_date}")
    
    # Connect to database to check current state
    db_path = '/workspaces/itowvms/vehicles.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get current vehicle count
    cursor.execute("SELECT COUNT(*) FROM vehicles;")
    current_count = cursor.fetchone()[0]
    print(f"Current vehicles in database: {current_count}")
    
    # Get current active vehicles
    cursor.execute("""
        SELECT COUNT(*) FROM vehicles 
        WHERE status NOT IN ('DISPOSED', 'RELEASED', 'COMPLETED', 'Released', 'Scrapped', 'Transferred');
    """)
    active_count = cursor.fetchone()[0]
    print(f"Current active vehicles: {active_count}")
    
    conn.close()
    
    # Initialize scraper in test mode
    print(f"\nInitializing TowBook scraper...")
    scraper = TowBookScraper(username, password, test_mode=True)
    
    try:
        print("Attempting to login to TowBook...")
        if scraper.login():
            print("✅ Successfully logged in to TowBook!")
            
            print("\nStarting scrape (test mode - will not save to database)...")
            scraper.scrape_data(start_date, end_date)
            
            # Get progress info
            progress = scraper.get_progress()
            print(f"\nScraping complete!")
            print(f"Status: {progress['status']}")
            print(f"Processed: {progress['processed']}")
            print(f"Total found: {progress['total']}")
            
            if progress.get('error'):
                print(f"Error: {progress['error']}")
        else:
            print("❌ Failed to login to TowBook")
            print("Please check your username and password")
            
    except Exception as e:
        print(f"❌ Error during scraping: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        if scraper.driver:
            scraper.driver.quit()
            print("Browser closed.")

if __name__ == "__main__":
    main()
