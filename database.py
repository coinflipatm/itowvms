#database.py

import sqlite3
from datetime import datetime, timedelta
import logging
import contextlib
import os
import json

def get_db_connection():
    """Get a connection to the SQLite database with Row factory"""
    conn = sqlite3.connect('vehicles.db')
    conn.row_factory = sqlite3.Row
    return conn

@contextlib.contextmanager
def transaction():
    """Context manager for database transactions that handles commit/rollback"""
    conn = get_db_connection()
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_db():
    """Initialize the database schema if it doesn't exist"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Vehicle table schema - updated with new status fields
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
    
    # Logs table for activity tracking
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action_type TEXT,
            vehicle_id TEXT,
            details TEXT,
            timestamp TEXT
        )
    ''')
    
    # Auction table for tracking auction events
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
    
    conn.commit()
    conn.close()
    
    # Create a directory for generated PDF files if it doesn't exist
    os.makedirs('static/generated_pdfs', exist_ok=True)
    logging.info("Database and directories initialized")

def insert_vehicle(data):
    """Insert a new vehicle record or update existing one"""
    # Import function here to avoid circular imports
    from utils import generate_invoice_number, log_action
    
    try:
        with transaction() as conn:
            cursor = conn.cursor()
            
            # Check if we already have an invoice number
            if not data.get('invoice_number'):
                invoice_number, sequence, year = generate_invoice_number()
                data['invoice_number'] = invoice_number
                data['invoice_sequence'] = sequence
                data['invoice_year'] = year
            
            # Determine if owner is known
            owner_known = 'Yes' if data.get('vin') or data.get('plate') else 'No'
            
            # Check if this is an update to an existing vehicle
            cursor.execute("SELECT towbook_call_number FROM vehicles WHERE towbook_call_number = ?", 
                        (data['towbook_call_number'],))
            existing_vehicle = cursor.fetchone()
            
            if existing_vehicle:
                # Build the update statement dynamically
                update_fields = []
                update_values = []
                
                for field, value in data.items():
                    if field != 'towbook_call_number':
                        update_fields.append(f"{field} = ?")
                        update_values.append(value)
                
                update_fields.append("last_updated = ?")
                update_values.append(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                update_values.append(data['towbook_call_number'])
                
                cursor.execute(f'''
                    UPDATE vehicles SET {', '.join(update_fields)}
                    WHERE towbook_call_number = ?
                ''', update_values)
                
                log_action("UPDATE", data['towbook_call_number'], f"Updated vehicle: {data.get('make', '')} {data.get('model', '')}")
                return True, "Vehicle updated successfully"
            else:
                # Insert as a new vehicle
                fields = ['towbook_call_number', 'invoice_number', 'vin', 'make', 'model', 'year', 'color', 'tow_date', 
                        'tow_time', 'location', 'requestor', 'status', 'last_updated', 'owner_known', 
                        'invoice_sequence', 'invoice_year', 'complaint_number', 'plate', 'state']
                
                values = [
                    data.get('towbook_call_number', ''), 
                    data.get('invoice_number', ''), 
                    data.get('vin', ''),
                    data.get('make', ''), 
                    data.get('model', ''),
                    data.get('year', ''),
                    data.get('color', ''),
                    data.get('tow_date', ''),
                    data.get('tow_time', ''),
                    data.get('location', ''),
                    data.get('requestor', 'PROPERTY OWNER'),
                    data.get('status', 'New'),
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    owner_known,
                    data.get('invoice_sequence', ''),
                    data.get('invoice_year', ''),
                    data.get('complaint_number', ''),
                    data.get('plate', ''),
                    data.get('state', '')
                ]
                
                # If tow date is provided, calculate next step date (20 days after tow)
                if data.get('tow_date'):
                    try:
                        tow_date = datetime.strptime(data['tow_date'], '%Y-%m-%d')
                        tr52_date = tow_date + timedelta(days=20)
                        fields.append('tr52_available_date')
                        values.append(tr52_date.strftime('%Y-%m-%d'))
                    except Exception as e:
                        logging.warning(f"Error calculating TR52 date: {e}")
                
                placeholders = ','.join(['?' for _ in fields])
                cursor.execute(f'''
                    INSERT INTO vehicles ({','.join(fields)})
                    VALUES ({placeholders})
                ''', values)
                
                log_action("INSERT", data['towbook_call_number'], f"Added vehicle: {data.get('make', '')} {data.get('model', '')}")
                return True, "Vehicle added successfully"
                
    except Exception as e:
        logging.error(f"Error in insert_vehicle: {e}")
        return False, str(e)

def update_vehicle_status(vehicle_id, new_status, update_fields=None):
    """Update a vehicle's status with enhanced status tracking"""
    # Import function here to avoid circular imports
    from utils import log_action
    
    # Define valid statuses and transitions
    valid_statuses = [
        'New',                    # Just added to system
        'TOP Generated',          # TOP form has been generated 
        'Ready for Disposition',  # 20 days after TOP Generated
        'Paperwork Received',     # TR-52 acquired
        'Ready for Auction',      # Decision to auction + schedule
        'Ready for Scrap',        # Decision to scrap
        'In Auction',             # Scheduled for specific auction
        'Auctioned',              # Vehicle has been auctioned
        'Scrapped',               # Vehicle has been scrapped
        'Released',               # Vehicle released to owner or other party
    ]
    
    # Map frontend status to backend status
    status_map = {
        'TOP_Sent': 'TOP Generated',
        'Ready': 'Ready for Disposition',
        'Paperwork': 'Paperwork Received',
        'Action': 'Ready for Action'
    }
    
    # Convert frontend status if needed
    if new_status in status_map:
        new_status = status_map[new_status]
    
    # Validate status
    if new_status not in valid_statuses:
        logging.warning(f"Invalid status: {new_status}. Using 'New' instead.")
        new_status = 'New'
    
    try:
        with transaction() as conn:
            cursor = conn.cursor()
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Get current status before updating
            cursor.execute("SELECT status FROM vehicles WHERE towbook_call_number = ?", (vehicle_id,))
            result = cursor.fetchone()
            if not result:
                return False
                
            current_status = result['status']
            
            # Add status change to update fields
            if not update_fields:
                update_fields = {}
            
            # For specific statuses, set additional fields
            if new_status == 'TOP Generated' and 'top_form_sent_date' not in update_fields:
                update_fields['top_form_sent_date'] = datetime.now().strftime('%Y-%m-%d')
                
                # Calculate tr52_available_date (20 days after TOP generation)
                try:
                    tr52_date = datetime.now() + timedelta(days=20)
                    update_fields['tr52_available_date'] = tr52_date.strftime('%Y-%m-%d')
                except Exception as e:
                    logging.warning(f"Error calculating TR52 date: {e}")
            
            if new_status == 'Paperwork Received' and 'paperwork_received_date' not in update_fields:
                update_fields['paperwork_received_date'] = datetime.now().strftime('%Y-%m-%d')
            
            # For decision statuses, calculate dates
            if new_status == 'Ready for Auction':
                # Calculate next auction date (next Monday after paper deadline)
                try:
                    today = datetime.now().date()
                    days_to_monday = (7 - today.weekday()) % 7  # Days until next Monday
                    if days_to_monday < 3:  # If Monday is less than 3 days away, target the following Monday
                        days_to_monday += 7
                    next_monday = today + timedelta(days=days_to_monday)
                    
                    # Ensure we have at least 10 days for the newspaper ad
                    if (next_monday - today).days < 10:
                        next_monday += timedelta(days=7)
                        
                    update_fields['estimated_date'] = next_monday.strftime('%Y-%m-%d')
                    update_fields['decision'] = 'Auction'
                    update_fields['decision_date'] = datetime.now().strftime('%Y-%m-%d')
                except Exception as e:
                    logging.warning(f"Error calculating auction date: {e}")
                    
            if new_status == 'Ready for Scrap':
                # 7 days after paperwork received
                try:
                    cursor.execute("SELECT paperwork_received_date FROM vehicles WHERE towbook_call_number = ?", (vehicle_id,))
                    result = cursor.fetchone()
                    if result and result['paperwork_received_date']:
                        paperwork_date = datetime.strptime(result['paperwork_received_date'], '%Y-%m-%d')
                        scrap_date = paperwork_date + timedelta(days=7)
                        update_fields['estimated_date'] = scrap_date.strftime('%Y-%m-%d')
                    
                    update_fields['decision'] = 'Scrap'
                    update_fields['decision_date'] = datetime.now().strftime('%Y-%m-%d')
                except Exception as e:
                    logging.warning(f"Error calculating scrap date: {e}")
            
            # For release-type statuses, ensure we have a proper release reason if not specified
            if new_status in ['Auctioned', 'Scrapped', 'Released'] and 'release_reason' not in update_fields:
                if new_status == 'Released':
                    update_fields['release_reason'] = 'Released to Owner'
                elif new_status == 'Auctioned':
                    update_fields['release_reason'] = 'Auctioned'
                elif new_status == 'Scrapped':
                    update_fields['release_reason'] = 'Scrapped'
                
                # Add release date and time if not present
                if 'release_date' not in update_fields:
                    update_fields['release_date'] = datetime.now().strftime('%Y-%m-%d')
                if 'release_time' not in update_fields:
                    update_fields['release_time'] = datetime.now().strftime('%H:%M')
                    
                # Mark as archived to move to completed tab
                update_fields['archived'] = 1
            
            # Build the UPDATE statement
            set_clause = ', '.join([f"{field} = ?" for field in update_fields.keys()])
            if set_clause:
                set_clause += ', '
            
            values = list(update_fields.values()) + [new_status, current_time, vehicle_id]
            
            cursor.execute(f'''
                UPDATE vehicles 
                SET {set_clause}status = ?, last_updated = ?
                WHERE towbook_call_number = ?
            ''', values)
            
            # Log the action
            log_action("STATUS_CHANGE", vehicle_id, f"Changed status from {current_status} to {new_status}")
            
            return True
            
    except Exception as e:
        logging.error(f"Error updating vehicle status: {e}")
        return False

def get_vehicles_by_status(status_filter, sort_column=None, sort_direction='asc'):
    """Get vehicles filtered by status with optional sorting"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Map status values coming from frontend to actual database values
        if isinstance(status_filter, list) and status_filter:
            status_map = {
                'TOP_Sent': 'TOP Generated',
                'Ready': 'Ready for Disposition',
                'Paperwork': 'Paperwork Received',
                'Action': ['Ready for Auction', 'Ready for Scrap']
            }
            
            # Replace any mapped values
            mapped_filter = []
            for status in status_filter:
                if status in status_map:
                    if isinstance(status_map[status], list):
                        mapped_filter.extend(status_map[status])
                    else:
                        mapped_filter.append(status_map[status])
                else:
                    mapped_filter.append(status)
                    
            status_filter = mapped_filter
        
        base_query = "SELECT * FROM vehicles"
        params = []
        
        # Apply status filter
        if status_filter and len(status_filter) > 0:
            placeholders = ', '.join(['?' for _ in status_filter])
            base_query += f" WHERE status IN ({placeholders})"
            params.extend(status_filter)
        
        # Apply sorting if specified
        if sort_column and sort_column in ['towbook_call_number', 'complaint_number', 'tow_date', 
                                        'jurisdiction', 'vin', 'make', 'model', 'status', 
                                        'release_reason', 'release_date']:
            # Sanitize sort_direction to prevent SQL injection
            sort_direction = 'asc' if sort_direction.lower() != 'desc' else 'desc'
            base_query += f" ORDER BY {sort_column} {sort_direction}"
        else:
            # Default sort by most recent update
            base_query += " ORDER BY last_updated DESC"
        
        cursor.execute(base_query, params)
        vehicles = cursor.fetchall()
        conn.close()
        return vehicles
    except Exception as e:
        logging.error(f"Error in get_vehicles_by_status: {e}")
        conn.close() if 'conn' in locals() else None
        return []

def update_vehicle(old_call_number, data):
    """Update a vehicle with potential towbook_call_number change"""
    from utils import log_action
    
    try:
        with transaction() as conn:
            cursor = conn.cursor()
            
            # Check if the towbook_call_number is being changed
            new_call_number = data.get('towbook_call_number', old_call_number)
            
            if new_call_number != old_call_number:
                # Check if the new call number already exists
                cursor.execute("SELECT COUNT(*) FROM vehicles WHERE towbook_call_number = ?", (new_call_number,))
                exists = cursor.fetchone()[0] > 0
                
                if exists:
                    return False, "The new call number already exists in the database"
                
                # Since we're changing the primary key, we need to:
                # 1. Create a new record with the new call number
                # 2. Copy all data from the old record
                # 3. Delete the old record
                
                # Get all data from the old record
                cursor.execute("SELECT * FROM vehicles WHERE towbook_call_number = ?", (old_call_number,))
                old_vehicle = cursor.fetchone()
                
                if not old_vehicle:
                    return False, "Original vehicle not found"
                
                # Prepare data for the new record
                new_vehicle = dict(old_vehicle)
                new_vehicle['towbook_call_number'] = new_call_number
                
                # Update with new data
                for key, value in data.items():
                    new_vehicle[key] = value
                
                # Set last_updated
                new_vehicle['last_updated'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
                # Insert the new record
                fields = list(new_vehicle.keys())
                values = list(new_vehicle.values())
                placeholders = ','.join(['?' for _ in fields])
                
                cursor.execute(f'''
                    INSERT INTO vehicles ({','.join(fields)})
                    VALUES ({placeholders})
                ''', values)
                
                # Delete the old record
                cursor.execute("DELETE FROM vehicles WHERE towbook_call_number = ?", (old_call_number,))
                
                # Update logs to point to the new call number
                cursor.execute('''
                    UPDATE logs SET vehicle_id = ?
                    WHERE vehicle_id = ?
                ''', (new_call_number, old_call_number))
                
                log_action("UPDATE", new_call_number, f"Changed call number from {old_call_number} to {new_call_number}")
                
                return True, "Vehicle updated successfully with new call number"
            
            else:
                # Standard update without changing the primary key
                # Build update statement
                update_fields = []
                update_values = []
                
                for key, value in data.items():
                    if key != 'towbook_call_number':
                        update_fields.append(f"{key} = ?")
                        update_values.append(value)
                
                update_fields.append("last_updated = ?")
                update_values.append(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                update_values.append(old_call_number)
                
                cursor.execute(f'''
                    UPDATE vehicles 
                    SET {', '.join(update_fields)}
                    WHERE towbook_call_number = ?
                ''', update_values)
                
                log_action("UPDATE", old_call_number, "Updated vehicle information")
                
                return True, "Vehicle updated successfully"
                
    except Exception as e:
        logging.error(f"Error updating vehicle: {e}")
        return False, f"Error updating vehicle: {str(e)}"

def toggle_archive_status(call_number):
    """Toggle a vehicle between active and completed (archived) status"""
    from utils import log_action
    
    try:
        with transaction() as conn:
            cursor = conn.cursor()
            
            # Get current archived status
            cursor.execute("SELECT archived FROM vehicles WHERE towbook_call_number = ?", (call_number,))
            result = cursor.fetchone()
            
            if not result:
                return False, "Vehicle not found"
            
            current_archived = result[0]
            new_archived = 1 if current_archived == 0 else 0
            
            # Update the archived status
            cursor.execute('''
                UPDATE vehicles
                SET archived = ?, last_updated = ?
                WHERE towbook_call_number = ?
            ''', (new_archived, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), call_number))
            
            status_text = "completed" if new_archived == 1 else "active"
            log_action("ARCHIVE_TOGGLE", call_number, f"Changed vehicle status to {status_text}")
            
            return True, f"Vehicle status changed to {status_text}"
            
    except Exception as e:
        logging.error(f"Error toggling archive status: {e}")
        return False, f"Error toggling archive status: {str(e)}"

def check_and_update_statuses():
    """Auto-update statuses based on days since tow date"""
    try:
        from utils import log_action
        
        with transaction() as conn:
            cursor = conn.cursor()
            
            # Get all active vehicles
            cursor.execute('''
                SELECT towbook_call_number, tow_date, top_form_sent_date, status, owner_known, tr52_available_date 
                FROM vehicles 
                WHERE archived = 0 AND status IN ('New', 'TOP Generated', 'Ready for Disposition')
            ''')
            
            vehicles = cursor.fetchall()
            today = datetime.now().date()
            
            for vehicle in vehicles:
                if not vehicle['tow_date']:
                    continue
                
                # Convert date format if needed
                try:
                    if '/' in vehicle['tow_date']:
                        month, day, year = vehicle['tow_date'].split('/')
                        tow_date = datetime(int(year), int(month), int(day)).date()
                    else:
                        tow_date = datetime.strptime(vehicle['tow_date'], '%Y-%m-%d').date()
                        
                    days_since_tow = (today - tow_date).days
                    
                    # Auto-update based on status
                    if vehicle['status'] == 'New' and days_since_tow >= 2:
                        # After 2 days, remind to generate TOP
                        cursor.execute('''
                            UPDATE vehicles 
                            SET days_until_next_step = ?
                            WHERE towbook_call_number = ?
                        ''', (0, vehicle['towbook_call_number']))
                        log_action("SYSTEM", vehicle['towbook_call_number'], "TOP form generation reminder")
                        
                    elif vehicle['status'] == 'TOP Generated':
                        # Check if ready for disposition (20 days)
                        if vehicle['tr52_available_date']:
                            tr52_date = datetime.strptime(vehicle['tr52_available_date'], '%Y-%m-%d').date()
                            if today >= tr52_date:
                                # Update to Ready for Disposition
                                cursor.execute('''
                                    UPDATE vehicles 
                                    SET status = 'Ready for Disposition', 
                                        last_updated = ?
                                    WHERE towbook_call_number = ?
                                ''', (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), vehicle['towbook_call_number']))
                                
                                log_action("AUTO_STATUS_CHANGE", vehicle['towbook_call_number'], 
                                        "Automatically updated status to Ready for Disposition after 20 days")
                            else:
                                # Update days remaining
                                days_remaining = (tr52_date - today).days
                                cursor.execute('''
                                    UPDATE vehicles 
                                    SET days_until_next_step = ?
                                    WHERE towbook_call_number = ?
                                ''', (days_remaining, vehicle['towbook_call_number']))
                except Exception as e:
                    logging.error(f"Error processing date for vehicle {vehicle['towbook_call_number']}: {e}")
        
        return True
    except Exception as e:
        logging.error(f"Error in check_and_update_statuses: {e}")
        return False

def get_logs(vehicle_id=None, limit=100):
    """Get activity logs for one or all vehicles"""
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
        conn.close() if 'conn' in locals() else None
        return []

def get_vehicles(tab="active", sort_column=None, sort_direction='asc'):
    """Get all vehicles with optional sorting and tab filtering"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        base_query = "SELECT * FROM vehicles"
        
        # Filter by tab
        if tab == "active":
            base_query += " WHERE archived = 0"
        elif tab == "completed":
            base_query += " WHERE archived = 1"
        
        # Apply sorting if specified
        if sort_column and sort_column in ['towbook_call_number', 'complaint_number', 'tow_date', 
                                        'jurisdiction', 'vin', 'make', 'model', 'status', 
                                        'release_reason', 'release_date']:
            # Sanitize sort_direction to prevent SQL injection
            sort_direction = 'asc' if sort_direction.lower() != 'desc' else 'desc'
            base_query += f" ORDER BY {sort_column} {sort_direction}"
        else:
            # Default sort by most recent update
            base_query += " ORDER BY last_updated DESC"
        
        cursor.execute(base_query)
        vehicles = cursor.fetchall()
        conn.close()
        return vehicles
    except Exception as e:
        logging.error(f"Error getting vehicles: {e}")
        conn.close() if 'conn' in locals() else None
        return []

def create_auction(auction_date, vehicle_ids):
    """Create a new auction and assign vehicles to it"""
    from utils import log_action
    
    try:
        with transaction() as conn:
            cursor = conn.cursor()
            
            # Parse and format the date
            auction_date_obj = datetime.strptime(auction_date, '%Y-%m-%d')
            
            # Calculate ad date (Wednesday before auction)
            days_to_wednesday = (2 - auction_date_obj.weekday()) % 7  # 2 = Wednesday
            if days_to_wednesday == 0:  # If auction date is Wednesday, use previous Wednesday
                days_to_wednesday = 7
            ad_date = auction_date_obj - timedelta(days=days_to_wednesday)
            
            # Get VIN list for the auction
            cursor.execute(f'''
                SELECT vin FROM vehicles 
                WHERE towbook_call_number IN ({','.join(['?' for _ in vehicle_ids])})
            ''', vehicle_ids)
            
            vin_list = [row['vin'] for row in cursor.fetchall() if row['vin']]
            vin_list_str = ', '.join(vin_list)
            
            # Create auction record
            cursor.execute('''
                INSERT INTO auctions (auction_date, ad_date, status, vin_list, created_date, updated_date)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                auction_date, 
                ad_date.strftime('%Y-%m-%d'),
                'Scheduled',
                vin_list_str,
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            ))
            
            auction_id = cursor.lastrowid
            
            # Update vehicles with auction info
            for vehicle_id in vehicle_ids:
                cursor.execute('''
                    UPDATE vehicles
                    SET status = 'In Auction',
                        auction_date = ?,
                        auction_id = ?,
                        last_updated = ?
                    WHERE towbook_call_number = ?
                ''', (
                    auction_date,
                    auction_id,
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    vehicle_id
                ))
                
                log_action("AUCTION_SCHEDULED", vehicle_id, f"Added to auction #{auction_id} on {auction_date}")
            
            return True, f"Successfully created auction #{auction_id} with {len(vehicle_ids)} vehicles"
    except Exception as e:
        logging.error(f"Error creating auction: {e}")
        return False, f"Error creating auction: {str(e)}"

def batch_update_status(vehicle_ids, new_status):
    """Update status for multiple vehicles at once"""
    from utils import log_action
    
    try:
        # Map frontend status to actual database status if needed
        status_map = {
            'TOP_Sent': 'TOP Generated',
            'Ready': 'Ready for Disposition',
            'Paperwork': 'Paperwork Received',
            'Action': 'Ready for Action'
        }
        
        db_status = status_map.get(new_status, new_status)
        
        with transaction() as conn:
            cursor = conn.cursor()
            
            updated_count = 0
            for call_number in vehicle_ids:
                cursor.execute(
                    "UPDATE vehicles SET status = ?, last_updated = ? WHERE towbook_call_number = ?",
                    (db_status, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), call_number)
                )
                if cursor.rowcount > 0:
                    updated_count += 1
                    log_action("STATUS_CHANGE", call_number, f"Changed status to {db_status} (batch update)")
            
            return True, updated_count, f"Updated {updated_count} vehicles to {db_status}"
    except Exception as e:
        logging.error(f"Error in batch update: {e}")
        return False, 0, str(e)