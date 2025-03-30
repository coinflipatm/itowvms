from datetime import datetime, timedelta
import sqlite3
import logging

def generate_complaint_number():
    try:
        conn = sqlite3.connect('vehicles.db')
        cursor = conn.cursor()
        current_year = datetime.now().strftime('%y')
        cursor.execute("SELECT complaint_sequence FROM vehicles WHERE complaint_year = ? ORDER BY complaint_sequence DESC LIMIT 1", (current_year,))
        result = cursor.fetchone()
        next_sequence = 95 if not result else result[0] + 1  # Start at 95 per user request
        conn.close()
        return f"IT{next_sequence:04d}-{current_year}", next_sequence, current_year
    except Exception as e:
        logging.error(f"Complaint number error: {e}")
        return f"ITERR-{current_year}", 999, current_year

def ensure_logs_table_exists():
    try:
        conn = sqlite3.connect('vehicles.db')
        cursor = conn.cursor()
        cursor.execute('CREATE TABLE IF NOT EXISTS logs (id INTEGER PRIMARY KEY AUTOINCREMENT, action_type TEXT, vehicle_id TEXT, details TEXT, timestamp TEXT)')
        conn.commit()
        conn.close()
    except Exception as e:
        logging.error(f"Logs table error: {e}")

def log_action(action_type, vehicle_id, details):
    ensure_logs_table_exists()
    try:
        conn = sqlite3.connect('vehicles.db')
        cursor = conn.cursor()
        cursor.execute("INSERT INTO logs (action_type, vehicle_id, details, timestamp) VALUES (?, ?, ?, ?)",
                       (action_type, vehicle_id, details, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logging.error(f"Log error: {e}")
        return False

def release_vehicle(call_number, reason, recipient=None, release_date=None, release_time=None):
    from database import update_vehicle_status  # Move import here to avoid circular import
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
    """
    Calculate the next auction date. If ad_placement_date is provided, set the auction
    for the next Monday at least 5 days after the ad date. Otherwise, default to the
    next Monday from today.
    """
    today = datetime.now().date()
    if ad_placement_date:
        if isinstance(ad_placement_date, str):
            ad_date = datetime.strptime(ad_placement_date, '%Y-%m-%d').date()
        else:
            ad_date = ad_placement_date
        # Ensure auction is at least 5 days after ad placement, on a Monday
        min_auction_date = ad_date + timedelta(days=5)
        days_to_monday = (7 - min_auction_date.weekday()) % 7
        if days_to_monday == 0:  # If it's already Monday, push to next Monday
            days_to_monday = 7
        return min_auction_date + timedelta(days=days_to_monday)
    else:
        # Default to next Monday from today
        days_to_monday = (7 - today.weekday()) % 7 or 7
        return today + timedelta(days=days_to_monday)

def calculate_newspaper_ad_date(auction_date):
    """
    Calculate the newspaper ad date, which should be a Wednesday at least 5 days
    before the auction date.
    """
    if isinstance(auction_date, str):
        auction_date = datetime.strptime(auction_date, '%Y-%m-%d').date()
    # Aim for a Wednesday (weekday 2) at least 5 days before auction
    target_date = auction_date - timedelta(days=5)
    days_to_wednesday = (target_date.weekday() - 2) % 7
    if days_to_wednesday == 0 and (auction_date - target_date).days < 5:
        days_to_wednesday = 7  # Push to previous Wednesday if too close
    return target_date - timedelta(days=days_to_wednesday)

def get_status_filter(status_type):
    """
    Map UI status types to database statuses based on the desired flow:
    New → TOP Sent → Ready → Scheduled for Release → Auction → Completed
    """
    filters = {
        'New': ['New'],
        'TOP_Sent': ['TOP Sent'],
        'Ready': ['Ready'],
        'Scheduled': ['Scheduled for Release'],
        'Auction': ['Auction'],
        'Completed': ['Released', 'Scrapped', 'Auctioned']
    }
    return filters.get(status_type, [])

def setup_logging():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s',
                        handlers=[logging.FileHandler('app.log'), logging.StreamHandler()])