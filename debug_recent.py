#!/usr/bin/env python3
import sqlite3
import os
from datetime import datetime

# Database path
db_path = '/workspaces/itowvms/vehicles.db'

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get most recent vehicles by tow_date
    cursor.execute("""
        SELECT towbook_call_number, complaint_number, make, model, plate, status, tow_date, tow_time, last_updated 
        FROM vehicles 
        ORDER BY tow_date DESC, tow_time DESC 
        LIMIT 20;
    """)
    recent = cursor.fetchall()
    print(f"Most recent 20 vehicles by tow date:")
    for i, vehicle in enumerate(recent, 1):
        print(f"{i:2d}. Call#: {vehicle[0] or 'N/A'}, Complaint#: {vehicle[1] or 'N/A'}")
        print(f"     {vehicle[2] or 'N/A'} {vehicle[3] or 'N/A'}, Plate: {vehicle[4] or 'N/A'}")
        print(f"     Status: {vehicle[5] or 'N/A'}, Towed: {vehicle[6] or 'N/A'} {vehicle[7] or 'N/A'}")
        print(f"     Last Updated: {vehicle[8] or 'N/A'}")
        print()
    
    # Check for vehicles with "New" status specifically
    cursor.execute("SELECT COUNT(*) FROM vehicles WHERE status = 'New';")
    new_count = cursor.fetchone()[0]
    print(f"Vehicles with 'New' status: {new_count}")
    
    if new_count > 0:
        cursor.execute("""
            SELECT towbook_call_number, complaint_number, make, model, plate, tow_date, tow_time, last_updated 
            FROM vehicles 
            WHERE status = 'New'
            ORDER BY tow_date DESC;
        """)
        new_vehicles = cursor.fetchall()
        print(f"\nVehicles with 'New' status:")
        for vehicle in new_vehicles:
            print(f"  Call#: {vehicle[0]}, Complaint#: {vehicle[1]}, {vehicle[2]} {vehicle[3]}, Plate: {vehicle[4]}")
            print(f"  Towed: {vehicle[5]} {vehicle[6]}, Updated: {vehicle[7]}")
    
    # Check today's vehicles
    today = datetime.now().strftime('%Y-%m-%d')
    cursor.execute("""
        SELECT COUNT(*) FROM vehicles 
        WHERE tow_date = ? OR DATE(last_updated) = ?;
    """, (today, today))
    today_count = cursor.fetchone()[0]
    print(f"\nVehicles towed or updated today ({today}): {today_count}")
    
    if today_count > 0:
        cursor.execute("""
            SELECT towbook_call_number, complaint_number, make, model, plate, status, tow_date, last_updated 
            FROM vehicles 
            WHERE tow_date = ? OR DATE(last_updated) = ?
            ORDER BY last_updated DESC;
        """, (today, today))
        today_vehicles = cursor.fetchall()
        print(f"\nToday's vehicles:")
        for vehicle in today_vehicles:
            print(f"  Call#: {vehicle[0]}, Status: {vehicle[5]}, {vehicle[2]} {vehicle[3]}")
            print(f"  Towed: {vehicle[6]}, Updated: {vehicle[7]}")
    
    conn.close()
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
