"""
Core Database Module
Centralized database operations with proper separation of concerns
"""

import sqlite3
import os
import logging
from flask import g, current_app
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

class DatabaseManager:
    """Centralized database operations"""
    
    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize database with Flask app"""
        self.app = app
        app.teardown_appcontext(self.close_db)
        
        # Ensure database directory exists
        db_path = app.config.get('DATABASE_URL', 'sqlite:///database.db')
        if db_path.startswith('sqlite:///'):
            db_file = db_path.replace('sqlite:///', '')
            db_dir = os.path.dirname(os.path.abspath(db_file))
            os.makedirs(db_dir, exist_ok=True)
    
    def get_db(self):
        """Get database connection"""
        if 'db' not in g:
            db_url = current_app.config['DATABASE_URL']
            if db_url.startswith('sqlite:///'):
                db_path = db_url.replace('sqlite:///', '')
                g.db = sqlite3.connect(db_path)
                g.db.row_factory = sqlite3.Row
                
                # Enable foreign key constraints
                g.db.execute('PRAGMA foreign_keys = ON')
                
        return g.db
    
    def close_db(self, error=None):
        """Close database connection"""
        db = g.pop('db', None)
        if db is not None:
            db.close()
    
    def execute_query(self, query: str, params: tuple = ()) -> sqlite3.Cursor:
        """Execute a database query safely"""
        try:
            db = self.get_db()
            cursor = db.execute(query, params)
            db.commit()
            return cursor
        except sqlite3.Error as e:
            logging.error(f"Database error: {e}")
            raise
    
    def fetch_one(self, query: str, params: tuple = ()) -> Optional[sqlite3.Row]:
        """Fetch single row from database"""
        cursor = self.execute_query(query, params)
        return cursor.fetchone()
    
    def fetch_all(self, query: str, params: tuple = ()) -> List[sqlite3.Row]:
        """Fetch all rows from database"""
        cursor = self.execute_query(query, params)
        return cursor.fetchall()

class VehicleRepository:
    """Vehicle-specific database operations"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    def get_vehicle_by_call_number(self, call_number: str) -> Optional[Dict]:
        """Get vehicle by call number (using existing schema)"""
        query = "SELECT * FROM vehicles WHERE towbook_call_number = ?"
        row = self.db.fetch_one(query, (call_number,))
        return dict(row) if row else None
    
    def get_vehicles_by_status(self, status: str) -> List[Dict]:
        """Get all vehicles with specific status"""
        query = "SELECT * FROM vehicles WHERE status = ? ORDER BY tow_date DESC"
        rows = self.db.fetch_all(query, (status,))
        return [dict(row) for row in rows]
    
    def get_vehicles_needing_seven_day_notice(self) -> List[Dict]:
        """Get vehicles that need 7-day notices sent"""
        # Updated to use actual column names from existing schema
        query = """
        SELECT * FROM vehicles 
        WHERE status = 'INITIAL_HOLD' 
        AND JULIANDAY('now') - JULIANDAY(tow_date) >= 7
        AND tr52_notification_sent IS NULL
        ORDER BY tow_date ASC
        """
        rows = self.db.fetch_all(query)
        return [dict(row) for row in rows]
    
    def update_vehicle_status(self, vehicle_identifier: str, new_status: str, 
                            notes: str = None) -> bool:
        """Update vehicle status with audit trail (using towbook_call_number as identifier)"""
        try:
            # Update vehicle status
            query = "UPDATE vehicles SET status = ?, last_updated = ? WHERE towbook_call_number = ?"
            self.db.execute_query(query, (new_status, datetime.now().isoformat(), vehicle_identifier))
            
            # Log the status change
            self._log_status_change(vehicle_identifier, new_status, notes)
            
            return True
        except Exception as e:
            logging.error(f"Failed to update vehicle {vehicle_identifier} status: {e}")
            return False
    
    def get_latest_vehicle(self) -> Optional[Dict]:
        """Get the most recently towed vehicle"""
        query = "SELECT * FROM vehicles ORDER BY tow_date DESC, towbook_call_number DESC LIMIT 1"
        row = self.db.fetch_one(query)
        return dict(row) if row else None
    
    def get_vehicles_updated_since(self, since_timestamp: str) -> List[Dict]:
        """Get vehicles updated since given timestamp"""
        query = """
        SELECT * FROM vehicles 
        WHERE last_updated >= ? 
        ORDER BY last_updated DESC
        """
        rows = self.db.fetch_all(query, (since_timestamp,))
        return [dict(row) for row in rows]

    def _log_status_change(self, vehicle_identifier: str, new_status: str, notes: str):
        """Log status changes for audit trail (using existing logs table)"""
        query = """
        INSERT INTO logs 
        (action_type, vehicle_id, details, timestamp)
        VALUES (?, ?, ?, ?)
        """
        details = f"Status changed to {new_status}"
        if notes:
            details += f". Notes: {notes}"
        
        self.db.execute_query(query, (
            'status_change', vehicle_identifier, details, datetime.now().isoformat()
        ))

def safe_parse_date(date_str: str) -> Optional[datetime]:
    """Safely parse a date string, returning None if invalid"""
    if not date_str or date_str == 'N/A':
        return None
    
    formats = ['%Y-%m-%d', '%m/%d/%Y', '%Y-%m-%d %H:%M:%S']
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    
    logging.warning(f"Invalid date format encountered: {date_str}")
    return None

# Initialize database manager
db_manager = DatabaseManager()

def init_db(app):
    """Initialize database with Flask app"""
    db_manager.init_app(app)
    
    # Create tables if they don't exist
    with app.app_context():
        create_tables()

def create_tables():
    """Create database tables if they don't exist"""
    
    # Basic tables for backward compatibility with original system
    basic_tables = [
        """CREATE TABLE IF NOT EXISTS vehicles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            call_number TEXT UNIQUE,
            plate_number TEXT,
            vin TEXT,
            make TEXT,
            model TEXT,
            year INTEGER,
            color TEXT,
            tow_company TEXT,
            lot_number TEXT,
            lot_position TEXT,
            date_received DATE,
            time_received TEXT,
            tow_fee DECIMAL(10, 2),
            storage_fee_per_day DECIMAL(10, 2),
            total_fees DECIMAL(10, 2),
            release_reason TEXT,
            release_date DATE,
            release_time TEXT,
            po_number TEXT,
            status TEXT DEFAULT 'INITIAL_HOLD',
            jurisdiction TEXT,
            lien_date DATE,
            violation_codes TEXT,
            description_of_violation TEXT,
            officer_name TEXT,
            officer_badge_number TEXT,
            towing_request_reason TEXT,
            city_hearing_date DATE,
            city_hearing_time TEXT,
            seven_day_notice_sent DATE,
            certified_mail_number TEXT,
            police_log_id TEXT,
            notes TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        
        """CREATE TABLE IF NOT EXISTS contacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            jurisdiction TEXT UNIQUE,
            contact_name TEXT,
            phone_number TEXT,
            email TEXT,
            fax_number TEXT,
            address TEXT,
            additional_notes TEXT
        )""",
        
        """CREATE TABLE IF NOT EXISTS system_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            level TEXT,
            message TEXT,
            category TEXT,
            user_id TEXT
        )""",
        
        """CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vehicle_id INTEGER,
            type TEXT,
            recipient TEXT,
            sent_date DATETIME DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'PENDING',
            message TEXT,
            FOREIGN KEY (vehicle_id) REFERENCES vehicles(id)
        )"""
    ]
    
    # Execute basic table creation first
    for table_sql in basic_tables:
        db_manager.execute_query(table_sql)
    
    logging.info("Basic database tables created successfully")
    
    # Enhanced tables for additional functionality
    tables = [
        """CREATE TABLE IF NOT EXISTS vehicle_lifecycle_stages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vehicle_id INTEGER NOT NULL,
            stage TEXT NOT NULL,
            entered_date DATETIME DEFAULT CURRENT_TIMESTAMP,
            exited_date DATETIME,
            duration_days INTEGER,
            stage_notes TEXT,
            automated_action_taken BOOLEAN DEFAULT FALSE,
            FOREIGN KEY (vehicle_id) REFERENCES vehicles(id)
        )""",
        
        """CREATE TABLE IF NOT EXISTS vehicle_disposition_tracking (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vehicle_id INTEGER NOT NULL,
            disposition_type TEXT NOT NULL,
            approval_date DATETIME,
            scheduled_pickup_date DATETIME,
            pickup_company TEXT,
            pickup_confirmed_date DATETIME,
            physical_removal_date DATETIME,
            payment_amount DECIMAL(10,2),
            documentation_complete BOOLEAN DEFAULT FALSE,
            final_disposition_notes TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (vehicle_id) REFERENCES vehicles(id)
        )""",
        
        """CREATE TABLE IF NOT EXISTS notification_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vehicle_id INTEGER NOT NULL,
            notification_type TEXT NOT NULL,
            recipient TEXT NOT NULL,
            sent_date DATETIME DEFAULT CURRENT_TIMESTAMP,
            delivery_confirmed BOOLEAN DEFAULT FALSE,
            document_generated TEXT,
            towbook_synced BOOLEAN DEFAULT FALSE,
            FOREIGN KEY (vehicle_id) REFERENCES vehicles(id)
        )""",
        
        """CREATE TABLE IF NOT EXISTS vehicle_audit_trail (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vehicle_id INTEGER NOT NULL,
            action_type TEXT NOT NULL,
            action_details TEXT,
            user_id TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            system_generated BOOLEAN DEFAULT FALSE,
            compliance_requirement TEXT,
            FOREIGN KEY (vehicle_id) REFERENCES vehicles(id)
        )"""
    ]
    
    # Execute each table creation separately
    for table_sql in tables:
        db_manager.execute_query(table_sql)
    
    logging.info("Enhanced database tables created successfully")

# Legacy function wrappers for backward compatibility
def get_db_connection():
    """Legacy wrapper for database connection"""
    return db_manager.get_db()

def get_vehicle_by_call_number(call_number: str):
    """Legacy wrapper for getting vehicle by call number"""
    vehicle_repo = VehicleRepository(db_manager)
    return vehicle_repo.get_vehicle_by_call_number(call_number)

def get_vehicles_by_status(status: str):
    """Legacy wrapper for getting vehicles by status"""
    vehicle_repo = VehicleRepository(db_manager)
    return vehicle_repo.get_vehicles_by_status(status)

def update_vehicle_status(vehicle_call_number: str, new_status: str):
    """Legacy wrapper for updating vehicle status"""
    vehicle_repo = VehicleRepository(db_manager)
    return vehicle_repo.update_vehicle_status(vehicle_call_number, new_status)
