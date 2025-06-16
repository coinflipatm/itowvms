#!/usr/bin/env python3

import sqlite3
import sys
import os

print("Starting debug test...")

# Check database exists
db_path = "vehicles.db" 
print(f"Database exists: {os.path.exists(db_path)}")

try:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Get total count
    cursor.execute('SELECT COUNT(*) FROM vehicles')
    total = cursor.fetchone()[0]
    print(f"Total vehicles: {total}")

    # Get status distribution
    cursor.execute('SELECT status, COUNT(*) as count FROM vehicles GROUP BY status ORDER BY count DESC')
    statuses = cursor.fetchall()
    print("Status distribution:")
    for row in statuses:
        print(f"  {row['status']}: {row['count']}")

    # Test active statuses
    active_statuses = ['New', 'TOP Generated', 'Ready for Auction', 'Ready for Scrap']
    placeholders = ','.join(['?'] * len(active_statuses))
    cursor.execute(f'SELECT COUNT(*) FROM vehicles WHERE status IN ({placeholders})', active_statuses)
    active_count = cursor.fetchone()[0]
    print(f"Active vehicles (using active status list): {active_count}")

    # Test completed statuses  
    completed_statuses = ['Released', 'Auctioned', 'Scrapped', 'Transferred']
    placeholders = ','.join(['?'] * len(completed_statuses))
    cursor.execute(f'SELECT COUNT(*) FROM vehicles WHERE status IN ({placeholders})', completed_statuses)
    completed_count = cursor.fetchone()[0]
    print(f"Completed vehicles (using completed status list): {completed_count}")

    # Check if archived field affects results
    cursor.execute('SELECT archived, COUNT(*) FROM vehicles GROUP BY archived')
    archived_dist = cursor.fetchall()
    print("Archived distribution:")
    for row in archived_dist:
        archived_val = row[0] if row[0] is not None else 'NULL'
        print(f"  archived={archived_val}: {row[1]}")

    conn.close()
    print("Debug test complete")

except Exception as e:
    print(f"Error during test: {e}")
    import traceback
    traceback.print_exc()
