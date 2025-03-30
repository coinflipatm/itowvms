import sqlite3
from datetime import datetime, timedelta
import logging
from utils import calculate_next_auction_date, calculate_newspaper_ad_date, get_status_filter

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
            complaint_number TEXT,
            vin TEXT,
            make TEXT,
            model TEXT,
            year TEXT,
            color TEXT,
            tow_date TEXT,
            tow_time TEXT,
            location TEXT,
            requestor TEXT,
            jurisdiction TEXT,
            status TEXT DEFAULT 'New',
            top_form_sent_date TEXT,
            tr52_available_date TEXT,
            decision TEXT,
            decision_date TEXT,
            auction_date TEXT,
            last_updated TEXT,
            archived INTEGER DEFAULT 0,
            release_reason TEXT,
            release_date TEXT,
            release_time TEXT,
            recipient TEXT,
            complaint_sequence INTEGER,
            complaint_year TEXT,
            plate TEXT,
            state TEXT,
            case_number TEXT,
            officer_name TEXT,
            days_until_next_step INTEGER,
            paperwork_received_date TEXT,
            estimated_date TEXT,
            ad_placement_date TEXT
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
    # Ensure vehicle_id column exists
    cursor.execute("PRAGMA table_info(logs)")
    columns = [col[1] for col in cursor.fetchall()]
    if 'vehicle_id' not in columns:
        cursor.execute("ALTER TABLE logs ADD COLUMN vehicle_id TEXT")
    conn.commit()
    conn.close()
    logging.info("Database initialized")

def insert_vehicle(vehicle_data):  # Removed unused 'data' parameter
    from utils import log_action, generate_complaint_number
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        towbook_call_number = vehicle_data.get('towbook_call_number')
        # Check if vehicle exists
        cursor.execute("SELECT COUNT(*) FROM vehicles WHERE towbook_call_number = ?", (towbook_call_number,))
        exists = cursor.fetchone()[0] > 0
        if exists:
            # Update existing vehicle
            cursor.execute("""
                UPDATE vehicles SET 
                    complaint_number = ?, jurisdiction = ?, tow_date = ?, tow_time = ?, location = ?, 
                    vin = ?, year = ?, make = ?, model = ?, color = ?, plate = ?, status = ?, 
                    last_updated = ?
                WHERE towbook_call_number = ?
            """, (
                vehicle_data.get('complaint_number'), vehicle_data.get('jurisdiction'), 
                vehicle_data.get('tow_date'), vehicle_data.get('tow_time'), vehicle_data.get('location'),
                vehicle_data.get('vin'), vehicle_data.get('year'), vehicle_data.get('make'), 
                vehicle_data.get('model'), vehicle_data.get('color'), vehicle_data.get('plate'), 
                vehicle_data.get('status', 'New'), datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 
                towbook_call_number
            ))
            logging.info(f"Updated existing vehicle {towbook_call_number}")
        else:
            # Insert new vehicle
            cursor.execute("""
                INSERT INTO vehicles (
                    towbook_call_number, complaint_number, jurisdiction, tow_date, tow_time, location, 
                    vin, year, make, model, color, plate, status, last_updated
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                towbook_call_number, vehicle_data.get('complaint_number'), vehicle_data.get('jurisdiction'),
                vehicle_data.get('tow_date'), vehicle_data.get('tow_time'), vehicle_data.get('location'),
                vehicle_data.get('vin'), vehicle_data.get('year'), vehicle_data.get('make'), 
                vehicle_data.get('model'), vehicle_data.get('color'), vehicle_data.get('plate'), 
                'New', datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            ))
            logging.info(f"Inserted new vehicle {towbook_call_number}")
        conn.commit()
        conn.close()
        log_action("INSERT", towbook_call_number, f"Added vehicle: {vehicle_data.get('make', '')} {vehicle_data.get('model', '')}")
        return True, "Vehicle added"
    except Exception as e:
        logging.error(f"Insert error: {e}")
        return False, str(e)

def update_vehicle_status(towbook_call_number, new_status, update_fields=None):
    from utils import log_action
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM vehicles WHERE towbook_call_number = ?", (towbook_call_number,))
        vehicle = cursor.fetchone()
        if not vehicle:
            conn.close()
            return False
        
        if not update_fields:
            update_fields = {}
        update_fields['status'] = new_status
        update_fields['last_updated'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        if new_status == 'TOP Sent':
            update_fields['top_form_sent_date'] = datetime.now().strftime('%Y-%m-%d')
            tr52_date = datetime.now() + timedelta(days=20)
            update_fields['tr52_available_date'] = tr52_date.strftime('%Y-%m-%d')
        
        elif new_status == 'Auction':
            ad_placement_date = update_fields.get('ad_placement_date') or vehicle['ad_placement_date']
            auction_date = calculate_next_auction_date(ad_placement_date)
            update_fields['auction_date'] = auction_date.strftime('%Y-%m-%d')
        
        elif new_status in ['Released', 'Auctioned', 'Scrapped']:
            update_fields['archived'] = 1
            if 'release_date' not in update_fields:
                update_fields['release_date'] = datetime.now().strftime('%Y-%m-%d')
            if 'release_time' not in update_fields:
                update_fields['release_time'] = datetime.now().strftime('%H:%M')
        
        set_clause = ', '.join([f"{k} = ?" for k in update_fields.keys()])
        values = list(update_fields.values()) + [towbook_call_number]
        cursor.execute(f'UPDATE vehicles SET {set_clause} WHERE towbook_call_number = ?', values)
        conn.commit()
        conn.close()
        log_action("STATUS_CHANGE", towbook_call_number, f"Status changed to {new_status}")
        return True
    except Exception as e:
        logging.error(f"Status update error: {e}")
        return False

def get_vehicles_by_status(status_type):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        status_filter = get_status_filter(status_type)
        if not status_filter:
            conn.close()
            return []
        if status_type == 'Completed':
            cursor.execute("""
                SELECT * FROM vehicles 
                WHERE status IN ({}) AND archived = 0
            """.format(','.join('?' * len(status_filter))), status_filter)
        elif status_type == 'Scheduled':
            cursor.execute("""
                SELECT * FROM vehicles 
                WHERE status = 'Scheduled for Release' AND archived = 0
            """)
        else:
            cursor.execute("""
                SELECT * FROM vehicles 
                WHERE status IN ({}) AND archived = 0
            """.format(','.join('?' * len(status_filter))), status_filter)
        vehicles = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return vehicles
    except Exception as e:
        logging.error(f"Get vehicles error: {e}")
        return []

def update_vehicle(old_call_number, data):
    from utils import log_action
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        new_call_number = data.get('towbook_call_number', old_call_number)
        data['last_updated'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        if new_call_number != old_call_number:
            cursor.execute("SELECT * FROM vehicles WHERE towbook_call_number = ?", (old_call_number,))
            old_vehicle = cursor.fetchone()
            if not old_vehicle:
                conn.close()
                return False, "Vehicle not found"
            new_vehicle = dict(old_vehicle)
            new_vehicle.update(data)
            fields = list(new_vehicle.keys())
            values = list(new_vehicle.values())
            placeholders = ','.join(['?' for _ in fields])
            cursor.execute(f'INSERT OR REPLACE INTO vehicles ({",".join(fields)}) VALUES ({placeholders})', values)
            if new_call_number != old_call_number:
                cursor.execute("DELETE FROM vehicles WHERE towbook_call_number = ?", (old_call_number,))
                cursor.execute("UPDATE logs SET vehicle_id = ? WHERE vehicle_id = ?", (new_call_number, old_call_number))
        else:
            set_clause = ', '.join([f"{k} = ?" for k in data.keys()])
            values = list(data.values()) + [old_call_number]
            cursor.execute(f'UPDATE vehicles SET {set_clause} WHERE towbook_call_number = ?', values)
        conn.commit()
        conn.close()
        log_action("UPDATE", new_call_number, "Vehicle updated")
        return True, "Vehicle updated"
    except Exception as e:
        logging.error(f"Update error: {e}")
        return False, str(e)

def toggle_archive_status(call_number):
    from utils import log_action
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT archived FROM vehicles WHERE towbook_call_number = ?", (call_number,))
        result = cursor.fetchone()
        if not result:
            conn.close()
            return False, "Vehicle not found"
        new_archived = 1 if result['archived'] == 0 else 0
        cursor.execute("UPDATE vehicles SET archived = ?, last_updated = ? WHERE towbook_call_number = ?",
                       (new_archived, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), call_number))
        conn.commit()
        conn.close()
        status_text = "completed" if new_archived else "active"
        log_action("ARCHIVE_TOGGLE", call_number, f"Status toggled to {status_text}")
        return True, f"Status changed to {status_text}"
    except Exception as e:
        logging.error(f"Toggle error: {e}")
        return False, str(e)

def check_and_update_statuses():
    from utils import log_action
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM vehicles WHERE archived = 0")
        vehicles = cursor.fetchall()
        today = datetime.now().date()
        for vehicle in vehicles:
            tow_date = vehicle['tow_date']
            if tow_date:
                try:
                    tow_date = datetime.strptime(tow_date, '%Y-%m-%d').date()
                except ValueError:
                    tow_date = datetime.strptime(tow_date, '%m/%d/%Y').date()
                    cursor.execute("UPDATE vehicles SET tow_date = ? WHERE towbook_call_number = ?",
                                   (tow_date.strftime('%Y-%m-%d'), vehicle['towbook_call_number']))
                days_since_tow = (today - tow_date).days

                if vehicle['status'] == 'TOP Sent' and days_since_tow >= 20:
                    cursor.execute("""
                        UPDATE vehicles SET status = ?, last_updated = ?, days_until_next_step = 0 
                        WHERE towbook_call_number = ?
                    """, ('Ready', datetime.now().strftime('%Y-%m-%d %H:%M:%S'), vehicle['towbook_call_number']))
                    log_action("AUTO_STATUS", vehicle['towbook_call_number'], "Moved to Ready")
                elif vehicle['status'] == 'TOP Sent':
                    days_left = 20 - days_since_tow
                    cursor.execute("UPDATE vehicles SET days_until_next_step = ? WHERE towbook_call_number = ?",
                                   (days_left, vehicle['towbook_call_number']))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logging.error(f"Status check error: {e}")
        return False
    
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
        logging.error(f"Get logs error: {e}")
        return []

def create_auction(auction_date, vehicle_ids):
    from utils import log_action
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(f"SELECT vin FROM vehicles WHERE towbook_call_number IN ({','.join(['?' for _ in vehicle_ids])})", vehicle_ids)
        vin_list = ', '.join([row['vin'] for row in cursor.fetchall() if row['vin']])
        cursor.execute("INSERT INTO auctions (auction_date, status, vin_list, created_date) VALUES (?, 'Scheduled', ?, ?)",
                       (auction_date, vin_list, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        auction_id = cursor.lastrowid
        for vehicle_id in vehicle_ids:
            cursor.execute("UPDATE vehicles SET status = 'Auction', auction_date = ?, last_updated = ? WHERE towbook_call_number = ?",
                           (auction_date, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), vehicle_id))
        conn.commit()
        conn.close()
        log_action("AUCTION", "BATCH", f"Auction #{auction_id} created with {len(vehicle_ids)} vehicles")
        return True, f"Auction #{auction_id} created"
    except Exception as e:
        logging.error(f"Auction error: {e}")
        return False, str(e)

def batch_update_status(vehicle_ids, new_status):
    from utils import log_action
    try:
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