import sqlite3 # Added: for SQLite database operations
import os      # Added: for path operations
import logging # Added logging import
from flask import g, current_app # Ensure current_app is imported
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
            return datetime.strptime(date_str, '%m/%d/%Y').date() # Added alternative format
        except ValueError:
            logging.warning(f"Invalid date format encountered: {date_str}") # Log warning
            return None

# Make sure we have a consistent database path
def get_database_path():
    # Get the directory where this script is located
    base_dir = os.path.dirname(os.path.abspath(__file__))
    # Define the database file path
    db_path = os.path.join(base_dir, 'vehicles.db')
    return db_path

DATABASE = get_database_path() # Use the function directly to ensure consistency

def get_db_connection(db_path=None):
    db_path = db_path or DATABASE  # Default to our defined DATABASE path
    
    # Log the path being used for debugging
    try:
        logging.debug(f"Connecting to database: {os.path.abspath(db_path)}")
    except:
        pass

    # Check if we have an existing connection in the Flask g object
    db = getattr(g, '_database', None)
    
    # Create a new connection if we don't have one or if the path has changed
    if db is None:
        try:
            # Ensure the directory exists
            db_dir = os.path.dirname(db_path)
            if db_dir and not os.path.exists(db_dir):
                os.makedirs(db_dir)
                
            # Connect to the database
            db = sqlite3.connect(db_path)
            db.row_factory = sqlite3.Row
            
            # Store in Flask g object if available
            try:
                g._database = db
            except:
                pass  # Not in a Flask context
                
        except Exception as e:
            logging.error(f"Database connection error: {e}", exc_info=True)
            raise
    
    return db

def transaction():
    """Context manager for database transactions"""
    class Transaction:
        def __enter__(self):
            self.conn = get_db_connection()
            self.conn.execute("BEGIN")
            return self.conn.cursor() # Return cursor for use within 'with' block

        def __exit__(self, exc_type, exc_val, exc_tb):
            if exc_type is None:
                self.conn.commit()
            else:
                self.conn.rollback()
            # The connection itself is managed by Flask's 'g' object, so usually not closed here
            # unless it's a non-Flask context. For simplicity, relying on 'g'.

    return Transaction()

def init_db(db_path=None):
    db_path = db_path or os.environ.get('DATABASE_URL', get_database_path())
    logger = current_app.logger if hasattr(current_app, 'logger') else logging.getLogger(__name__)
    logger.info(f"Initializing database at {db_path}...")
    
    conn = get_db_connection(db_path) # Ensures connection is correctly established or reused via 'g'
    try:
        with conn: # Use connection as a context manager for commit/rollback
            # Vehicles table
            conn.execute("""
            CREATE TABLE IF NOT EXISTS vehicles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                towbook_call_number TEXT UNIQUE,
                complaint_number TEXT UNIQUE,
                tow_date TEXT,
                vehicle_year TEXT,
                make TEXT,
                model TEXT,
                vin TEXT,
                license_plate TEXT,
                license_state TEXT,
                color TEXT,
                location_from TEXT,
                requested_by TEXT,
                driver TEXT,
                reason_for_tow TEXT,
                status TEXT DEFAULT 'New', -- e.g., New, TOP Generated, TR52 Ready, Released, Auctioned
                owner_name TEXT,
                owner_address TEXT,
                owner_phone TEXT,
                owner_email TEXT,
                owner_known TEXT DEFAULT 'No', -- Yes, No
                lienholder_name TEXT,
                lienholder_address TEXT,
                lienholder_phone TEXT,
                lienholder_email TEXT,
                last_updated TEXT, -- Timestamp of the last status update or significant change
                release_date TEXT,
                released_to TEXT,
                release_fee REAL,
                storage_start_date TEXT,
                storage_end_date TEXT,
                daily_storage_rate REAL,
                total_storage_fees REAL,
                auction_date TEXT,
                auction_house TEXT,
                sold_price REAL,
                scrap_date TEXT,
                scrap_yard TEXT,
                scrap_value REAL,
                notes TEXT,
                archived INTEGER DEFAULT 0, -- 0 for not archived, 1 for archived
                photos TEXT, -- JSON string of photo paths or comma-separated
                documents TEXT, -- JSON string of document info {name, path, type}
                certified_mail_number_owner TEXT,
                certified_mail_number_lienholder TEXT,
                newspaper_ad_date TEXT,
                tr208_eligible INTEGER DEFAULT 0, -- 0 for No, 1 for Yes
                tr208_filed_date TEXT,
                tr208_approved_date TEXT,
                tr208_status TEXT, -- e.g., Pending, Approved, Denied
                jurisdiction TEXT -- e.g., City, County, State Police post
            );
            """)
            logger.info("Table 'vehicles' checked/created.")

            # Contacts table
            conn.execute("""
            CREATE TABLE IF NOT EXISTS contacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                jurisdiction TEXT NOT NULL UNIQUE, -- e.g., "City Police", "County Sheriff", "State Police Post 5"
                contact_name TEXT,
                phone_number TEXT,
                email_address TEXT,
                fax_number TEXT,
                address TEXT,
                notes TEXT
            );
            """)
            logger.info("Table 'contacts' checked/created.")

            # System Logs table
            conn.execute("""
            CREATE TABLE IF NOT EXISTS system_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                level TEXT NOT NULL, -- e.g., INFO, WARNING, ERROR
                user_id TEXT, -- User performing the action, if applicable
                action TEXT, -- e.g., "Vehicle Added", "Status Update", "Login Attempt"
                vehicle_call_number TEXT, -- Link to vehicle if action is vehicle-related
                details TEXT,
                ip_address TEXT
            );
            """)
            logger.info("Table 'system_logs' checked/created.")

            # Notifications table
            conn.execute("""
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vehicle_id INTEGER,
                towbook_call_number TEXT, -- Denormalized for easier access
                message TEXT NOT NULL,
                type TEXT NOT NULL, -- e.g., 'Overdue TOP', 'Auction Reminder', 'TR208 Deadline'
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                due_date TEXT, -- Date when the action related to notification is due
                status TEXT DEFAULT 'Pending', -- e.g., Pending, Sent, Dismissed
                recipient_type TEXT, -- e.g., 'Owner', 'Lienholder', 'Internal'
                method TEXT, -- How it was sent, e.g., 'Email', 'SMS', 'Fax', 'Certified Mail'
                sent_at DATETIME,
                sent_to TEXT, -- Actual recipient address/number
                FOREIGN KEY (vehicle_id) REFERENCES vehicles(id)
            );
            """)
            logger.info("Table 'notifications' checked/created.")

            # Auctions table
            conn.execute("""
            CREATE TABLE IF NOT EXISTS auctions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                auction_date TEXT NOT NULL,
                auction_house TEXT,
                notes TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            """)
            logger.info("Table 'auctions' checked/created.")

            # Auction Vehicles (junction table)
            conn.execute("""
            CREATE TABLE IF NOT EXISTS auction_vehicles (
                auction_id INTEGER NOT NULL,
                vehicle_id INTEGER NOT NULL,
                lot_number TEXT,
                sold_price REAL,
                status TEXT DEFAULT 'Scheduled', -- e.g., Scheduled, Sold, Not Sold
                PRIMARY KEY (auction_id, vehicle_id),
                FOREIGN KEY (auction_id) REFERENCES auctions(id),
                FOREIGN KEY (vehicle_id) REFERENCES vehicles(id)
            );
            """)
            logger.info("Table 'auction_vehicles' checked/created.")
            
            # Documents table (if not storing as JSON in vehicles.documents)
            # This provides a more structured way to handle documents
            conn.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vehicle_id INTEGER,
                towbook_call_number TEXT, -- Denormalized for easier access
                document_name TEXT NOT NULL,
                document_type TEXT, -- e.g., 'TOP', 'TR52', 'Photo', 'Owner Letter'
                file_path TEXT NOT NULL,
                uploaded_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                uploaded_by TEXT, -- User ID or 'System'
                FOREIGN KEY (vehicle_id) REFERENCES vehicles(id)
            );
            """)
            logger.info("Table 'documents' checked/created.")

            # Police Log table (for TR52, TR208 submissions etc.)
            conn.execute("""
            CREATE TABLE IF NOT EXISTS police_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vehicle_id INTEGER NOT NULL,
                towbook_call_number TEXT,
                form_type TEXT NOT NULL, -- e.g., TR52, TR208
                submission_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                recipient_jurisdiction TEXT,
                method TEXT, -- e.g., Email, Fax, In-Person
                confirmation_details TEXT, -- e.g., Email ID, Fax confirmation, Officer badge
                notes TEXT,
                logged_by TEXT, -- User ID
                FOREIGN KEY (vehicle_id) REFERENCES vehicles(id)
            );
            """)
            logger.info("Table 'police_log' checked/created.")


    except sqlite3.Error as e:
        logger.error(f"Database initialization error: {e}", exc_info=True)
    # finally:
    #     if conn and not hasattr(g, '_database'): # Only close if not managed by g
    #         conn.close()

def get_vehicle_by_call_number(call_number):
    conn = get_db_connection() 
    # No close here, connection managed by g or calling context
    vehicle = conn.execute('SELECT * FROM vehicles WHERE towbook_call_number = ?', (call_number,)).fetchone()
    return dict(vehicle) if vehicle else None

def get_vehicles_by_status(status_type, sort_column=None, sort_direction=None, include_archived=False):
    from utils import get_status_filter # Local import to avoid circular dependency issues
    logger = current_app.logger if hasattr(current_app, 'logger') else logging.getLogger(__name__)
    try:
        conn = get_db_connection()
        base_query = "SELECT * FROM vehicles"
        conditions = []
        params = []

        status_conditions, status_params = get_status_filter(status_type)
        if status_conditions:
            conditions.append(f"({status_conditions})")
            params.extend(status_params)

        if not include_archived:
            conditions.append("archived = 0")
        
        if conditions:
            base_query += " WHERE " + " AND ".join(conditions)
        
        if sort_column:
            # Basic validation for sort_column to prevent SQL injection if it's too dynamic
            # For now, assume it's from a controlled set of inputs
            direction = 'DESC' if sort_direction and sort_direction.lower() == 'desc' else 'ASC'
            base_query += f" ORDER BY {sort_column} {direction}"
        else:
            base_query += " ORDER BY last_updated DESC" # Default sort

        # logger.debug(f"Executing query: {base_query} with params: {params}")
        vehicles = conn.execute(base_query, tuple(params)).fetchall()
        return [dict(row) for row in vehicles]
    except Exception as e:
        logger.error(f"Error in get_vehicles_by_status ({status_type}): {e}", exc_info=True)
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
    from utils import log_action, generate_next_complaint_number # Ensure generate_next_complaint_number is correct
    logger = current_app.logger if hasattr(current_app, 'logger') else logging.getLogger(__name__)
    try:
        conn = get_db_connection()
        
        # Ensure essential fields are present or have defaults
        data.setdefault('status', 'New')
        data.setdefault('tow_date', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        data.setdefault('last_updated', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        data.setdefault('owner_known', 'No')
        data.setdefault('archived', 0)
        data.setdefault('tr208_eligible', 0)

        # Generate complaint number if not provided
        if 'complaint_number' not in data or not data['complaint_number']:
            data['complaint_number'] = generate_next_complaint_number(conn) # Pass conn if needed by the function

        # Define columns based on your table schema to avoid inserting extra keys from data
        # This also helps in maintaining the correct order if not using named placeholders
        columns = [
            'towbook_call_number', 'complaint_number', 'tow_date', 'vehicle_year', 'make', 
            'model', 'vin', 'license_plate', 'license_state', 'color', 'location_from', 
            'requested_by', 'driver', 'reason_for_tow', 'status', 'owner_name', 
            'owner_address', 'owner_phone', 'owner_email', 'owner_known', 'lienholder_name', 
            'lienholder_address', 'lienholder_phone', 'lienholder_email', 'last_updated', 
            'release_date', 'released_to', 'release_fee', 'storage_start_date', 
            'storage_end_date', 'daily_storage_rate', 'total_storage_fees', 'auction_date', 
            'auction_house', 'sold_price', 'scrap_date', 'scrap_yard', 'scrap_value', 
            'notes', 'archived', 'photos', 'documents', 'certified_mail_number_owner',
            'certified_mail_number_lienholder', 'newspaper_ad_date', 'tr208_eligible',
            'tr208_filed_date', 'tr208_approved_date', 'tr208_status', 'jurisdiction'
        ]
        
        # Filter data to include only known columns and prepare for insertion
        insert_data = {col: data.get(col) for col in columns}

        query = f"""
            INSERT INTO vehicles ({', '.join(insert_data.keys())})
            VALUES ({', '.join(['?'] * len(insert_data))})
        """
        
        with conn:
            cursor = conn.cursor()
            cursor.execute(query, tuple(insert_data.values()))
            vehicle_id = cursor.lastrowid
        
        logger.info(f"Vehicle inserted with ID: {vehicle_id}, Call Number: {data.get('towbook_call_number')}")
        # log_action('Vehicle Added', data.get('towbook_call_number'), 'System', f"Vehicle {data.get('make')} {data.get('model')} added.") # User from context
        return vehicle_id

    except sqlite3.IntegrityError as e:
        logger.error(f"Integrity error inserting vehicle (Call#: {data.get('towbook_call_number')}, Complaint#: {data.get('complaint_number')}): {e}", exc_info=True)
        raise # Re-raise to be handled by the caller, perhaps with a user-friendly message
    except Exception as e:
        logger.error(f"Error inserting vehicle (Call#: {data.get('towbook_call_number')}): {e}", exc_info=True)
        raise

def get_vehicles(tab, sort_column=None, sort_direction='asc'):
    """
    Enhanced version of get_vehicles with improved error handling and status mapping.
    'tab' corresponds to sidebar filters.
    """
    from utils import get_status_filter # Local import
    logger = current_app.logger if hasattr(current_app, 'logger') else logging.getLogger(__name__)
    try:
        conn = get_db_connection()
        
        # Determine status conditions and parameters from the tab
        status_conditions, status_params = get_status_filter(tab)
        
        query = "SELECT * FROM vehicles"
        params = list(status_params) # Convert tuple to list for potential extension

        conditions = []
        if status_conditions:
            conditions.append(f"({status_conditions})")
        
        # Always exclude archived unless 'archived' or 'all_including_archived' tab is specified
        if tab != 'archived' and tab != 'all_including_archived': # Assuming you might add such tabs
             conditions.append("archived = 0")
        elif tab == 'archived':
            conditions.append("archived = 1")

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        # Sorting
        valid_sort_columns = [
            'towbook_call_number', 'complaint_number', 'tow_date', 'make', 'model', 'vin', 
            'license_plate', 'status', 'last_updated', 'release_date', 'auction_date', 'jurisdiction'
        ] # Add more as needed
        
        if sort_column and sort_column in valid_sort_columns:
            direction = 'DESC' if sort_direction and sort_direction.lower() == 'desc' else 'ASC'
            query += f" ORDER BY {sort_column} {direction}"
        else:
            # Default sort order, e.g., by last_updated or tow_date
            query += " ORDER BY last_updated DESC, tow_date DESC"
            
        # logger.debug(f"Executing get_vehicles query: {query} with params: {params}")
        vehicle_rows = conn.execute(query, tuple(params)).fetchall()
        return [dict(row) for row in vehicle_rows]
        
    except Exception as e:
        logger.error(f"Error in get_vehicles (tab: {tab}): {e}", exc_info=True)
        return []

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

def get_pending_notifications():
    logger = current_app.logger if hasattr(current_app, 'logger') else logging.getLogger(__name__)
    try:
        conn = get_db_connection()
        # Fetch notifications that are 'Pending' and optionally order them by due_date or created_at
        query = '''
            SELECT n.*, v.make, v.model, v.plate as license_plate, v.vin, v.status as vehicle_status 
            FROM notifications n
            LEFT JOIN vehicles v ON n.vehicle_id = v.towbook_call_number 
            WHERE n.status = 'Pending'
            ORDER BY n.due_date ASC, n.created_at ASC
        '''
        notifications = conn.execute(query).fetchall()
        return [dict(row) for row in notifications]
    except Exception as e:
        logger.error(f"Error fetching pending notifications: {e}", exc_info=True)
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
                    
                columns = ', '.join([k for k in contact_data.keys() if k != 'id'])
                placeholders = ', '.join(['?' for k in contact_data.keys() if k != 'id'])
                values = [contact_data[k] for k in contact_data.keys() if k != 'id']
                
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

def get_contact_by_id(contact_id):
    conn = get_db_connection()
    contact = conn.execute("SELECT * FROM contacts WHERE id = ?", (contact_id,)).fetchone()
    # conn.close() # Connection managed by g
    return dict(contact) if contact else None

def add_contact_explicit(data):
    conn = get_db_connection()
    # cursor = conn.cursor() # Not needed if using conn.execute directly with context manager
    logger = current_app.logger if hasattr(current_app, 'logger') else logging.getLogger(__name__)
    try:
        # Ensure required fields like jurisdiction are present
        if not data.get('jurisdiction'):
            raise ValueError("Jurisdiction is a required field for contacts.")

        query = """
            INSERT INTO contacts (jurisdiction, contact_name, phone_number, email_address, fax_number, address, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            data.get('jurisdiction'),
            data.get('contact_name'),
            data.get('phone_number'),
            data.get('email_address'),
            data.get('fax_number'),
            data.get('address'),
            data.get('notes')
        )
        with conn: # transactionality
            cursor = conn.execute(query, params)
            new_id = cursor.lastrowid
        logger.info(f"Contact added explicitly with ID: {new_id} for jurisdiction: {data.get('jurisdiction')}")
        return new_id
    except sqlite3.IntegrityError as e:        
        logger.error(f"Integrity error adding contact for jurisdiction {data.get('jurisdiction')}: {e}", exc_info=True)
        raise ValueError(f"A contact for jurisdiction '{data.get('jurisdiction')}' already exists.") # User-friendly
    except Exception as e:
        logger.error(f"Error adding contact explicitly: {e}", exc_info=True)
        raise # Re-raise for caller to handle

def update_contact_explicit(contact_id, data):
    conn = get_db_connection()
    logger = current_app.logger if hasattr(current_app, 'logger') else logging.getLogger(__name__)
    try:
        # Construct SET clause dynamically for fields present in data
        set_clauses = []
        params = []
        allowed_fields = ['jurisdiction', 'contact_name', 'phone_number', 'email_address', 'fax_number', 'address', 'notes']
        for field in allowed_fields:
            if field in data:
                set_clauses.append(f"{field} = ?")
                params.append(data[field])
        
        if not set_clauses:
            # raise ValueError("No data provided for update.") # Or just return without error
            return True # No changes to make

        params.append(contact_id)
        query = f"UPDATE contacts SET {', '.join(set_clauses)} WHERE id = ?"
        
        with conn:
            cursor = conn.execute(query, tuple(params))
        
        if cursor.rowcount == 0:
            logger.warning(f"Attempted to update contact ID {contact_id}, but it was not found.")
            raise ValueError(f"Contact with ID {contact_id} not found.")
            
        logger.info(f"Contact ID {contact_id} updated successfully.")
        return True # Indicate success
            
    except sqlite3.IntegrityError as e:        
        logger.error(f"Integrity error updating contact ID {contact_id} (e.g. duplicate jurisdiction): {e}", exc_info=True)
        # Assuming jurisdiction is unique, this error could occur if trying to change to an existing one
        raise ValueError(f"Failed to update contact: A contact with the provided jurisdiction may already exist.")
    except Exception as e:
        logger.error(f"Error updating contact ID {contact_id}: {e}", exc_info=True)
        raise

def delete_contact_explicit(contact_id):
    conn = get_db_connection()
    logger = current_app.logger if hasattr(current_app, 'logger') else logging.getLogger(__name__)
    try:
        with conn:
            cursor = conn.execute("DELETE FROM contacts WHERE id = ?", (contact_id,))
        
        if cursor.rowcount == 0:
            logger.warning(f"Attempted to delete contact ID {contact_id}, but it was not found.")
            # Depending on desired behavior, either raise an error or return False
            return False # Or raise ValueError("Contact not found")
            
        logger.info(f"Contact ID {contact_id} deleted successfully.")
        return True # Indicate success
    except Exception as e:
        logger.error(f"Error deleting contact ID {contact_id}: {e}", exc_info=True)
        raise

def log_police_event(vehicle_id, form_type, recipient_jurisdiction, method, logged_by, notes='', confirmation_details=''):
    conn = get_db_connection() 
    logger = current_app.logger if hasattr(current_app, 'logger') else logging.getLogger(__name__)
    try:
        # Get towbook_call_number for denormalization
        vehicle_info = conn.execute("SELECT towbook_call_number FROM vehicles WHERE id = ?", (vehicle_id,)).fetchone()
        towbook_call_number = vehicle_info['towbook_call_number'] if vehicle_info else None

        query = """
            INSERT INTO police_log (vehicle_id, towbook_call_number, form_type, recipient_jurisdiction, method, logged_by, notes, confirmation_details, submission_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            vehicle_id, towbook_call_number, form_type, recipient_jurisdiction, method, 
            logged_by, notes, confirmation_details, datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        )
        with conn:
            conn.execute(query, params)
        logger.info(f"Police event logged for vehicle ID {vehicle_id}, form {form_type} by {logged_by}.")
    except sqlite3.Error as e:
         logger.error(f"Error logging police event for vehicle ID {vehicle_id}: {e}", exc_info=True)
         # Decide if to raise or handle, for now, just log

def add_document(call_number, document_name, document_type, file_path, uploaded_by='System'): 
    conn = get_db_connection()
    logger = current_app.logger if hasattr(current_app, 'logger') else logging.getLogger(__name__)
    try:
        # Get vehicle_id from call_number
        vehicle_info = conn.execute("SELECT id FROM vehicles WHERE towbook_call_number = ?", (call_number,)).fetchone()
        if not vehicle_info:
            logger.error(f"Cannot add document. Vehicle with call_number {call_number} not found.")
            return None # Or raise error
        vehicle_id = vehicle_info['id']

        query = """
            INSERT INTO documents (vehicle_id, towbook_call_number, document_name, document_type, file_path, uploaded_by, uploaded_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            vehicle_id, call_number, document_name, document_type, 
            file_path, uploaded_by, datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        )
        with conn:
            cursor = conn.execute(query, params)
            doc_id = cursor.lastrowid
        logger.info(f"Document '{document_name}' added for vehicle call_number {call_number} by {uploaded_by}. Doc ID: {doc_id}")
        return doc_id
    except sqlite3.Error as e:
        logger.error(f"Error adding document for vehicle call_number {call_number}: {e}", exc_info=True)
        # Decide if to raise or handle
        return None