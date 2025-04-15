"""
Fix incorrect statuses in the database.
This script corrects any vehicles with incorrect status assignments.
"""
import sqlite3
import logging
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_db_connection():
    """Get a connection to the SQLite database with Row factory"""
    conn = sqlite3.connect('vehicles.db')
    conn.row_factory = sqlite3.Row
    return conn

def log_action(action_type, vehicle_id, details):
    """Log an action to the logs table"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # Create logs table if it doesn't exist
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action_type TEXT,
                vehicle_id TEXT,
                details TEXT,
                timestamp TEXT
            )
        ''')
        
        cursor.execute("INSERT INTO logs (action_type, vehicle_id, details, timestamp) VALUES (?, ?, ?, ?)",
                       (action_type, vehicle_id, details, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logging.error(f"Log error: {e}")
        return False

def fix_incorrect_statuses():
    """Fix vehicles with incorrect status assignments"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check for vehicles with 'Auction' status (should be 'Ready for Auction')
    cursor.execute("SELECT towbook_call_number FROM vehicles WHERE status = 'Auction'")
    auction_vehicles = cursor.fetchall()
    
    # Update incorrect 'Auction' statuses to 'Ready for Auction'
    if auction_vehicles:
        logging.info(f"Found {len(auction_vehicles)} vehicles with incorrect 'Auction' status")
        for vehicle in auction_vehicles:
            call_number = vehicle['towbook_call_number']
            
            # Update to correct status
            cursor.execute("""
                UPDATE vehicles 
                SET status = 'Ready for Auction', 
                    last_updated = ?
                WHERE towbook_call_number = ?
            """, (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), call_number))
            
            # Calculate next auction date (next Monday)
            today = datetime.now().date()
            days_to_monday = (7 - today.weekday()) % 7
            if days_to_monday < 3:  # If Monday is less than 3 days away, use the following Monday
                days_to_monday += 7
            auction_date = today + timedelta(days=days_to_monday)
            
            # Update auction date
            cursor.execute("""
                UPDATE vehicles
                SET auction_date = ?,
                    days_until_auction = ?
                WHERE towbook_call_number = ?
            """, (auction_date.strftime('%Y-%m-%d'), days_to_monday, call_number))
            
            # Log the status correction
            log_action("STATUS_CORRECTION", call_number, f"Changed incorrect status 'Auction' to 'Ready for Auction'")
            logging.info(f"Fixed status for vehicle {call_number}")
    
    conn.commit()
    conn.close()
    
    return len(auction_vehicles) if auction_vehicles else 0

if __name__ == "__main__":
    print("Starting status correction...")
    corrected_count = fix_incorrect_statuses()
    print(f"Status correction complete. {corrected_count} vehicles fixed.")