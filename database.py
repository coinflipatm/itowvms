import sqlite3
import os
import logging
from datetime import datetime, timedelta
import re # Added for parsing complaint numbers

# Helper function for safely parsing dates
def safe_parse_date(date_str):
    """Safely parse a date string, returning None if invalid"""
    if not date_str or date_str == 'N/A':
        return None
    
    try:
        return datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        try:
            # Try alternate format
            return datetime.strptime(date_str, '%m/%d/%Y').date()
        except ValueError:
            logging.warning(f"Could not parse date: {date_str}")
            return None

# Make sure we have a consistent database path
def get_database_path():
    # Get the directory where this script is located
    base_dir = os.path.dirname(os.path.abspath(__file__))
    # Define the database file path
    db_path = os.path.join(base_dir, 'vehicles.db')
    return db_path

def get_db_connection():
    try:
        # Try the hardcoded path first
        db_path = r'C:\Users\Finor\impound_lot_manager\itowvms-1\vehicles.db'
        if not os.path.exists(db_path):
            # Fall back to relative path if hardcoded path doesn't exist
            db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'vehicles.db')
            logging.info(f"Using fallback database path: {db_path}")
        
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as e:
        logging.error(f"Database connection error: {e}")
        # Create a more helpful error message
        raise Exception(f"Failed to connect to database at {db_path}. Error: {str(e)}")

def transaction():
    """Context manager for database transactions"""
    class Transaction:
        def __enter__(self):
            self.conn = get_db_connection()
            return self.conn

        def __exit__(self, exc_type, exc_val, exc_tb):
            if (exc_type is not None):
                self.conn.rollback()
            else:
                self.conn.commit()
            self.conn.close()

    return Transaction()

def init_db():
    logging.info("Initializing database...")
    try:
        # Ensure the database directory exists
        db_path = get_database_path()
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Create vehicles table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS vehicles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                towbook_call_number TEXT UNIQUE,
                complaint_number TEXT,
                complaint_sequence INTEGER,
                complaint_year TEXT,
                vin TEXT,
                make TEXT,
                model TEXT,
                year TEXT,
                color TEXT,
                plate TEXT,
                state TEXT DEFAULT 'MI',
                tow_date TEXT,
                tow_time TEXT,
                requestor TEXT,
                location TEXT,
                vehicle_description TEXT,
                status TEXT DEFAULT 'New',
                jurisdiction TEXT,
                registered_owner TEXT,
                registered_address TEXT,
                lienholder TEXT,
                abandoned BOOLEAN DEFAULT 1,
                photo_paths TEXT,
                top_form_sent_date TEXT,
                top_notification_sent BOOLEAN DEFAULT 0,
                tr52_available_date TEXT,
                tr52_received_date TEXT,
                tr208_eligible BOOLEAN DEFAULT 0,
                tr208_available_date TEXT,
                tr208_received_date TEXT,
                paperwork_received_date TEXT,
                decision TEXT,
                decision_date TEXT,
                auction_date TEXT,
                ad_placement_date TEXT,
                auction_ad_sent BOOLEAN DEFAULT 0,
                storage_days INTEGER,
                storage_fees REAL,
                storage_fee_per_day REAL DEFAULT 25.00,
                estimated_date TEXT,
                days_until_auction INTEGER,
                days_until_next_step INTEGER,
                redemption_end_date TEXT,
                release_date TEXT,
                release_time TEXT,
                release_reason TEXT,
                recipient TEXT,
                sale_amount REAL,
                fees REAL,
                net_proceeds REAL,
                certified_mail_number TEXT,
                certified_mail_sent_date TEXT,
                certified_mail_received_date TEXT,
                case_number TEXT,
                officer_name TEXT,
                release_notification_sent BOOLEAN DEFAULT 0,
                inoperable BOOLEAN DEFAULT 0,
                damage_extent TEXT,
                condition_notes TEXT,
                archived BOOLEAN DEFAULT 0,
                salvage_value REAL,
                last_updated TEXT DEFAULT CURRENT_TIMESTAMP,
                requested_by TEXT,
                hearing_date TEXT,
                hearing_requested INTEGER DEFAULT 0,
                newspaper_name TEXT,
                newspaper_contact TEXT,
                lien_amount REAL,
                additional_fees TEXT,
                buyer_name TEXT,
                buyer_id TEXT,
                auction_price REAL,
                vehicle_disposition TEXT
            )
        ''')
        
        # Create police logs table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS police_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vehicle_id TEXT,
                communication_date TEXT,
                communication_type TEXT,
                notes TEXT,
                recipient TEXT,
                contact_method TEXT,
                attachment_path TEXT,
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (vehicle_id) REFERENCES vehicles (towbook_call_number)
            )
        ''')
        
        # Create documents table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vehicle_id TEXT,
                type TEXT,
                filename TEXT,
                upload_date TEXT,
                generated_date TEXT,
                sent_date TEXT,
                sent_to TEXT,
                sent_method TEXT,
                delivery_status TEXT,
                tracking_number TEXT,
                FOREIGN KEY (vehicle_id) REFERENCES vehicles (towbook_call_number)
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
                status TEXT,
                location TEXT,
                auctioneer TEXT,
                advertisement_date TEXT,
                newspaper_name TEXT,
                vin_list TEXT,
                created_date TEXT,
                completed_date TEXT,
                notes TEXT
            )
        ''')
        
        # Create notifications table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vehicle_id TEXT,
                notification_type TEXT, 
                due_date TEXT,
                sent_date TEXT,
                sent_method TEXT,
                recipient TEXT,
                status TEXT,
                reminder_sent INTEGER DEFAULT 0,
                document_path TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (vehicle_id) REFERENCES vehicles (towbook_call_number)
            )
        ''')
        
        # Create contacts table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS contacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                jurisdiction TEXT UNIQUE,
                contact_name TEXT,
                phone TEXT,
                email TEXT,
                fax TEXT,
                address TEXT,
                preferred_method TEXT,
                notes TEXT
            )
        ''')

        # Create complaint_sequence_override table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS complaint_sequence_override (
                year TEXT PRIMARY KEY,
                next_sequence_number INTEGER NOT NULL
            )
        """)
        logging.info("Ensured complaint_sequence_override table exists.")

        # Add indices for performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_vehicles_status ON vehicles(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_vehicles_tow_date ON vehicles(tow_date)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_vehicles_jurisdiction ON vehicles(jurisdiction)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_police_logs_vehicle_id ON police_logs(vehicle_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_documents_vehicle_id ON documents(vehicle_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_notifications_vehicle_id ON notifications(vehicle_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_notifications_due_date ON notifications(due_date)')
        
        # Insert default contacts for common jurisdictions if table is empty
        cursor.execute("SELECT COUNT(*) FROM contacts")
        if cursor.fetchone()[0] == 0:
            default_jurisdictions = [
                ('Flint', 'Flint Police Department', '810-555-0100', 'flint-pd@example.com', '810-555-0101', '123 Main St, Flint, MI', 'email'),
                ('Burton', 'Burton Police Department', '810-555-0200', 'burton-pd@example.com', '810-555-0201', '456 Oak St, Burton, MI', 'fax'),
                ('Grand Blanc', 'Grand Blanc Police', '810-555-0300', 'grandblanc-pd@example.com', '810-555-0301', '789 Maple St, Grand Blanc, MI', 'email'),
                ('Flushing', 'Flushing Police Department', '810-555-0400', 'flushing-pd@example.com', '810-555-0401', '101 Pine St, Flushing, MI', 'fax'),
                ('Clio', 'Clio Police Department', '810-555-0500', 'clio-pd@example.com', '810-555-0501', '202 Elm St, Clio, MI', 'email')
            ]
            for jurisdiction in default_jurisdictions:
                cursor.execute('''
                    INSERT INTO contacts (jurisdiction, contact_name, phone, email, fax, address, preferred_method)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', jurisdiction)
        
        conn.commit()
        conn.close()
        logging.info("Database initialized successfully")
    except Exception as e:
        logging.error(f"Database initialization error: {e}")
        raise

def get_vehicles_by_status(status_type, sort_column=None, sort_direction=None, include_archived=False):
    from utils import get_status_filter
    try:
        # Accept a list of statuses or a single status
        if isinstance(status_type, list):
            status_filter = status_type
        else:
            # Convert underscored status to space format to match database
            original_status_type = status_type
            if status_type == 'TOP_Generated':
                status_type = 'TOP Generated'
            elif status_type == 'TR52_Ready':
                status_type = 'TR52 Ready'  
            elif status_type == 'TR208_Ready':
                status_type = 'TR208 Ready'
            elif status_type == 'Ready_for_Auction':
                status_type = 'Ready for Auction'
            elif status_type == 'Ready_for_Scrap':
                status_type = 'Ready for Scrap'
            status_filter = get_status_filter(status_type)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        query = "SELECT * FROM vehicles WHERE "
        if include_archived:
            query += f"status IN ({','.join(['?' for _ in status_filter])}) AND archived = 1"
        else:
            query += f"status IN ({','.join(['?' for _ in status_filter])}) AND archived = 0"
        
        # Add sort if provided
        if sort_column:
            valid_columns = [
                'towbook_call_number', 'complaint_number', 'vin', 'make', 'model', 
                'year', 'color', 'tow_date', 'jurisdiction', 'status', 'last_updated'
            ]
            if sort_column in valid_columns:
                sort_dir = "ASC" if sort_direction and sort_direction.lower() == 'asc' else "DESC"
                query += f" ORDER BY {sort_column} {sort_dir}"
        else:
            query += " ORDER BY tow_date DESC"
        
        rows = cursor.execute(query, status_filter).fetchall()
        vehicles = [dict(row) for row in rows]
        
        # Add days calculations with improved error handling
        today = datetime.now().date()
        for vehicle in vehicles:
            for key in vehicle:
                if vehicle[key] is None:
                    vehicle[key] = 'N/A'
            if vehicle.get('tow_date') and vehicle['tow_date'] != 'N/A':
                tow_date = safe_parse_date(vehicle['tow_date'])
                if tow_date:
                    vehicle['days_since_tow'] = (today - tow_date).days
                else:
                    vehicle['days_since_tow'] = 0
            # ...existing code for next step calculations...
        conn.close()
        return vehicles
    except Exception as e:
        logging.error(f"Get vehicles error: {e}")
        return []

def update_vehicle_status(call_number, new_status, update_fields=None):
    from utils import log_action, is_eligible_for_tr208, calculate_tr208_timeline, calculate_next_auction_date, calculate_newspaper_ad_date
    
    # First, convert any underscored status to space format
    if new_status == 'TOP_Generated':
        new_status = 'TOP Generated'
    elif new_status == 'TR52_Ready':
        new_status = 'TR52 Ready'  
    elif new_status == 'TR208_Ready':
        new_status = 'TR208 Ready'
    elif new_status == 'Ready_for_Auction':
        new_status = 'Ready for Auction'
    elif new_status == 'Ready_for_Scrap':
        new_status = 'Ready for Scrap'
        
    logging.info(f"Updating vehicle {call_number} status to: {new_status}")
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM vehicles WHERE towbook_call_number = ?", (call_number,))
        vehicle = cursor.fetchone()
        if not vehicle:
            conn.close()
            return False

        if not update_fields:
            update_fields = {}

        # Get valid column names
        cursor.execute("PRAGMA table_info(vehicles)")
        valid_columns = set(row[1] for row in cursor.fetchall())

        # Filter update_fields to only include valid columns
        update_fields = {k: v for k, v in update_fields.items() if k in valid_columns}

        update_fields['status'] = new_status
        update_fields['last_updated'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        if new_status == 'TOP Generated':
            top_date = datetime.now()
            update_fields['top_form_sent_date'] = top_date.strftime('%Y-%m-%d')

            # Check TR208 eligibility
            vehicle_data = dict(vehicle)
            tr208_eligible, _ = is_eligible_for_tr208(vehicle_data)
            update_fields['tr208_eligible'] = 1 if tr208_eligible else 0

            if tr208_eligible:
                # If eligible for TR208, set timeline to 27 days
                tr208_date = calculate_tr208_timeline(top_date)
                update_fields['tr208_available_date'] = tr208_date.strftime('%Y-%m-%d')
                update_fields['days_until_next_step'] = 27
            else:
                # Otherwise, standard TR52 path (20 days)
                tr52_date = top_date + timedelta(days=20)
                update_fields['tr52_available_date'] = tr52_date.strftime('%Y-%m-%d')
                update_fields['days_until_next_step'] = 20

            update_fields['redemption_end_date'] = (top_date + timedelta(days=30)).strftime('%Y-%m-%d')

            # Create notification record for either TR52 or TR208 document
            if tr208_eligible:
                cursor.execute("""
                    INSERT INTO notifications
                    (vehicle_id, notification_type, due_date, status)
                    VALUES (?, ?, ?, ?)
                """, (call_number, 'TR208', update_fields['tr208_available_date'], 'pending'))
            else:
                cursor.execute("""
                    INSERT INTO notifications
                    (vehicle_id, notification_type, due_date, status)
                    VALUES (?, ?, ?, ?)
                """, (call_number, 'TR52', update_fields['tr52_available_date'], 'pending'))

        elif new_status == 'TR52 Ready':
            # No specific fields to update, handled by update_fields parameter
            pass

        elif new_status == 'TR208 Ready':
            if 'tr208_received_date' not in update_fields:
                update_fields['tr208_received_date'] = datetime.now().strftime('%Y-%m-%d')

        elif new_status == 'Ready for Auction':
            if 'auction_date' in update_fields and update_fields['auction_date']:
                auction_date = datetime.strptime(update_fields['auction_date'], '%Y-%m-%d')
            else:
                ad_placement_date = vehicle.get('ad_placement_date')
                auction_date = calculate_next_auction_date(ad_placement_date)
                update_fields['auction_date'] = auction_date.strftime('%Y-%m-%d')
                
            update_fields['decision'] = 'Auction'
            update_fields['decision_date'] = datetime.now().strftime('%Y-%m-%d')
            days_until_auction = (auction_date.date() - datetime.now().date()).days
            update_fields['days_until_auction'] = max(0, days_until_auction)

            # Set ad placement date if not already set
            if 'ad_placement_date' not in update_fields or not update_fields['ad_placement_date']:
                ad_date = calculate_newspaper_ad_date(auction_date)
                update_fields['ad_placement_date'] = ad_date.strftime('%Y-%m-%d')

            # Create notification record for auction advertisement
            cursor.execute("""
                INSERT INTO notifications
                (vehicle_id, notification_type, due_date, status)
                VALUES (?, ?, ?, ?)
            """, (call_number, 'Auction_Ad', update_fields['ad_placement_date'], 'pending'))

        elif new_status == 'Ready for Scrap':
            scrap_date = datetime.now() + timedelta(days=7)
            update_fields['estimated_date'] = scrap_date.strftime('%Y-%m-%d')
            update_fields['decision'] = 'Scrap'
            update_fields['decision_date'] = datetime.now().strftime('%Y-%m-%d')
            update_fields['days_until_next_step'] = 7
            update_fields['vehicle_disposition'] = 'Scrap'

            # Create notification record for scrap photos
            cursor.execute("""
                INSERT INTO notifications
                (vehicle_id, notification_type, due_date, status)
                VALUES (?, ?, ?, ?)
            """, (call_number, 'Scrap_Photos', scrap_date.strftime('%Y-%m-%d'), 'pending'))

        elif new_status == 'Released':
            update_fields['archived'] = 1
            update_fields['release_date'] = update_fields.get('release_date', datetime.now().strftime('%Y-%m-%d'))
            update_fields['release_time'] = update_fields.get('release_time', datetime.now().strftime('%H:%M'))
            update_fields['release_reason'] = update_fields.get('release_reason', 'Owner Redeemed')
            update_fields['vehicle_disposition'] = 'Redeemed'

            # Create notification record for release notification
            cursor.execute("""
                INSERT INTO notifications
                (vehicle_id, notification_type, due_date, status)
                VALUES (?, ?, ?, ?)
            """, (call_number, 'Release_Notice', update_fields['release_date'], 'pending'))

        elif new_status == 'Auctioned':
            update_fields['archived'] = 1
            update_fields['release_date'] = update_fields.get('release_date', datetime.now().strftime('%Y-%m-%d'))
            update_fields['release_time'] = update_fields.get('release_time', datetime.now().strftime('%H:%M'))
            update_fields['release_reason'] = 'Auctioned'
            update_fields['vehicle_disposition'] = 'Auctioned'

            if 'sale_amount' in update_fields and 'fees' in update_fields:
                try:
                    sale_amount = float(update_fields['sale_amount'])
                    fees = float(update_fields['fees'])
                    update_fields['net_proceeds'] = sale_amount - fees
                except (ValueError, TypeError):
                    update_fields['net_proceeds'] = 0

            # Create notification record for release notification
            cursor.execute("""
                INSERT INTO notifications
                (vehicle_id, notification_type, due_date, status)
                VALUES (?, ?, ?, ?)
            """, (call_number, 'Release_Notice', update_fields['release_date'], 'pending'))

        elif new_status == 'Scrapped':
            update_fields['archived'] = 1
            update_fields['release_date'] = update_fields.get('release_date', datetime.now().strftime('%Y-%m-%d'))
            update_fields['release_reason'] = 'Scrapped'
            update_fields['vehicle_disposition'] = 'Scrapped'

            # Create notification record for release notification
            cursor.execute("""
                INSERT INTO notifications
                (vehicle_id, notification_type, due_date, status)
                VALUES (?, ?, ?, ?)
            """, (call_number, 'Release_Notice', update_fields['release_date'], 'pending'))

        elif new_status == 'Transferred':
            update_fields['archived'] = 1
            update_fields['release_date'] = update_fields.get('release_date', datetime.now().strftime('%Y-%m-%d'))
            update_fields['release_reason'] = 'Transferred to Custodian'
            update_fields['vehicle_disposition'] = 'Transferred'

            # Create notification record for release notification
            cursor.execute("""
                INSERT INTO notifications
                (vehicle_id, notification_type, due_date, status)
                VALUES (?, ?, ?, ?)
            """, (call_number, 'Release_Notice', update_fields['release_date'], 'pending'))

        # Ensure all fields in update_fields exist in the database
        update_fields = {k: v for k, v in update_fields.items() if k in valid_columns}

        set_clause = ', '.join([f"{k} = ?" for k in update_fields.keys()])
        values = list(update_fields.values()) + [call_number]
        cursor.execute(f'UPDATE vehicles SET {set_clause} WHERE towbook_call_number = ?', values)
        conn.commit()
        conn.close()
        log_action("STATUS_CHANGE", call_number, f"Status changed to {new_status}")
        return True
    except Exception as e:
        logging.error(f"Status update error: {e}")
        return False

def update_vehicle(call_number, data):
    from utils import log_action
    logging.info(f"Updating vehicle {call_number}: {data}")
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get existing columns from the database
        cursor.execute("PRAGMA table_info(vehicles)")
        existing_columns = [row[1] for row in cursor.fetchall()]
        
        # Verify the vehicle exists
        cursor.execute("SELECT * FROM vehicles WHERE towbook_call_number = ?", (call_number,))
        if not cursor.fetchone():
            conn.close()
            return False, "Vehicle not found"
        
        # Filter out any fields that don't exist in the database
        filtered_data = {k: v for k, v in data.items() if k in existing_columns}
        
        # Explicitly handle the 'requested_by' case - map it to 'requestor' if needed
        if 'requested_by' in data and 'requested_by' not in existing_columns:
            if 'requestor' in existing_columns:
                filtered_data['requestor'] = data['requested_by']

        # If complaint_number is being updated, try to parse and set sequence/year
        if 'complaint_number' in filtered_data:
            new_complaint_number = filtered_data['complaint_number']
            if new_complaint_number and new_complaint_number != 'N/A':
                match = re.fullmatch(r"IT(\d{4})-(\d{2})", new_complaint_number)
                if match:
                    sequence_str, year_str = match.groups()
                    if 'complaint_sequence' in existing_columns:
                        filtered_data['complaint_sequence'] = int(sequence_str)
                    if 'complaint_year' in existing_columns:
                        filtered_data['complaint_year'] = year_str
                    logging.info(f"Parsed edited complaint number {new_complaint_number} to sequence {sequence_str} and year {year_str}")
                else:
                    # If format is custom, nullify sequence and year if columns exist
                    if 'complaint_sequence' in existing_columns:
                        filtered_data['complaint_sequence'] = None 
                    if 'complaint_year' in existing_columns:
                        filtered_data['complaint_year'] = None
                    logging.warning(f"Custom complaint number format {new_complaint_number} during edit. Sequence and year set to NULL.")
            elif not new_complaint_number or new_complaint_number == 'N/A': # If complaint number is cleared
                 if 'complaint_sequence' in existing_columns:
                        filtered_data['complaint_sequence'] = None
                 if 'complaint_year' in existing_columns:
                        filtered_data['complaint_year'] = None
                 logging.info(f"Complaint number cleared for {call_number}. Sequence and year set to NULL.")
        
        # Update the 'last_updated' timestamp
        filtered_data['last_updated'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Clean data to prevent NULL values (ensure this doesn't overwrite deliberate None for sequence/year)
        for key, value in filtered_data.items():
            if key not in ['complaint_sequence', 'complaint_year'] and (value is None or value == ''):
                filtered_data[key] = 'N/A'
            elif (key == 'complaint_sequence' or key == 'complaint_year') and value == '': # Treat empty string for seq/year as N/A or None
                 filtered_data[key] = None


        # Update each field in the data dictionary
        set_clause = ', '.join([f"{key} = ?" for key in filtered_data.keys()])
        values = list(filtered_data.values()) + [call_number]
        
        cursor.execute(f"UPDATE vehicles SET {set_clause} WHERE towbook_call_number = ?", values)
        conn.commit()
        conn.close()
        
        log_action("UPDATE", call_number, "Vehicle updated")
        return True, "Vehicle updated successfully"
    except Exception as e:
        logging.error(f"Error updating vehicle: {e}")
        return False, str(e)

def insert_vehicle(data):
    from utils import log_action, generate_complaint_number
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Standardize 'requested_by' to 'requestor'
        if 'requested_by' in data:
            # If 'requestor' is not already in data or is empty/N/A,
            # move value from 'requested_by' to 'requestor'.
            # Otherwise, 'requestor' takes precedence if it has a value.
            if data.get('requestor') is None or data.get('requestor') == 'N/A' or data.get('requestor') == '':
                data['requestor'] = data.pop('requested_by')
                logging.info("Mapped 'requested_by' to 'requestor' in input data for insert_vehicle as 'requestor' was empty/missing.")
            else:
                # 'requestor' has a value, so just remove 'requested_by' to avoid conflict
                data.pop('requested_by')
                logging.info("'requested_by' also found in input data but 'requestor' already had a value. Using 'requestor', 'requested_by' removed.")
        
        towbook_call_number = data.get('towbook_call_number')
        cursor.execute("SELECT COUNT(*) FROM vehicles WHERE towbook_call_number = ?", (towbook_call_number,))
        exists = cursor.fetchone()[0] > 0
        
        # Clean data to prevent NULL values
        for key in list(data.keys()): # Iterate over a copy of keys for safe deletion
            if data[key] is None or data[key] == '':
                # Allow complaint_sequence and complaint_year to be None/NULL if intentionally cleared
                if key in ['complaint_sequence', 'complaint_year']:
                    data[key] = None
                else:
                    data[key] = 'N/A'
            # Ensure boolean fields are 0 or 1, not N/A
            elif key in ['archived', 'top_notification_sent', 'tr208_eligible', 'auction_ad_sent', 'release_notification_sent', 'inoperable', 'hearing_requested'] and data[key] == 'N/A':
                data[key] = 0 # Default to false if N/A

        # Handle complaints
        # If complaint_number is not provided or is 'N/A', or if its constituent parts are missing
        if (data.get('complaint_number') == 'N/A' or not data.get('complaint_number')) or \
           (data.get('complaint_sequence') is None and data.get('complaint_year') is None):
            complaint_number_val, sequence_val, year_val = generate_complaint_number()
            data['complaint_number'] = complaint_number_val
            data['complaint_sequence'] = sequence_val
            data['complaint_year'] = year_val
            logging.info(f"Generated new complaint details for {towbook_call_number}: {complaint_number_val}, seq: {sequence_val}, year: {year_val}")
        elif data.get('complaint_number') and (data.get('complaint_sequence') is None or data.get('complaint_year') is None):
            # Complaint number is provided, but sequence/year might be missing (e.g. manual entry)
            match = re.fullmatch(r"IT(\d{4})-(\d{2})", data['complaint_number'])
            if match:
                sequence_str, year_str = match.groups()
                data['complaint_sequence'] = int(sequence_str)
                data['complaint_year'] = year_str
                logging.info(f"Parsed provided complaint number {data['complaint_number']} to sequence {sequence_str} and year {year_str} for new vehicle.")
            else:
                data['complaint_sequence'] = None
                data['complaint_year'] = None
                logging.warning(f"Custom complaint number format {data['complaint_number']} for new vehicle. Sequence and year set to NULL.")
        # If complaint_number, complaint_sequence, and complaint_year are all provided, they are assumed to be correct and will be used.

        # Get existing columns from the database to filter data before insert/update
        cursor.execute("PRAGMA table_info(vehicles)")
        existing_columns = [row[1] for row in cursor.fetchall()]
        
        # Ensure last_updated is always set for new inserts
        data['last_updated'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        filtered_data = {k: v for k, v in data.items() if k in existing_columns}

        if exists:
            # Build update query dynamically based on provided fields
            fields = []
            values = []
            for key, value in filtered_data.items(): # Use filtered_data
                if key != 'towbook_call_number':  # Skip primary key
                    fields.append(f"{key} = ?")
                    values.append(value)
            
            # Add the WHERE condition value
            values.append(towbook_call_number)
            
            # Execute the update query
            cursor.execute(f"""
                UPDATE vehicles SET
                    {", ".join(fields)},
                    last_updated = ?
                WHERE towbook_call_number = ?
            """, values + [datetime.now().strftime('%Y-%m-%d %H:%M:%S'), towbook_call_number])
            
            logging.info(f"Updated existing vehicle {towbook_call_number}")
        else:
            # For INSERT, we need field names and placeholders
            field_names = list(filtered_data.keys()) # Use filtered_data
            placeholders = ["?"] * len(field_names)
            values = list(filtered_data.values()) # Use filtered_data

            cursor.execute(f"""
                INSERT INTO vehicles (
                    {", ".join(field_names)}
                ) VALUES ({", ".join(placeholders)})
            """, values)
            
            logging.info(f"Inserted new vehicle {towbook_call_number} with data: {filtered_data}")
            
            # Create initial notification records
            if 'tow_date' in data and data['tow_date'] != 'N/A':
                try:
                    tow_date = datetime.strptime(data['tow_date'], '%Y-%m-%d')
                    top_due_date = tow_date + timedelta(days=1)
                    cursor.execute("""
                        INSERT INTO notifications
                        (vehicle_id, notification_type, due_date, status)
                        VALUES (?, ?, ?, ?)
                    """, (towbook_call_number, 'TOP', top_due_date.strftime('%Y-%m-%d'), 'pending'))
                except ValueError as e:
                    logging.warning(f"Could not parse tow date '{data['tow_date']}' for {towbook_call_number}: {e}")
        
        conn.commit()
        conn.close()
        log_action("INSERT", towbook_call_number, f"Added vehicle: {data.get('make', 'N/A')} {data.get('model', 'N/A')}")
        return True, "Vehicle added successfully"
    except Exception as e:
        logging.error(f"Insert error: {e}")
        return False, str(e)

def check_and_update_statuses():
    """Check and update vehicle statuses based on date thresholds"""
    from utils import log_action
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM vehicles WHERE archived = 0")
        vehicles = cursor.fetchall()
        today = datetime.now().date()
        
        # Create notifications table if needed
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vehicle_id TEXT,
                notification_type TEXT,
                due_date TEXT,
                sent_date TEXT,
                sent_method TEXT,
                recipient TEXT,
                status TEXT,
                reminder_sent INTEGER DEFAULT 0,
                document_path TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (vehicle_id) REFERENCES vehicles (towbook_call_number)
            )
        """)
        
        for vehicle in vehicles:
            # Handle tow date - use safe_parse_date from utils.py
            try:
                from utils import safe_parse_date
                tow_date_str = vehicle['tow_date']
                if tow_date_str and tow_date_str != 'N/A':
                    tow_date = safe_parse_date(tow_date_str)
                    
                    # Only proceed if we have a valid tow_date
                    if tow_date:
                        # Store the tow_date in standard format in the database
                        cursor.execute(
                            "UPDATE vehicles SET tow_date = ? WHERE towbook_call_number = ?",
                            (tow_date.strftime('%Y-%m-%d'), vehicle['towbook_call_number'])
                        )

                        # Handle TOP Generated status
                        if vehicle['status'] == 'TOP Generated' and vehicle['top_form_sent_date']:
                            top_date = safe_parse_date(vehicle['top_form_sent_date'])
                            if top_date:
                                days_since_top = (today - top_date).days
                                
                                # Check if vehicle is eligible for TR208
                                if vehicle['tr208_eligible'] == 1:
                                    # Process TR208 available date
                                    tr208_date = None
                                    if vehicle['tr208_available_date']:
                                        tr208_date = safe_parse_date(vehicle['tr208_available_date'])
                                    else:
                                        # Default to top_date + 27 days if not set
                                        tr208_date = top_date + timedelta(days=27)
                                    
                                    if tr208_date and today >= tr208_date:
                                        cursor.execute("""
                                            UPDATE vehicles SET status = ?, last_updated = ?
                                            WHERE towbook_call_number = ?
                                        """, ('TR208 Ready', datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                             vehicle['towbook_call_number']))

                                        # Create notification for TR208 ready
                                        cursor.execute("""
                                            INSERT INTO notifications
                                            (vehicle_id, notification_type, due_date, status)
                                            VALUES (?, ?, ?, ?)
                                        """, (vehicle['towbook_call_number'], 'TR208_Ready',
                                             today.strftime('%Y-%m-%d'), 'pending'))

                                        log_action("AUTO_STATUS", vehicle['towbook_call_number'],
                                                 "Automatically moved to TR208 Ready status")
                                    elif tr208_date:
                                        days_left = (tr208_date - today).days
                                        cursor.execute("""
                                            UPDATE vehicles SET days_until_next_step = ?
                                            WHERE towbook_call_number = ?
                                        """, (days_left, vehicle['towbook_call_number']))
                                else:
                                    # Standard TR52 path
                                    if days_since_top >= 20:
                                        cursor.execute("""
                                            UPDATE vehicles SET status = ?, last_updated = ?
                                            WHERE towbook_call_number = ?
                                        """, ('TR52 Ready', datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                             vehicle['towbook_call_number']))

                                        # Create notification for TR52 ready
                                        cursor.execute("""
                                            INSERT INTO notifications
                                            (vehicle_id, notification_type, due_date, status)
                                            VALUES (?, ?, ?, ?)
                                        """, (vehicle['towbook_call_number'], 'TR52_Ready',
                                             today.strftime('%Y-%m-%d'), 'pending'))

                                        log_action("AUTO_STATUS", vehicle['towbook_call_number'],
                                                 "Automatically moved to TR52 Ready status after 20 days")
                                    else:
                                        days_left = 20 - days_since_top
                                        cursor.execute("""
                                            UPDATE vehicles SET days_until_next_step = ?
                                            WHERE towbook_call_number = ?
                                        """, (days_left, vehicle['towbook_call_number']))

                                        # Check if we should send a reminder at 15 days
                                        if days_since_top == 15:
                                            cursor.execute("""
                                                INSERT INTO notifications
                                                (vehicle_id, notification_type, due_date, status)
                                                VALUES (?, ?, ?, ?)
                                            """, (vehicle['towbook_call_number'], 'TOP_Reminder',
                                                 today.strftime('%Y-%m-%d'), 'pending'))

                        # Handle Ready for Auction status
                        elif vehicle['status'] == 'Ready for Auction' and vehicle['auction_date']:
                            auction_date = safe_parse_date(vehicle['auction_date'])
                            if auction_date:
                                days_until_auction = (auction_date - today).days
                                cursor.execute("""
                                    UPDATE vehicles SET days_until_auction = ?
                                    WHERE towbook_call_number = ?
                                """, (max(0, days_until_auction), vehicle['towbook_call_number']))

                                # Create notification for auction ad 10 days before auction
                                if days_until_auction == 10 and not vehicle['auction_ad_sent']:
                                    cursor.execute("""
                                        INSERT INTO notifications
                                        (vehicle_id, notification_type, due_date, status)
                                        VALUES (?, ?, ?, ?)
                                    """, (vehicle['towbook_call_number'], 'Auction_Ad',
                                         today.strftime('%Y-%m-%d'), 'pending'))

                                # Create notification for auction report day after auction
                                if days_until_auction == -1:
                                    cursor.execute("""
                                        INSERT INTO notifications
                                        (vehicle_id, notification_type, due_date, status)
                                        VALUES (?, ?, ?, ?)
                                    """, (vehicle['towbook_call_number'], 'Auction_Report',
                                         today.strftime('%Y-%m-%d'), 'pending'))

                                if days_until_auction < -1:
                                    cursor.execute("""
                                        UPDATE vehicles SET status = ?, archived = 1, release_reason = ?,
                                        release_date = ?, last_updated = ?
                                        WHERE towbook_call_number = ?
                                    """, ('Auctioned', 'Auto-completed auction',
                                         auction_date.strftime('%Y-%m-%d'),
                                         datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                         vehicle['towbook_call_number']))
                                    log_action("AUTO_STATUS", vehicle['towbook_call_number'],
                                             "Automatically marked as Auctioned after auction date")

                        # Handle Ready for Scrap status
                        elif vehicle['status'] == 'Ready for Scrap':
                            days_since_tow = (today - tow_date).days if tow_date else 0
                            if days_since_tow < 27:
                                days_left = 27 - days_since_tow
                                cursor.execute("""
                                    UPDATE vehicles SET days_until_next_step = ?
                                    WHERE towbook_call_number = ?
                                """, (days_left, vehicle['towbook_call_number']))

                                # Create notification for scrap photos 1 day before legal scrap date
                                if days_left == 1:
                                    cursor.execute("""
                                        INSERT INTO notifications
                                        (vehicle_id, notification_type, due_date, status)
                                        VALUES (?, ?, ?, ?)
                                    """, (vehicle['towbook_call_number'], 'Scrap_Photos',
                                         today.strftime('%Y-%m-%d'), 'pending'))
                            else:
                                cursor.execute("""
                                    UPDATE vehicles SET days_until_next_step = 0
                                    WHERE towbook_call_number = ?
                                """, (vehicle['towbook_call_number'],))
            except Exception as e:
                # logging.warning(f"Date processing error for {vehicle['towbook_call_number']}: {e}")  # Suppressed per requirements
                pass

        # Check for any pending notifications
        cursor.execute("""
            SELECT n.*, v.jurisdiction
            FROM notifications n
            JOIN vehicles v ON n.vehicle_id = v.towbook_call_number
            WHERE n.status = 'pending' AND n.due_date <= ?
        """, (today.strftime('%Y-%m-%d'),))

        pending_notifications = cursor.fetchall()
        for notification in pending_notifications:
            # Get jurisdiction contact info
            cursor.execute("""
                SELECT * FROM contacts
                WHERE jurisdiction = ?
            """, (notification['jurisdiction'],))
            contact = cursor.fetchone()

            if contact:
                # Update notification with contact info
                cursor.execute("""
                    UPDATE notifications
                    SET recipient = ?, sent_method = ?
                    WHERE id = ?
                """, (contact['contact_name'], contact['preferred_method'], notification['id']))

            # Log the pending notification
            log_action("NOTIFICATION", notification['vehicle_id'],
                     f"Pending {notification['notification_type']} notification due {notification['due_date']}")

        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logging.error(f"Status check error: {e}")
        return False

def get_vehicles(tab, sort_column=None, sort_direction='asc'):
    """
    Enhanced version of get_vehicles with improved error handling
    """
    try:
        # Special handling for status types that come with underscores from frontend
        if tab == 'TOP_Generated':
            return get_vehicles_by_status('TOP Generated', sort_column, sort_direction)
        elif tab == 'TR52_Ready':
            return get_vehicles_by_status('TR52 Ready', sort_column, sort_direction)
        elif tab == 'TR208_Ready':
            return get_vehicles_by_status('TR208 Ready', sort_column, sort_direction)
        elif tab == 'Ready_for_Auction':
            return get_vehicles_by_status('Ready for Auction', sort_column, sort_direction)
        elif tab == 'Ready_for_Scrap':
            return get_vehicles_by_status('Ready for Scrap', sort_column, sort_direction)
        elif tab == 'active':
            conn = get_db_connection()
            cursor = conn.cursor()
            sort_by = "tow_date DESC"
            if sort_column:
                valid_columns = [
                    'towbook_call_number', 'complaint_number', 'vin', 'make', 'model',
                    'year', 'color', 'tow_date', 'jurisdiction', 'status', 'last_updated'
                ]
                if sort_column in valid_columns:
                    sort_dir = "ASC" if sort_direction.lower() == 'asc' else "DESC"
                    sort_by = f"{sort_column} {sort_dir}"
            cursor.execute(f"SELECT * FROM vehicles WHERE archived = 0 ORDER BY {sort_by}")
            vehicles = cursor.fetchall()
            
            # Convert row objects to dictionaries and ensure no None values
            result = []
            for vehicle in vehicles:
                vehicle_dict = dict(vehicle)
                for key in vehicle_dict:
                    if vehicle_dict[key] is None:
                        vehicle_dict[key] = 'N/A'
                result.append(vehicle_dict)
                
            conn.close()
            return result
        else:
            return get_vehicles_by_status(tab, sort_column, sort_direction)
    except Exception as e:
        logging.error(f"Get vehicles error (tab={tab}): {e}")
        return []

def toggle_archive_status(call_number):
    from utils import log_action
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check current archive status
        cursor.execute("SELECT archived FROM vehicles WHERE towbook_call_number = ?", (call_number,))
        result = cursor.fetchone()
        if not result:
            conn.close()
            return False, "Vehicle not found"
        
        # Toggle status
        new_archived = 1 if result['archived'] == 0 else 0
        cursor.execute("""
            UPDATE vehicles 
            SET archived = ?, last_updated = ?
            WHERE towbook_call_number = ?
        """, (new_archived, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), call_number))
        
        conn.commit()
        conn.close()
        
        status_text = "completed" if new_archived else "active"
        log_action("ARCHIVE_TOGGLE", call_number, f"Status toggled to {status_text}")
        return True, f"Vehicle {status_text} successfully"
    except Exception as e:
        logging.error(f"Error toggling archive status: {e}")
        return False, str(e)

def batch_update_status(vehicle_ids, new_status):
    from utils import log_action
    try:
        # Convert underscored status to space format if needed
        if new_status == 'TOP_Generated':
            new_status = 'TOP Generated'
        elif new_status == 'TR52_Ready':
            new_status = 'TR52 Ready'  
        elif new_status == 'TR208_Ready':
            new_status = 'TR208 Ready'
        elif new_status == 'Ready_for_Auction':
            new_status = 'Ready for Auction'
        elif new_status == 'Ready_for_Scrap':
            new_status = 'Ready for Scrap'
            
        conn = get_db_connection()
        cursor = conn.cursor()
        updated_count = 0
        for call_number in vehicle_ids:
            cursor.execute("UPDATE vehicles SET status = ?, last_updated = ? WHERE towbook_call_number = ?",
                           (new_status, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), call_number))
            if cursor.rowcount > 0:
                updated_count += 1
                log_action("BATCH_UPDATE", call_number, f"Status updated to {new_status}")
        conn.commit()
        conn.close()
        return True, updated_count, f"Updated {updated_count} vehicles"
    except Exception as e:
        logging.error(f"Batch update error: {e}")
        return False, 0, str(e)

def get_logs(vehicle_id=None, limit=100):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if vehicle_id:
            cursor.execute("SELECT * FROM logs WHERE vehicle_id = ? ORDER BY timestamp DESC LIMIT ?", (vehicle_id, limit))
        else:
            cursor.execute("SELECT * FROM logs ORDER BY timestamp DESC LIMIT ?", (limit,))
        
        logs = cursor.fetchall()
        conn.close()
        return logs
    except Exception as e:
        logging.error(f"Error getting logs: {e}")
        return []

def create_auction(auction_date, vehicle_ids):
    from utils import log_action, calculate_newspaper_ad_date
    try:
        if not auction_date or not vehicle_ids:
            return False, "Missing required fields"
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(f"SELECT vin FROM vehicles WHERE towbook_call_number IN ({','.join(['?' for _ in vehicle_ids])})", vehicle_ids)
        vin_list = ', '.join([row['vin'] for row in cursor.fetchall() if row['vin']])
        
        # Calculate ad placement date
        auction_date_obj = datetime.strptime(auction_date, '%Y-%m-%d')
        ad_date = calculate_newspaper_ad_date(auction_date_obj)
        
        cursor.execute("INSERT INTO auctions (auction_date, status, vin_list, created_date, advertisement_date) VALUES (?, 'Scheduled', ?, ?, ?)",
                      (auction_date, vin_list, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), ad_date.strftime('%Y-%m-%d')))
        auction_id = cursor.lastrowid
        
        successfully_updated = []
        for vehicle_id in vehicle_ids:
            # Update the vehicle record
            cursor.execute("""
                UPDATE vehicles 
                SET status = 'Ready for Auction', 
                    auction_date = ?,
                    ad_placement_date = ?,
                    decision = 'Auction',
                    decision_date = ?,
                    last_updated = ?
                WHERE towbook_call_number = ?
            """, (auction_date, 
                 ad_date.strftime('%Y-%m-%d'),
                 datetime.now().strftime('%Y-%m-%d'),
                 datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                 vehicle_id))
            
            if cursor.rowcount > 0:
                successfully_updated.append(vehicle_id)
                
                # Create notification for auction ad
                cursor.execute("""
                    INSERT INTO notifications
                    (vehicle_id, notification_type, due_date, status)
                    VALUES (?, ?, ?, ?)
                """, (vehicle_id, 'Auction_Ad', ad_date.strftime('%Y-%m-%d'), 'pending'))
                
                # Add a log entry
                log_action("AUCTION_SCHEDULE", vehicle_id, f"Scheduled for auction on {auction_date}")
        
        conn.commit()
        conn.close()
        
        if not successfully_updated:
            return False, "No eligible vehicles were updated"
            
        return True, f"Scheduled {len(successfully_updated)} vehicles for auction on {auction_date}"
    except Exception as e:
        logging.error(f"Error creating auction: {e}")
        return False, str(e)

def get_pending_notifications():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        today = datetime.now().date().strftime('%Y-%m-%d')
        
        cursor.execute("""
            SELECT n.*, v.jurisdiction, v.make, v.model, v.year, v.color, v.towbook_call_number, v.vin
            FROM notifications n
            JOIN vehicles v ON n.vehicle_id = v.towbook_call_number
            WHERE n.status = 'pending' AND n.due_date <= ?
            ORDER BY n.due_date
        """, (today,))
        
        notifications = [dict(row) for row in cursor.fetchall()]
        
        # Get contact information for each jurisdiction
        for notification in notifications:
            cursor.execute("SELECT * FROM contacts WHERE jurisdiction = ?", (notification['jurisdiction'],))
            contact = cursor.fetchone()
            if contact:
                notification['contact'] = dict(contact)
        
        conn.close()
        return notifications
    except Exception as e:
        logging.error(f"Error getting pending notifications: {e}")
        return []

def mark_notification_sent(notification_id, method, recipient):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE notifications
            SET status = 'sent', sent_date = ?, sent_method = ?, recipient = ?
            WHERE id = ?
        """, (datetime.now().strftime('%Y-%m-%d'), method, recipient, notification_id))
        
        # Get notification details for logging
        cursor.execute("SELECT * FROM notifications WHERE id = ?", (notification_id,))
        notification = cursor.fetchone()
        
        if notification:
            # Update vehicle record based on notification type
            if notification['notification_type'] == 'TOP':
                cursor.execute("UPDATE vehicles SET top_notification_sent = 1 WHERE towbook_call_number = ?",
                              (notification['vehicle_id'],))
            
            elif notification['notification_type'] == 'Auction_Ad':
                cursor.execute("UPDATE vehicles SET auction_ad_sent = 1 WHERE towbook_call_number = ?",
                              (notification['vehicle_id'],))
            
            elif notification['notification_type'] == 'Release_Notice':
                cursor.execute("UPDATE vehicles SET release_notification_sent = 1 WHERE towbook_call_number = ?",
                              (notification['vehicle_id'],))
            
            # Log the action
            from utils import log_action
            log_action("NOTIFICATION_SENT", notification['vehicle_id'],
                      f"{notification['notification_type']} sent to {recipient} via {method}")
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logging.error(f"Error marking notification sent: {e}")
        return False

def get_contact_by_jurisdiction(jurisdiction):
    try:
        conn = get_db_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM contacts WHERE jurisdiction = ?", (jurisdiction,))
        contact = cursor.fetchone()
        
        conn.close()
        return dict(contact) if contact else None
    except Exception as e:
        logging.error(f"Error getting contact: {e}")
        return None

def save_contact(contact_data):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if contact exists
        if 'id' in contact_data and contact_data['id']:
            # Update existing contact
            cursor.execute("SELECT * FROM contacts WHERE id = ?", (contact_data['id'],))
            if not cursor.fetchone():
                conn.close()
                return False, "Contact not found"
                
            set_clause = ', '.join([f"{key} = ?" for key in contact_data.keys() if key != 'id'])
            values = [contact_data[key] for key in contact_data.keys() if key != 'id'] + [contact_data['id']]
            
            cursor.execute(f"UPDATE contacts SET {set_clause} WHERE id = ?", values)
            message = "Contact updated successfully"
        else:
            # Check if jurisdiction exists
            cursor.execute("SELECT id FROM contacts WHERE jurisdiction = ?", (contact_data['jurisdiction'],))
            existing = cursor.fetchone()
            
            if existing:
                # Update existing contact by jurisdiction
                fields = []
                values = []
                for key, value in contact_data.items():
                    if key != 'id' and key != 'jurisdiction':  # Skip primary key and jurisdiction
                        fields.append(f"{key} = ?")
                        values.append(value)
                
                # Add jurisdiction for WHERE clause
                values.append(contact_data['jurisdiction'])
                
                cursor.execute(f"""
                    UPDATE contacts SET {", ".join(fields)}
                    WHERE jurisdiction = ?
                """, values)
                message = "Contact updated successfully"
            else:
                # Create new contact
                if 'jurisdiction' not in contact_data or not contact_data['jurisdiction']:
                    conn.close()
                    return False, "Jurisdiction is required"
                    
                columns = ', '.join([key for key in contact_data.keys() if key != 'id'])
                placeholders = ', '.join(['?' for _ in contact_data.keys() if key != 'id'])
                values = [contact_data[key] for key in contact_data.keys() if key != 'id']
                
                cursor.execute(f"INSERT INTO contacts ({columns}) VALUES ({placeholders})", values)
                message = "Contact added successfully"
        
        conn.commit()
        conn.close()
        return True, message
    except Exception as e:
        logging.error(f"Error saving contact: {e}")
        return False, str(e)

def get_contacts():
    try:
        conn = get_db_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM contacts ORDER BY jurisdiction")
        contacts = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        return contacts
    except Exception as e:
        logging.error(f"Error getting contacts: {e}")
        return []