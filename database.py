import sqlite3
from datetime import datetime
import logging
import json

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
            complaint_sequence INTEGER,
            complaint_year TEXT,
            vin TEXT,
            make TEXT,
            model TEXT,
            year TEXT,
            color TEXT,
            plate TEXT,
            state TEXT,
            tow_date TEXT,
            tow_time TEXT,
            location TEXT,
            jurisdiction TEXT,
            requested_by TEXT,
            officer_name TEXT,
            case_number TEXT,
            status TEXT DEFAULT 'New',
            last_updated TEXT,
            top_form_sent_date TEXT,
            top_notification_sent INTEGER DEFAULT 0,
            tr52_available_date TEXT,
            tr52_received_date TEXT,
            redemption_end_date TEXT,
            auction_date TEXT,
            ad_placement_date TEXT,
            auction_ad_sent INTEGER DEFAULT 0,
            release_date TEXT,
            release_time TEXT,
            release_reason TEXT,
            release_notification_sent INTEGER DEFAULT 0,
            recipient TEXT,
            paperwork_received_date TEXT,
            estimated_date TEXT,
            days_until_next_step INTEGER,
            days_until_auction INTEGER,
            photo_paths TEXT,
            sale_amount REAL,
            fees REAL,
            net_proceeds REAL,
            archived INTEGER DEFAULT 0
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS police_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vehicle_id TEXT,
            communication_date TEXT,
            communication_type TEXT,
            notes TEXT,
            FOREIGN KEY (vehicle_id) REFERENCES vehicles(towbook_call_number)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vehicle_id TEXT,
            type TEXT,
            filename TEXT,
            upload_date TEXT,
            FOREIGN KEY (vehicle_id) REFERENCES vehicles(towbook_call_number)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action_type TEXT,
            vehicle_id TEXT,
            timestamp TEXT,
            details TEXT
        )
    ''')
    conn.commit()
    conn.close()

def get_vehicles_by_status(status_type, sort_column=None, sort_direction='desc'):
    conn = get_db_connection()
    cursor = conn.cursor()
    query = "SELECT * FROM vehicles WHERE archived = 0"
    params = []
    
    if status_type and status_type != 'active':
        status_filter, additional_params = get_status_filter(status_type)
        query += f" AND {status_filter}"
        params.extend(additional_params)
    
    if sort_column:
        valid_columns = [
            'towbook_call_number', 'complaint_number', 'vin', 'make', 'model', 
            'year', 'color', 'tow_date', 'jurisdiction', 'status', 'last_updated'
        ]
        if sort_column in valid_columns:
            sort_dir = 'ASC' if sort_direction.lower() == 'asc' else 'DESC'
            query += f" ORDER BY {sort_column} {sort_dir}"
    
    cursor.execute(query, params)
    vehicles = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return vehicles

def update_vehicle_status(call_number, new_status, additional_fields=None):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT status FROM vehicles WHERE towbook_call_number = ?", (call_number,))
        if cursor.fetchone() is None:
            conn.close()
            return False
        update_fields = {
            'status': new_status,
            'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        if additional_fields:
            update_fields.update(additional_fields)
        set_clause = ', '.join([f"{k} = ?" for k in update_fields.keys()])
        values = list(update_fields.values()) + [call_number]
        cursor.execute(f"UPDATE vehicles SET {set_clause} WHERE towbook_call_number = ?", values)
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logging.error(f"Error updating status for {call_number}: {e}")
        return False

def insert_vehicle(data):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        data['last_updated'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        fields = list(data.keys())
        placeholders = ','.join(['?' for _ in fields])
        values = [data[field] if data[field] else 'N/A' for field in fields]
        cursor.execute(f'INSERT INTO vehicles ({",".join(fields)}) VALUES ({placeholders})', values)
        conn.commit()
        conn.close()
        return True, "Vehicle added successfully"
    except Exception as e:
        logging.error(f"Insert error: {e}")
        return False, str(e)

def update_vehicle(call_number, data):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        data['last_updated'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        set_clause = ', '.join([f"{k} = ?" for k in data.keys()])
        values = list(data.values()) + [call_number]
        cursor.execute(f'UPDATE vehicles SET {set_clause} WHERE towbook_call_number = ?', values)
        if cursor.rowcount == 0:
            conn.close()
            return False, "Vehicle not found"
        conn.commit()
        conn.close()
        return True, "Vehicle updated successfully"
    except Exception as e:
        logging.error(f"Update error: {e}")
        return False, str(e)

def check_and_update_statuses():
    conn = get_db_connection()
    cursor = conn.cursor()
    today = datetime.now().date()
    cursor.execute("SELECT towbook_call_number, tow_date, status, top_form_sent_date, tr52_available_date FROM vehicles WHERE archived = 0")
    vehicles = cursor.fetchall()
    for vehicle in vehicles:
        call_number = vehicle['towbook_call_number']
        status = vehicle['status']
        tow_date = datetime.strptime(vehicle['tow_date'], '%Y-%m-%d').date() if vehicle['tow_date'] != 'N/A' else None
        if status == 'New' and tow_date and (today - tow_date).days >= 2 and not vehicle['top_form_sent_date']:
            cursor.execute("UPDATE vehicles SET status = ?, top_form_sent_date = ?, last_updated = ? WHERE towbook_call_number = ?",
                           ('TOP Generated', today.strftime('%Y-%m-%d'), datetime.now().strftime('%Y-%m-%d %H:%M:%S'), call_number))
            log_action("AUTO_STATUS", call_number, "Automatically moved to TOP Generated")
        elif status == 'TOP Generated' and vehicle['tr52_available_date'] != 'N/A':
            tr52_date = datetime.strptime(vehicle['tr52_available_date'], '%Y-%m-%d').date()
            if today >= tr52_date:
                cursor.execute("UPDATE vehicles SET status = ?, last_updated = ? WHERE towbook_call_number = ?",
                               ('TR52 Ready', datetime.now().strftime('%Y-%m-%d %H:%M:%S'), call_number))
                log_action("AUTO_STATUS", call_number, "Automatically moved to TR52 Ready")
    conn.commit()
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

def toggle_archive_status(call_number):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT archived FROM vehicles WHERE towbook_call_number = ?", (call_number,))
    current_status = cursor.fetchone()
    if current_status is None:
        conn.close()
        return False
    new_status = 1 if current_status['archived'] == 0 else 0
    cursor.execute("UPDATE vehicles SET archived = ?, last_updated = ? WHERE towbook_call_number = ?",
                   (new_status, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), call_number))
    conn.commit()
    conn.close()
    return True

def create_auction(auction_date, vehicle_ids):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        auction_date = datetime.strptime(auction_date, '%Y-%m-%d').strftime('%Y-%m-%d')
        ad_date = calculate_newspaper_ad_date(datetime.strptime(auction_date, '%Y-%m-%d'))
        for vehicle_id in vehicle_ids:
            cursor.execute("SELECT status FROM vehicles WHERE towbook_call_number = ?", (vehicle_id,))
            vehicle = cursor.fetchone()
            if vehicle and vehicle['status'] == 'Ready for Auction':
                cursor.execute("""
                    UPDATE vehicles 
                    SET status = ?, 
                        auction_date = ?, 
                        ad_placement_date = ?, 
                        last_updated = ?
                    WHERE towbook_call_number = ?
                """, ('Auction', auction_date, ad_date, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), vehicle_id))
                log_action("AUCTION_SCHEDULED", vehicle_id, f"Scheduled for auction on {auction_date}")
        conn.commit()
        conn.close()
        return True, f"Scheduled {len(vehicle_ids)} vehicles for auction on {auction_date}"
    except Exception as e:
        logging.error(f"Error scheduling auction: {e}")
        return False, str(e)