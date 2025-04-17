from datetime import datetime, timedelta
import sqlite3
import logging

def get_db_connection():
    conn = sqlite3.connect('vehicles.db')
    conn.row_factory = sqlite3.Row
    return conn

def generate_complaint_number():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        current_year = datetime.now().strftime('%y')
        cursor.execute("SELECT complaint_sequence FROM vehicles WHERE complaint_year = ? ORDER BY complaint_sequence DESC LIMIT 1", (current_year,))
        result = cursor.fetchone()
        next_sequence = 95 if not result else result[0] + 1
        conn.close()
        return f"IT{next_sequence:04d}-{current_year}", next_sequence, current_year
    except Exception as e:
        logging.error(f"Complaint number error: {e}")
        return f"ITERR-{current_year}", 999, current_year

def ensure_logs_table_exists():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('CREATE TABLE IF NOT EXISTS logs (id INTEGER PRIMARY KEY AUTOINCREMENT, action_type TEXT, vehicle_id TEXT, details TEXT, timestamp TEXT)')
        conn.commit()
        conn.close()
    except Exception as e:
        logging.error(f"Logs table error: {e}")

def log_action(action_type, vehicle_id, details):
    ensure_logs_table_exists()
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO logs (action_type, vehicle_id, details, timestamp) VALUES (?, ?, ?, ?)",
                       (action_type, vehicle_id, details, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logging.error(f"Log error: {e}")
        return False

def convert_frontend_status(frontend_status):
    status_map = {
        'New': 'New',
        'TOP_Generated': 'TOP Generated',
        'TR52_Ready': 'TR52 Ready',
        'Ready_Auction': 'Ready for Auction',
        'Ready_Scrap': 'Ready for Scrap',
        'Auction': 'Auction',
        'Scrapped': 'Scrapped',
        'Released': 'Released',
        'Completed': 'Released',
        'TOP Generated': 'TOP Generated',
        'TR52 Ready': 'TR52 Ready',
        'Ready for Auction': 'Ready for Auction',
        'Ready for Scrap': 'Ready for Scrap',
        'Auctioned': 'Auctioned'
    }
    logging.info(f"Converting status: {frontend_status} → {status_map.get(frontend_status, frontend_status)}")
    return status_map.get(frontend_status, frontend_status)

def release_vehicle(call_number, reason, recipient=None, release_date=None, release_time=None):
    from database import update_vehicle_status
    if not release_date:
        release_date = datetime.now().strftime('%Y-%m-%d')
    if not release_time:
        release_time = datetime.now().strftime('%H:%M:%S')
    fields = {
        'release_reason': reason,
        'release_date': release_date,
        'release_time': release_time,
        'recipient': recipient or 'N/A',
        'archived': 1
    }
    status = 'Released' if reason.lower() not in ['scrapped', 'auctioned'] else reason.capitalize()
    success = update_vehicle_status(call_number, status, fields)
    if success:
        log_action("RELEASE", call_number, f"Released: {reason}, to: {recipient or 'N/A'}")
    return success

def calculate_next_auction_date(ad_placement_date=None):
    today = datetime.now().date()
    if ad_placement_date:
        if isinstance(ad_placement_date, str):
            ad_date = datetime.strptime(ad_placement_date, '%Y-%m-%d').date()
        else:
            ad_date = ad_placement_date
        min_auction_date = ad_date + timedelta(days=5)
        days_to_monday = (7 - min_auction_date.weekday()) % 7
        if days_to_monday == 0:
            days_to_monday = 7
        return min_auction_date + timedelta(days=days_to_monday)
    else:
        days_to_monday = (7 - today.weekday()) % 7 or 7
        return today + timedelta(days=days_to_monday)

def calculate_newspaper_ad_date(auction_date):
    if isinstance(auction_date, str):
        auction_date = datetime.strptime(auction_date, '%Y-%m-%d').date()
    target_date = auction_date - timedelta(days=5)
    days_to_wednesday = (target_date.weekday() - 2) % 7
    if days_to_wednesday == 0 and (auction_date - target_date).days < 5:
        days_to_wednesday = 7
    return target_date - timedelta(days=days_to_wednesday)

def get_status_filter(status_type):
    filters = {
        'New': ['New'],
        'TOP_Generated': ['TOP Generated'],
        'TR52_Ready': ['TR52 Ready'],
        'Ready_Auction': ['Ready for Auction'],
        'Ready_Scrap': ['Ready for Scrap'],
        'Auction': ['Auction'],
        'Completed': ['Released', 'Scrapped', 'Auctioned']
    }
    backward_compat = {
        'Ready': ['TR52 Ready', 'Ready for Auction', 'Ready for Scrap'],
        'Scheduled': ['Scheduled for Release']
    }
    return filters.get(status_type, backward_compat.get(status_type, []))

def calculate_tr52_countdown(top_sent_date):
    if not top_sent_date:
        return None
    try:
        if isinstance(top_sent_date, str):
            top_date = datetime.strptime(top_sent_date, '%Y-%m-%d').date()
        else:
            top_date = top_sent_date
        tr52_date = top_date + timedelta(days=20)
        today = datetime.now().date()
        days_left = (tr52_date - today).days
        return max(0, days_left)
    except Exception as e:
        logging.error(f"Error calculating TR52 countdown: {e}")
        return None

def update_vehicle_status(towbook_call_number, new_status, update_fields=None):
    try:
        new_status = convert_frontend_status(new_status)
        logging.info(f"Updating vehicle {towbook_call_number} to status: {new_status}")
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM vehicles WHERE towbook_call_number = ?", (towbook_call_number,))
        vehicle = cursor.fetchone()
        if not vehicle:
            conn.close()
            logging.error(f"Vehicle not found: {towbook_call_number}")
            return False
        
        if not update_fields:
            update_fields = {}
        update_fields['status'] = new_status
        update_fields['last_updated'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        if new_status == 'TOP Generated':
            update_fields['top_form_sent_date'] = datetime.now().strftime('%Y-%m-%d')
            tr52_date = datetime.now() + timedelta(days=20)
            update_fields['tr52_available_date'] = tr52_date.strftime('%Y-%m-%d')
            update_fields['days_until_next_step'] = 20
            update_fields['redemption_end_date'] = tr52_date.strftime('%Y-%m-%d')
        
        elif new_status == 'TR52 Ready':
            if 'tr52_received_date' not in update_fields:
                update_fields['tr52_received_date'] = datetime.now().strftime('%Y-%m-%d')
        
        elif new_status == 'Ready for Auction':
            auction_date = calculate_next_auction_date()
            update_fields['auction_date'] = auction_date.strftime('%Y-%m-%d')
            update_fields['decision'] = 'Auction'
            update_fields['decision_date'] = datetime.now().strftime('%Y-%m-%d')
            days_until_auction = (auction_date - datetime.now().date()).days
            update_fields['days_until_auction'] = max(0, days_until_auction)
            update_fields['ad_placement_date'] = calculate_newspaper_ad_date(auction_date).strftime('%Y-%m-%d')
        
        elif new_status == 'Ready for Scrap':
            scrap_date = datetime.now() + timedelta(days=7)
            update_fields['estimated_date'] = scrap_date.strftime('%Y-%m-%d')
            update_fields['decision'] = 'Scrap'
            update_fields['decision_date'] = datetime.now().strftime('%Y-%m-%d')
            update_fields['days_until_next_step'] = 7
        
        elif new_status in ['Released', 'Auctioned', 'Scrapped']:
            update_fields['archived'] = 1
            if 'release_date' not in update_fields:
                update_fields['release_date'] = datetime.now().strftime('%Y-%m-%d')
            if 'release_time' not in update_fields:
                update_fields['release_time'] = datetime.now().strftime('%H:%M')
            if 'release_reason' not in update_fields:
                update_fields['release_reason'] = new_status
            if new_status == 'Auctioned' and 'sale_amount' in update_fields and 'fees' in update_fields:
                update_fields['net_proceeds'] = update_fields['sale_amount'] - update_fields['fees']
        
        set_clause = ', '.join([f"{k} = ?" for k in update_fields.keys()])
        values = list(update_fields.values()) + [towbook_call_number]
        logging.info(f"Update fields: {update_fields}")
        cursor.execute(f'UPDATE vehicles SET {set_clause} WHERE towbook_call_number = ?', values)
        conn.commit()
        cursor.execute("SELECT status FROM vehicles WHERE towbook_call_number = ?", (towbook_call_number,))
        updated = cursor.fetchone()
        conn.close()
        if updated and updated['status'] == new_status:
            logging.info(f"Status successfully updated to {new_status} for {towbook_call_number}")
            log_action("STATUS_CHANGE", towbook_call_number, f"Status changed to {new_status}")
            return True
        else:
            logging.error(f"Status update verification failed for {towbook_call_number}")
            return False
    except Exception as e:
        logging.error(f"Status update error: {e}")
        return False

def setup_logging():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s',
                        handlers=[logging.FileHandler('app.log'), logging.StreamHandler()])