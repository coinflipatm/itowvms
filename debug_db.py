#!/usr/bin/env python3
import sqlite3
import os
from datetime import datetime

# Database path
db_path = '/workspaces/itowvms/vehicles.db'

print(f"Database file exists: {os.path.exists(db_path)}")
print(f"Database size: {os.path.getsize(db_path)} bytes")

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # List all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print(f"\nTables in database: {[table[0] for table in tables]}")
    
    # Check vehicles table
    if 'vehicles' in [table[0] for table in tables]:
        # Get column info
        cursor.execute("PRAGMA table_info(vehicles);")
        columns = cursor.fetchall()
        print(f"\nVehicles table columns:")
        for col in columns:
            print(f"  {col[1]} ({col[2]})")
        
        # Get total count
        cursor.execute("SELECT COUNT(*) FROM vehicles;")
        total = cursor.fetchone()[0]
        print(f"\nTotal vehicles: {total}")
        
        # Get status distribution
        cursor.execute("SELECT status, COUNT(*) FROM vehicles GROUP BY status ORDER BY COUNT(*) DESC;")
        status_counts = cursor.fetchall()
        print(f"\nStatus distribution:")
        for status, count in status_counts:
            print(f"  {status or 'NULL'}: {count}")
        
        # Get most recent vehicles
        cursor.execute("SELECT id, towbook_call_number, complaint_number, make, model, license_plate, status, tow_date FROM vehicles ORDER BY id DESC LIMIT 10;")
        recent = cursor.fetchall()
        print(f"\nMost recent 10 vehicles:")
        for vehicle in recent:
            print(f"  ID: {vehicle[0]}, Call#: {vehicle[1]}, Complaint#: {vehicle[2]}, {vehicle[3]} {vehicle[4]}, Plate: {vehicle[5]}, Status: {vehicle[6]}, Date: {vehicle[7]}")
    
    conn.close()
    
except Exception as e:
    print(f"Error: {e}")
