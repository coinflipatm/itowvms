#!/usr/bin/env python3
"""
Fix archived field for vehicles that should not be archived.

This script corrects the archived field for vehicles with 'active' statuses 
that were incorrectly marked as archived=1.
"""

import sqlite3
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Define active statuses that should have archived=0
ACTIVE_STATUSES = [
    'New', 
    'TOP Generated', 
    'Ready for Auction', 
    'Ready for Scrap'
]

# Define completed statuses that should have archived=1
COMPLETED_STATUSES = [
    'Released', 
    'Auctioned', 
    'Scrapped', 
    'Transferred'
]

def fix_archived_field():
    """Fix the archived field for vehicles"""
    try:
        logging.info("Starting archived field correction...")
        
        conn = sqlite3.connect('vehicles.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # First, check current state
        cursor.execute("""
            SELECT status, archived, COUNT(*) as count 
            FROM vehicles 
            GROUP BY status, archived 
            ORDER BY status, archived
        """)
        
        logging.info("Current status/archived distribution:")
        for row in cursor.fetchall():
            logging.info(f"  Status: {row['status']}, Archived: {row['archived']}, Count: {row['count']}")
        
        # Fix active statuses that are incorrectly archived
        logging.info("Fixing active statuses that are incorrectly archived...")
        active_statuses_str = "', '".join(ACTIVE_STATUSES)
        
        cursor.execute(f"""
            SELECT COUNT(*) as count 
            FROM vehicles 
            WHERE status IN ('{active_statuses_str}') AND archived = 1
        """)
        
        incorrect_active_count = cursor.fetchone()['count']
        logging.info(f"Found {incorrect_active_count} active vehicles incorrectly marked as archived")
        
        if incorrect_active_count > 0:
            cursor.execute(f"""
                UPDATE vehicles 
                SET archived = 0, last_updated = datetime('now')
                WHERE status IN ('{active_statuses_str}') AND archived = 1
            """)
            logging.info(f"Fixed {cursor.rowcount} active vehicles (set archived=0)")
        
        # Fix completed statuses that are incorrectly not archived
        logging.info("Fixing completed statuses that are incorrectly not archived...")
        completed_statuses_str = "', '".join(COMPLETED_STATUSES)
        
        cursor.execute(f"""
            SELECT COUNT(*) as count 
            FROM vehicles 
            WHERE status IN ('{completed_statuses_str}') AND archived = 0
        """)
        
        incorrect_completed_count = cursor.fetchone()['count']
        logging.info(f"Found {incorrect_completed_count} completed vehicles incorrectly marked as not archived")
        
        if incorrect_completed_count > 0:
            cursor.execute(f"""
                UPDATE vehicles 
                SET archived = 1, last_updated = datetime('now')
                WHERE status IN ('{completed_statuses_str}') AND archived = 0
            """)
            logging.info(f"Fixed {cursor.rowcount} completed vehicles (set archived=1)")
        
        # Commit the changes
        conn.commit()
        
        # Check final state
        logging.info("Final status/archived distribution:")
        cursor.execute("""
            SELECT status, archived, COUNT(*) as count 
            FROM vehicles 
            GROUP BY status, archived 
            ORDER BY status, archived
        """)
        
        for row in cursor.fetchall():
            logging.info(f"  Status: {row['status']}, Archived: {row['archived']}, Count: {row['count']}")
        
        # Summary for active vehicles
        cursor.execute(f"""
            SELECT COUNT(*) as count 
            FROM vehicles 
            WHERE status IN ('{active_statuses_str}') AND archived = 0
        """)
        active_non_archived = cursor.fetchone()['count']
        logging.info(f"Active vehicles that should appear in frontend: {active_non_archived}")
        
        conn.close()
        logging.info("Archived field correction completed successfully!")
        
    except Exception as e:
        logging.error(f"Error fixing archived field: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    fix_archived_field()
