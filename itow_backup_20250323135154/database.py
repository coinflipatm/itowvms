import sqlite3
from datetime import datetime, timedelta
import logging

def get_db_connection():
    conn = sqlite3.connect('vehicles.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS vehicles (
            towbook_call_number TEXT PRIMARY KEY,
            invoice_number TEXT,
            vin TEXT,
            make TEXT,
            model TEXT,
            tow_date TEXT,
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
            invoice_year TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action_type TEXT,
            vehicle_id TEXT,
            details TEXT,
            timestamp TEXT
        )
    ''')
    
    conn.commit()
    conn.close()

def insert_vehicle(data):
    from utils import generate_invoice_number, log_action
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if we already have an invoice number
    if not data.get('invoice_number'):
        invoice_number, sequence, year = generate_invoice_number()
        data['invoice_number'] = invoice_number
        data['invoice_sequence'] = sequence
        data['invoice_year'] = year
    
    # Determine if owner is known
    owner_known = 'Yes' if data.get('vin') or data.get('plate') else 'No'
    
    cursor.execute('''
        INSERT OR REPLACE INTO vehicles (
            towbook_call_number, invoice_number, vin, make, model, tow_date, 
            status, last_updated, owner_known, invoice_sequence, invoice_year
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        data['towbook_call_number'], 
        data.get('invoice_number', ''), 
        data.get('vin', ''),
        data.get('make', ''), 
        data.get('model', ''), 
        data.get('tow_date', ''),
        'New', 
        datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 
        owner_known,
        data.get('invoice_sequence'),
        data.get('invoice_year')
    ))
    
    conn.commit()
    conn.close()
    
    # Log the action
    log_action("INSERT", data['towbook_call_number'], f"Added vehicle: {data.get('make', '')} {data.get('model', '')}")

def update_status(vehicle_id, new_status, update_fields=None):
    from utils import log_action
    
    conn = get_db_connection()
    cursor = conn.cursor()
    if update_fields:
        set_clause = ', '.join([f"{field} = ?" for field in update_fields.keys()])
        values = list(update_fields.values()) + [new_status, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), vehicle_id]
        cursor.execute(f'''
            UPDATE vehicles SET {set_clause}, status = ?, last_updated = ?
            WHERE towbook_call_number = ?
        ''', values)
    else:
        cursor.execute('''
            UPDATE vehicles SET status = ?, last_updated = ?
            WHERE towbook_call_number = ?
        ''', (new_status, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), vehicle_id))
    
    conn.commit()
    conn.close()
    
    # Log the status change
    log_action("STATUS_CHANGE", vehicle_id, f"Changed status to {new_status}")
def update_vehicle_status(vehicle_id, new_status, update_fields=None):

    """Update a vehicle's status with enhanced status tracking"""
    from utils import log_action
    
    valid_statuses = [
        'New',                  # Just added to system
        'TOP Sent',             # TOP form has been generated and sent
        'Ready for Disposition', # Hold period complete, action can be taken
        'Decision Pending',     # Waiting for decision on auction/scrap/release
        'Ready for Auction',    # Decision made to auction
        'Ready for Scrap',      # Decision made to scrap
        'Auctioned',            # Vehicle has been auctioned
        'Scrapped',             # Vehicle has been scrapped
        'Released',             # Vehicle released to owner or other party
        'Archived'              # Record archived (can be any status)
    ]
    
    # Validate status
    if new_status not in valid_statuses:
        logging.warning(f"Invalid status: {new_status}. Using 'New' instead.")
        new_status = 'New'
    
    conn = get_db_connection()
    cursor = conn.cursor()
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # Add status change to update fields
    if not update_fields:
        update_fields = {}
    
    # For specific statuses, set additional fields
    if new_status == 'TOP Sent' and 'top_form_sent_date' not in update_fields:
        update_fields['top_form_sent_date'] = datetime.now().strftime('%Y-%m-%d')
    
    if new_status == 'Archived' and 'archived' not in update_fields:
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
    
    conn.commit()
    conn.close()
    
    # Log the action
    log_action("STATUS_CHANGE", vehicle_id, f"Changed status to {new_status}")
    
    return True

def get_vehicles(status_filter=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    if status_filter == 'active':
        cursor.execute("SELECT * FROM vehicles WHERE archived = 0")
    elif status_filter == 'completed':
        cursor.execute("SELECT * FROM vehicles WHERE archived = 1")
    else:
        cursor.execute('SELECT * FROM vehicles')
    vehicles = cursor.fetchall()
    conn.close()
    return vehicles

def check_and_update_statuses():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT towbook_call_number, tow_date, top_form_sent_date, status, owner_known FROM vehicles WHERE archived = 0')
    vehicles = cursor.fetchall()
    for vehicle in vehicles:
        if not vehicle['tow_date']:
            continue
            
        # Convert date format if needed (MM/DD/YYYY to YYYY-MM-DD)
        tow_date_str = vehicle['tow_date']
        try:
            if '/' in tow_date_str:
                month, day, year = tow_date_str.split('/')
                tow_date = datetime(int(year), int(month), int(day))
            else:
                tow_date = datetime.strptime(tow_date_str, '%Y-%m-%d')
                
            days_since_tow = (datetime.now() - tow_date).days
            
            if vehicle['status'] == 'TOP Sent' and vehicle['owner_known'] == 'Yes' and days_since_tow >= 30:
                update_status(vehicle['towbook_call_number'], 'Ready for Disposition', {'tr52_available_date': datetime.now().strftime('%Y-%m-%d')})
            elif vehicle['status'] == 'TOP Sent' and vehicle['owner_known'] == 'No' and days_since_tow >= 10:
                update_status(vehicle['towbook_call_number'], 'Ready for Disposition', {'tr52_available_date': datetime.now().strftime('%Y-%m-%d')})
        except Exception as e:
            print(f"Error processing date for vehicle {vehicle['towbook_call_number']}: {e}")
            
    conn.close()

def get_logs(vehicle_id=None, limit=100):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if vehicle_id:
        cursor.execute("SELECT * FROM logs WHERE vehicle_id = ? ORDER BY timestamp DESC LIMIT ?", (vehicle_id, limit))
    else:
        cursor.execute("SELECT * FROM logs ORDER BY timestamp DESC LIMIT ?", (limit,))
        
    logs = cursor.fetchall()
    conn.close()
    return logs