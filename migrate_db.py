"""
Database migration script for iTow Impound Manager
This script handles database initialization and migrations
"""
import sqlite3
import logging
import os
from datetime import datetime

def get_db_connection():
    """Get a connection to the SQLite database with Row factory"""
    conn = sqlite3.connect('vehicles.db')
    conn.row_factory = sqlite3.Row
    return conn

def initialize_database():
    """Initialize database structure and perform any needed migrations"""
    logging.info("Initializing database...")
    
    # Create database file if it doesn't exist
    if not os.path.exists('vehicles.db'):
        create_new_database()
    else:
        run_migrations()
    
    logging.info("Database initialization complete")
    
def create_new_database():
    """Create a new database from scratch"""
    logging.info("Creating new database...")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create vehicles table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS vehicles (
            towbook_call_number TEXT PRIMARY KEY,
            invoice_number TEXT,
            vin TEXT,
            make TEXT,
            model TEXT,
            year TEXT, 
            color TEXT,
            tow_date TEXT,
            tow_time TEXT,
            location TEXT,
            requestor TEXT,
            status TEXT DEFAULT 'New',
            top_form_sent_date TEXT,
            tr52_available_date TEXT,
            decision TEXT,
            decision_date TEXT,
            action_date TEXT,
            notice_sent_date TEXT,
            last_updated TEXT,
            owner_known TEXT DEFAULT 'Yes',
            archived INTEGER DEFAULT 0,
            release_reason TEXT,
            release_date TEXT,
            release_time TEXT,
            recipient TEXT,
            invoice_prefix TEXT DEFAULT 'IT',
            invoice_sequence INTEGER,
            invoice_year TEXT,
            complaint_number TEXT,
            plate TEXT,
            state TEXT,
            case_number TEXT,
            officer_name TEXT,
            auction_date TEXT,
            auction_id TEXT,
            days_until_next_step INTEGER,
            paperwork_received_date TEXT,
            estimated_date TEXT
        )
    ''')
    
    # Create logs table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action_type TEXT,
            vehicle_id TEXT,
            details TEXT,
            timestamp TEXT
        )
    ''')
    
    # Create auctions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS auctions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            auction_date TEXT,
            ad_date TEXT,
            status TEXT DEFAULT 'Scheduled',
            vin_list TEXT,
            created_date TEXT,
            updated_date TEXT
        )
    ''')
    
    # Create settings table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT,
            updated_at TEXT
        )
    ''')
    
    # Initialize with application version
    cursor.execute('''
        INSERT OR IGNORE INTO settings (key, value, updated_at)
        VALUES (?, ?, ?)
    ''', ('app_version', '1.0.0', datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    
    # Create database_schema_version setting
    cursor.execute('''
        INSERT OR IGNORE INTO settings (key, value, updated_at)
        VALUES (?, ?, ?)
    ''', ('database_schema_version', '1', datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    
    conn.commit()
    conn.close()
    
    # Create directory for generated PDFs
    os.makedirs('static/generated_pdfs', exist_ok=True)
    
    logging.info("New database created successfully")

def run_migrations():
    """Run necessary database migrations to update schema"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # First check if settings table exists and has expected columns
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='settings'")
    settings_exists = cursor.fetchone() is not None
    
    # Get column info if table exists
    if settings_exists:
        cursor.execute("PRAGMA table_info(settings)")
        columns = {row['name'] for row in cursor.fetchall()}
        
        # Check if expected columns exist
        has_key_column = 'key' in columns
        has_value_column = 'value' in columns
        
        # If table exists but doesn't have expected columns, drop and recreate it
        if not (has_key_column and has_value_column):
            logging.info("Settings table exists but has incorrect schema - recreating...")
            cursor.execute("DROP TABLE settings")
            settings_exists = False
    
    # Create settings table if it doesn't exist or was dropped
    if not settings_exists:
        cursor.execute('''
            CREATE TABLE settings (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TEXT
            )
        ''')
        cursor.execute('''
            INSERT INTO settings (key, value, updated_at)
            VALUES (?, ?, ?)
        ''', ('database_schema_version', '0', datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        cursor.execute('''
            INSERT INTO settings (key, value, updated_at)
            VALUES (?, ?, ?)
        ''', ('app_version', '1.0.0', datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        conn.commit()
        current_version = 0
    else:
        # Get current schema version
        try:
            cursor.execute("SELECT value FROM settings WHERE key = 'database_schema_version'")
            result = cursor.fetchone()
            
            if result:
                current_version = int(result['value'])
            else:
                # No version entry - initialize it
                cursor.execute('''
                    INSERT INTO settings (key, value, updated_at)
                    VALUES (?, ?, ?)
                ''', ('database_schema_version', '0', datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
                conn.commit()
                current_version = 0
        except sqlite3.OperationalError as e:
            logging.error(f"Error getting schema version: {e}")
            current_version = 0
    
    # Run migrations based on current version
    if current_version < 1:
        logging.info("Running migration to schema version 1...")
        
        # Check if vehicles table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='vehicles'")
        if not cursor.fetchone():
            # Create vehicles table if it doesn't exist
            cursor.execute('''
                CREATE TABLE vehicles (
                    towbook_call_number TEXT PRIMARY KEY,
                    invoice_number TEXT,
                    vin TEXT,
                    make TEXT,
                    model TEXT,
                    year TEXT, 
                    color TEXT,
                    tow_date TEXT,
                    tow_time TEXT,
                    location TEXT,
                    requestor TEXT,
                    status TEXT DEFAULT 'New',
                    top_form_sent_date TEXT,
                    tr52_available_date TEXT,
                    decision TEXT,
                    decision_date TEXT,
                    action_date TEXT,
                    notice_sent_date TEXT,
                    last_updated TEXT,
                    owner_known TEXT DEFAULT 'Yes',
                    archived INTEGER DEFAULT 0,
                    release_reason TEXT,
                    release_date TEXT,
                    release_time TEXT,
                    recipient TEXT,
                    invoice_prefix TEXT DEFAULT 'IT',
                    invoice_sequence INTEGER,
                    invoice_year TEXT,
                    complaint_number TEXT,
                    plate TEXT,
                    state TEXT,
                    case_number TEXT,
                    officer_name TEXT,
                    auction_date TEXT,
                    auction_id TEXT
                )
            ''')
        
        # Add new columns that might be missing
        try:
            cursor.execute("ALTER TABLE vehicles ADD COLUMN days_until_next_step INTEGER")
        except sqlite3.OperationalError:
            pass  # Column already exists
            
        try:
            cursor.execute("ALTER TABLE vehicles ADD COLUMN paperwork_received_date TEXT")
        except sqlite3.OperationalError:
            pass  # Column already exists
            
        try:
            cursor.execute("ALTER TABLE vehicles ADD COLUMN estimated_date TEXT")
        except sqlite3.OperationalError:
            pass  # Column already exists
        
        # Create logs table if it doesn't exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='logs'")
        if not cursor.fetchone():
            cursor.execute('''
                CREATE TABLE logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    action_type TEXT,
                    vehicle_id TEXT,
                    details TEXT,
                    timestamp TEXT
                )
            ''')
        
        # Create auctions table if it doesn't exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='auctions'")
        if not cursor.fetchone():
            cursor.execute('''
                CREATE TABLE auctions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    auction_date TEXT,
                    ad_date TEXT,
                    status TEXT DEFAULT 'Scheduled',
                    vin_list TEXT,
                    created_date TEXT,
                    updated_date TEXT
                )
            ''')
            
        # Update schema version
        cursor.execute('''
            UPDATE settings SET value = ?, updated_at = ?
            WHERE key = 'database_schema_version'
        ''', ('1', datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        
        conn.commit()
        logging.info("Schema updated to version 1")
    
    # Add future migrations here:
    # if current_version < 2:
    #     # Run migration for version 2
    
    conn.close()
    
if __name__ == '__main__':
    # Configure logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    # Run initialization
    initialize_database()