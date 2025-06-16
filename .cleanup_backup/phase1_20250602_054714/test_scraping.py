#!/usr/bin/env python3
"""
Test scraping functionality to determine why BMW/Lexus vehicles aren't being added
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from scraper import TowBookScraper
import logging
import sqlite3

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_vehicles_count_by_status(status_list):
    """Get count of vehicles by status without Flask context"""
    conn = sqlite3.connect('vehicles.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    placeholders = ','.join(['?' for _ in status_list])
    query = f"SELECT COUNT(*) as count FROM vehicles WHERE status IN ({placeholders}) AND archived = 0"
    cursor.execute(query, status_list)
    result = cursor.fetchone()
    conn.close()
    return result['count'] if result else 0

def get_vehicle_by_call_number_simple(call_number):
    """Get vehicle by call number without Flask context"""
    conn = sqlite3.connect('vehicles.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM vehicles WHERE towbook_call_number = ?", (call_number,))
    result = cursor.fetchone()
    conn.close()
    return dict(result) if result else None

def test_scraper_functionality():
    """Test the scraper in test mode to verify functionality"""
    print("=" * 60)
    print("TESTING SCRAPER FUNCTIONALITY")
    print("=" * 60)
    
    # Count vehicles before test
    vehicles_before = get_vehicles_count_by_status(['New'])
    print(f"\nVehicles before test: {vehicles_before}")
    
    # Create scraper in test mode
    scraper = TowBookScraper("test_user", "test_pass", test_mode=True)
    
    # Run scraper
    success, message = scraper.scrape_data("2024-01-15", "2024-01-16")
    
    print(f"\nScraper completed: Success={success}, Message={message}")
    
    # Count vehicles after test
    vehicles_after = get_vehicles_count_by_status(['New'])
    print(f"Vehicles after test: {vehicles_after}")
    
    # Check if test vehicles were added
    test_calls = ['TEST001', 'TEST002', 'TEST003', 'TEST004', 'TEST005']
    for call_num in test_calls:
        vehicle = get_vehicle_by_call_number_simple(call_num)
        if vehicle:
            print(f"✓ Test vehicle {call_num} found: {vehicle['make']} {vehicle['model']}")
        else:
            print(f"✗ Test vehicle {call_num} NOT found")
    
    return success

def test_bmw_lexus_addition():
    """Test adding BMW/Lexus vehicles directly to verify database insertion works"""
    print("\n" + "=" * 60)
    print("TESTING BMW/LEXUS VEHICLE ADDITION")
    print("=" * 60)
    
    from database import insert_vehicle
    from utils import generate_next_complaint_number
    from datetime import datetime
    
    # Create BMW and Lexus test vehicles
    test_vehicles = [
        {
            'towbook_call_number': 'BMW_TEST_001',
            'jurisdiction': 'Flint',
            'tow_date': '2024-01-20',
            'tow_time': '10:30',
            'location': '100 BMW Test Drive',
            'requestor': 'POLICE',
            'vin': 'BMW1234567890001',
            'year': '2018',
            'make': 'BMW',
            'model': 'X5',
            'color': 'Black',
            'plate': 'BMW001',
            'state': 'MI',
            'status': 'New',
            'archived': 0,
            'complaint_number': generate_next_complaint_number(),
            'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        },
        {
            'towbook_call_number': 'LEXUS_TEST_001',
            'jurisdiction': 'Burton',
            'tow_date': '2024-01-20',
            'tow_time': '11:45',
            'location': '200 Lexus Lane',
            'requestor': 'PROPERTY OWNER',
            'vin': 'LEXUS1234567890001',
            'year': '2019',
            'make': 'Lexus',
            'model': 'RX350',
            'color': 'White',
            'plate': 'LEX001',
            'state': 'MI',
            'status': 'New',
            'archived': 0,
            'complaint_number': generate_next_complaint_number(),
            'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    ]
    
    # Insert test vehicles
    for vehicle in test_vehicles:
        try:
            vehicle_id = insert_vehicle(vehicle)
            if vehicle_id:
                print(f"✓ Successfully added {vehicle['make']} {vehicle['model']} (Call #{vehicle['towbook_call_number']})")
            else:
                print(f"✗ Failed to add {vehicle['make']} {vehicle['model']}")
        except Exception as e:
            print(f"✗ Error adding {vehicle['make']} {vehicle['model']}: {e}")
    
    # Verify they were added
    print("\nVerifying BMW/Lexus vehicles were added:")
    for vehicle in test_vehicles:
        found_vehicle = get_vehicle_by_call_number_simple(vehicle['towbook_call_number'])
        if found_vehicle:
            print(f"✓ Found {found_vehicle['make']} {found_vehicle['model']} with status: {found_vehicle['status']}")
        else:
            print(f"✗ BMW/Lexus vehicle {vehicle['towbook_call_number']} not found in database")

def main():
    print("Starting comprehensive scraping functionality test...")
    
    # Test 1: Test scraper functionality
    scraper_success = test_scraper_functionality()
    
    # Test 2: Test BMW/Lexus addition directly
    test_bmw_lexus_addition()
    
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"Scraper test mode: {'✓ PASSED' if scraper_success else '✗ FAILED'}")
    
    # Count final vehicles
    all_vehicles_count = get_vehicles_count_by_status(['New'])
    print(f"Total vehicles in database: {all_vehicles_count}")
    
    print("\nIf the scraper test mode works but BMW/Lexus vehicles aren't appearing")
    print("after real scraping, the issue is likely in:")
    print("1. TowBook login credentials")
    print("2. TowBook website changes")
    print("3. Date range not containing BMW/Lexus vehicles")
    print("4. Account permissions in TowBook")

if __name__ == "__main__":
    main()
