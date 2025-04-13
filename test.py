"""
Status Migration Script for iTow Impound Manager
Maps existing statuses to the new workflow
"""
import sqlite3
import logging
from datetime import datetime

def get_db_connection():
    """Get a connection to the SQLite database with Row factory"""
    conn = sqlite3.connect('vehicles.db')
    conn.row_factory = sqlite3.Row
    return conn

def migrate_statuses():
    """Migrate existing statuses to new workflow"""
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    # Status mapping dictionary (old_status -> new_status)
    status_map = {
        'New': 'New',
        'TOP Sent': 'TOP Generated',  # Older naming
        'TOP_Sent': 'TOP Generated',  # Older naming
        'TOP Generated': 'TOP Generated',
        'Ready': 'TR52 Ready',  # Map legacy "Ready" status to TR52 Ready
        'Scheduled for Release': 'TR52 Ready',  # Previous workflow step
        'Auction': 'Ready for Auction',  # Update to proper workflow
        'Released': 'Released',  # No change
        'Scrapped': 'Scrapped',  # No change
        'Auctioned': 'Auctioned'  # No change
    }
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get all vehicles
        cursor.execute("SELECT towbook_call_number, status, top_form_sent_date, tr52_available_date FROM vehicles")
        vehicles = cursor.fetchall()
        
        # Count statistics
        status_counts = {'before': {}, 'after': {}}
        for vehicle in vehicles:
            old_status = vehicle['status']
            if old_status in status_counts['before']:
                status_counts['before'][old_status] += 1
            else:
                status_counts['before'][old_status] = 1
        
        # Perform migration
        updated_count = 0
        for vehicle in vehicles:
            call_number = vehicle['towbook_call_number']
            old_status = vehicle['status']
            
            # Skip if status is not in the map
            if old_status not in status_map:
                logging.warning(f"Unknown status '{old_status}' for vehicle {call_number}, skipping")
                continue
            
            # Get new status
            new_status = status_map[old_status]
            
            # Update the status
            cursor.execute(
                "UPDATE vehicles SET status = ?, last_updated = ? WHERE towbook_call_number = ?",
                (new_status, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), call_number)
            )
            
            # Update TR52 dates if needed
            if new_status == 'TOP Generated' and not vehicle['tr52_available_date']:
                if vehicle['top_form_sent_date']:
                    # Calculate TR52 date as 20 days after TOP sent
                    try:
                        top_date = datetime.strptime(vehicle['top_form_sent_date'], '%Y-%m-%d')
                        tr52_date = top_date.strftime('%Y-%m-%d')
                        cursor.execute(
                            "UPDATE vehicles SET tr52_available_date = ? WHERE towbook_call_number = ?",
                            (tr52_date, call_number)
                        )
                    except Exception as e:
                        logging.warning(f"Could not calculate TR52 date for {call_number}: {e}")
            
            updated_count += 1
        
        # Get updated status counts
        cursor.execute("SELECT status, COUNT(*) as count FROM vehicles GROUP BY status")
        status_rows = cursor.fetchall()
        for row in status_rows:
            status_counts['after'][row['status']] = row['count']
        
        # Commit changes and close connection
        conn.commit()
        conn.close()
        
        # Print statistics
        logging.info(f"Status migration complete: {updated_count} vehicles updated")
        logging.info("Status counts before migration:")
        for status, count in status_counts['before'].items():
            logging.info(f"  {status}: {count}")
        
        logging.info("Status counts after migration:")
        for status, count in status_counts['after'].items():
            logging.info(f"  {status}: {count}")
        
        return True
    except Exception as e:
        logging.error(f"Error migrating statuses: {e}")
        if conn:
            conn.rollback()
            conn.close()
        return False

if __name__ == "__main__":
    print("Starting status migration...")
    success = migrate_statuses()
    print(f"Migration {'succeeded' if success else 'failed'}.")