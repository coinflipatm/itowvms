#!/usr/bin/env python3
import sqlite3

# Database path
db_path = '/workspaces/itowvms/vehicles.db'

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get all unique statuses
    cursor.execute("SELECT DISTINCT status FROM vehicles ORDER BY status;")
    all_statuses = cursor.fetchall()
    print("All statuses in database:")
    for status in all_statuses:
        cursor.execute("SELECT COUNT(*) FROM vehicles WHERE status = ?;", (status[0],))
        count = cursor.fetchone()[0]
        print(f"  {status[0] or 'NULL'}: {count}")
    
    print("\n" + "="*50)
    
    # Get "active" vehicles (not disposed/released/completed)
    excluded_statuses = ['DISPOSED', 'RELEASED', 'COMPLETED', 'Released', 'Scrapped', 'Transferred']
    placeholders = ','.join('?' * len(excluded_statuses))
    
    cursor.execute(f"""
        SELECT status, COUNT(*) 
        FROM vehicles 
        WHERE status NOT IN ({placeholders})
        GROUP BY status 
        ORDER BY COUNT(*) DESC;
    """, excluded_statuses)
    
    active_by_status = cursor.fetchall()
    
    print("Active vehicles (excluding disposed/released/completed statuses):")
    total_active = 0
    for status, count in active_by_status:
        print(f"  {status or 'NULL'}: {count}")
        total_active += count
    
    print(f"\nTotal active vehicles: {total_active}")
    
    # Show some active vehicles
    if total_active > 0:
        cursor.execute(f"""
            SELECT towbook_call_number, complaint_number, make, model, plate, status, tow_date, last_updated 
            FROM vehicles 
            WHERE status NOT IN ({placeholders})
            ORDER BY tow_date DESC 
            LIMIT 10;
        """, excluded_statuses)
        
        recent_active = cursor.fetchall()
        print(f"\nMost recent active vehicles:")
        for vehicle in recent_active:
            print(f"  Call#: {vehicle[0]}, Status: {vehicle[5]}, {vehicle[2]} {vehicle[3]}")
            print(f"    Towed: {vehicle[6]}, Updated: {vehicle[7]}")
    
    conn.close()
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
