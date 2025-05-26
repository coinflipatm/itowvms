#!/usr/bin/env python3
"""
Simple test to verify basic database operations and check scraping status
"""
import sqlite3
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def test_direct_database_insertion():
    """Test inserting BMW/Lexus vehicles directly into database"""
    print("=" * 60)
    print("TESTING DIRECT DATABASE INSERTION")
    print("=" * 60)
    
    conn = sqlite3.connect('vehicles.db')
    cursor = conn.cursor()
    
    # Create test BMW/Lexus vehicles
    test_vehicles = [
        ('BMW_TEST_001', 'Flint', '2024-01-20', '10:30', '100 BMW Test Drive', 'POLICE', 
         'BMW1234567890001', '2018', 'BMW', 'X5', 'Black', 'BMW001', 'MI', 'New', 0, 
         'IT0200-25', datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
        ('LEXUS_TEST_001', 'Burton', '2024-01-20', '11:45', '200 Lexus Lane', 'PROPERTY OWNER', 
         'LEXUS1234567890001', '2019', 'Lexus', 'RX350', 'White', 'LEX001', 'MI', 'New', 0, 
         'IT0201-25', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    ]
    
    success_count = 0
    for vehicle in test_vehicles:
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO vehicles 
                (towbook_call_number, jurisdiction, tow_date, tow_time, location, requestor, 
                 vin, year, make, model, color, plate, state, status, archived, 
                 complaint_number, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, vehicle)
            print(f"✓ Successfully inserted {vehicle[8]} {vehicle[9]} (Call #{vehicle[0]})")
            success_count += 1
        except Exception as e:
            print(f"✗ Error inserting {vehicle[8]} {vehicle[9]}: {e}")
    
    conn.commit()
    conn.close()
    
    print(f"\nInserted {success_count} out of {len(test_vehicles)} test vehicles")
    return success_count > 0

def check_database_status():
    """Check current database status"""
    print("\n" + "=" * 60)
    print("DATABASE STATUS CHECK")
    print("=" * 60)
    
    conn = sqlite3.connect('vehicles.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Check total vehicles
    cursor.execute("SELECT COUNT(*) as total FROM vehicles")
    total = cursor.fetchone()['total']
    print(f"Total vehicles in database: {total}")
    
    # Check by status
    cursor.execute("SELECT status, COUNT(*) as count FROM vehicles GROUP BY status ORDER BY count DESC")
    status_counts = cursor.fetchall()
    print("\nVehicles by status:")
    for row in status_counts:
        print(f"  {row['status']}: {row['count']}")
    
    # Check for BMW/Lexus
    cursor.execute("SELECT make, model, COUNT(*) as count FROM vehicles WHERE make IN ('BMW', 'Lexus') GROUP BY make, model")
    bmw_lexus = cursor.fetchall()
    print(f"\nBMW/Lexus vehicles found: {len(bmw_lexus)}")
    for row in bmw_lexus:
        print(f"  {row['make']} {row['model']}: {row['count']}")
    
    # Check test vehicles
    cursor.execute("SELECT towbook_call_number, make, model FROM vehicles WHERE towbook_call_number LIKE '%TEST%' ORDER BY towbook_call_number")
    test_vehicles = cursor.fetchall()
    print(f"\nTest vehicles found: {len(test_vehicles)}")
    for row in test_vehicles:
        print(f"  {row['towbook_call_number']}: {row['make']} {row['model']}")
    
    conn.close()

def check_scraping_logs():
    """Check if there are any scraping logs that might indicate issues"""
    print("\n" + "=" * 60)
    print("CHECKING FOR RECENT SCRAPING ACTIVITY")
    print("=" * 60)
    
    # Look for recent log files or error messages
    import os
    import glob
    
    log_files = glob.glob("*.log") + glob.glob("logs/*.log")
    print(f"Found {len(log_files)} log files: {log_files}")
    
    # Check if there's evidence of recent scraping attempts
    conn = sqlite3.connect('vehicles.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Check for recent vehicle updates (within last 7 days)
    cursor.execute("""
        SELECT towbook_call_number, make, model, last_updated 
        FROM vehicles 
        WHERE last_updated > date('now', '-7 days')
        ORDER BY last_updated DESC
        LIMIT 10
    """)
    recent_updates = cursor.fetchall()
    
    print(f"\nRecent vehicle updates (last 7 days): {len(recent_updates)}")
    for row in recent_updates:
        print(f"  {row['towbook_call_number']}: {row['make']} {row['model']} - {row['last_updated']}")
    
    conn.close()

def main():
    print("Running iTow scraping diagnostic tests...")
    
    # Check current database status
    check_database_status()
    
    # Test direct database insertion
    insertion_success = test_direct_database_insertion()
    
    # Check database status after insertion
    check_database_status()
    
    # Check for scraping logs/activity
    check_scraping_logs()
    
    print("\n" + "=" * 60)
    print("DIAGNOSTIC SUMMARY")
    print("=" * 60)
    print(f"Direct database insertion: {'✓ WORKING' if insertion_success else '✗ FAILED'}")
    print("\nNext steps to investigate BMW/Lexus scraping issue:")
    print("1. Verify TowBook login credentials are correct")
    print("2. Check date range includes BMW/Lexus vehicles")
    print("3. Ensure TowBook account has proper permissions")
    print("4. Test scraping with a recent date range")
    print("5. Check if TowBook website structure has changed")
    
    print("\nTo test real scraping, use the frontend Import Vehicles feature")
    print("or check the scraping API endpoints in the application logs.")

if __name__ == "__main__":
    main()
