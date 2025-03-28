# db_schema_fix.py
import sqlite3
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def fix_database_schema():
    """Add missing columns to the database schema"""
    try:
        # Connect to the database
        conn = sqlite3.connect('vehicles.db')
        cursor = conn.cursor()
        
        # Fix vehicles table - add missing columns
        missing_vehicle_columns = [
            ('days_until_next_step', 'INTEGER'),
            ('days_until_auction', 'INTEGER'),
            ('days_since_tow', 'INTEGER')
        ]
        
        for column_name, column_type in missing_vehicle_columns:
            try:
                # Check if column exists
                cursor.execute(f"SELECT {column_name} FROM vehicles LIMIT 1")
                logging.info(f"Column {column_name} already exists in vehicles table")
            except sqlite3.OperationalError:
                # Column doesn't exist, add it
                cursor.execute(f"ALTER TABLE vehicles ADD COLUMN {column_name} {column_type}")
                logging.info(f"Added column {column_name} to vehicles table")
        
        # Fix logs table - create or update with required columns
        try:
            # Check if logs table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='logs'")
            if cursor.fetchone():
                # Table exists, check if action_type column exists
                try:
                    cursor.execute("SELECT action_type FROM logs LIMIT 1")
                    logging.info("Column action_type already exists in logs table")
                except sqlite3.OperationalError:
                    # Add the missing column
                    cursor.execute("ALTER TABLE logs ADD COLUMN action_type TEXT")
                    logging.info("Added column action_type to logs table")
            else:
                # Create logs table with all required columns
                cursor.execute('''
                    CREATE TABLE logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        action_type TEXT,
                        vehicle_id TEXT,
                        details TEXT,
                        timestamp TEXT
                    )
                ''')
                logging.info("Created logs table with all required columns")
        except Exception as e:
            logging.error(f"Error handling logs table: {e}")
        
        # Verify column counts and print database status
        cursor.execute("PRAGMA table_info(vehicles)")
        vehicle_columns = cursor.fetchall()
        logging.info(f"Vehicles table now has {len(vehicle_columns)} columns")
        
        cursor.execute("PRAGMA table_info(logs)")
        logs_columns = cursor.fetchall()
        logging.info(f"Logs table now has {len(logs_columns)} columns")
        
        # Check vehicle statuses
        cursor.execute("SELECT status, COUNT(*) FROM vehicles GROUP BY status")
        status_counts = cursor.fetchall()
        logging.info("Current vehicle status counts:")
        for status, count in status_counts:
            logging.info(f"  {status}: {count}")
        
        # Commit changes
        conn.commit()
        logging.info("Database schema update completed successfully")
        
        # Print total vehicle count
        cursor.execute("SELECT COUNT(*) FROM vehicles")
        total_vehicles = cursor.fetchone()[0]
        logging.info(f"Total vehicles in database: {total_vehicles}")
        
    except Exception as e:
        logging.error(f"Database schema update failed: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    print("Starting database schema update...")
    fix_database_schema()
    print("Schema update complete. Check the logs for details.")