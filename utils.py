#utils.py

from datetime import datetime, timedelta
import sqlite3
import logging
import os
import json

def get_progress_mock():
    """Mock progress for testing"""
    return {'percentage': 50, 'is_running': True}

def update_vehicle_status(call_number, status, fields=None):
    """Update a vehicle's status and additional fields"""
    try:
        from database import update_vehicle_status as db_update_vehicle_status
        return db_update_vehicle_status(call_number, status, fields)
    except Exception as e:
        logging.error(f"Error updating vehicle status: {e}")
        return False

def generate_invoice_number():
    """Generate an invoice number in the format ITXXXX-YY starting from current sequence"""
    try:
        conn = sqlite3.connect('vehicles.db')
        cursor = conn.cursor()
        
        # Get current year
        current_year = datetime.now().strftime('%y')
        
        # Find the highest existing invoice number for this year
        cursor.execute("""
            SELECT invoice_number FROM vehicles 
            WHERE invoice_number LIKE ? 
            ORDER BY invoice_number DESC LIMIT 1
        """, (f'IT%-{current_year}',))
        
        result = cursor.fetchone()
        
        if result and result[0]:
            # Extract the sequence number from existing invoice
            try:
                current_sequence = int(result[0].split('-')[0].replace('IT', ''))
                next_sequence = current_sequence + 1
            except:
                # If parsing fails, start from 90 (current position)
                next_sequence = 90
        else:
            # First invoice of the year
            next_sequence = 1
        
        conn.close()
        
        # Format: ITXXXX-YY (e.g., IT0090-25)
        invoice_number = f"IT{next_sequence:04d}-{current_year}"
        
        return invoice_number, next_sequence, current_year
    except Exception as e:
        logging.error(f"Error generating invoice number: {e}")
        return f"ITERR-{current_year}", 999, current_year

def ensure_logs_table_exists():
    """Ensure logs table exists before attempting to log actions"""
    try:
        conn = sqlite3.connect('vehicles.db')
        cursor = conn.cursor()
        
        # Create logs table if it doesn't exist
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
    except Exception as e:
        logging.error(f"Failed to ensure logs table exists: {e}")

def log_action(action_type, vehicle_id, details):
    """Log an action with better error handling"""
    try:
        # Make sure logs table exists
        ensure_logs_table_exists()
        
        conn = sqlite3.connect('vehicles.db')
        cursor = conn.cursor()
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        cursor.execute(
            "INSERT INTO logs (action_type, vehicle_id, details, timestamp) VALUES (?, ?, ?, ?)",
            (action_type, vehicle_id, details, timestamp)
        )
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logging.error(f"Failed to log action: {e}")
        return False

def release_vehicle(call_number, reason, recipient=None, release_date=None, release_time=None):
    """Mark a vehicle as released and archive it"""
    # Default current date and time if not provided
    if not release_date:
        release_date = datetime.now().strftime('%Y-%m-%d')
    if not release_time:
        release_time = datetime.now().strftime('%H:%M:%S')
        
    # Prepare release fields
    fields = {
        'release_reason': reason,
        'release_date': release_date,
        'release_time': release_time,
        'archived': 1
    }
    
    if recipient:
        fields['recipient'] = recipient
    
    # Determine appropriate status based on reason
    status = 'Released'  # Default status
    if reason == 'Scrapped' or reason.lower().startswith('scrap'):
        status = 'Scrapped'
    elif reason == 'Auctioned' or reason.lower().startswith('auction'):
        status = 'Auctioned'
        
    success = update_vehicle_status(call_number, status, fields)
    
    if success:
        try:
            log_action('RELEASE', call_number, f"Released as {status} with reason: {reason}, to: {recipient or 'N/A'}, on: {fields['release_date']} at {fields['release_time']}")
        except Exception as e:
            logging.error(f"Failed to log release: {e}")
    
    return success

def calculate_next_auction_date():
    """Calculate the next auction date (next Monday)"""
    today = datetime.now().date()
    days_to_monday = (7 - today.weekday()) % 7  # 0 = Monday, so if today is Monday this is 0
    if days_to_monday == 0:
        days_to_monday = 7  # If today is Monday, schedule for next Monday
    
    next_monday = today + timedelta(days=days_to_monday)
    return next_monday

def calculate_newspaper_ad_date(auction_date):
    """Calculate the date for newspaper ad (Wednesday before auction)"""
    # Convert to datetime if string
    if isinstance(auction_date, str):
        auction_date = datetime.strptime(auction_date, '%Y-%m-%d').date()
        
    # Calculate Wednesday before auction date
    days_to_wednesday = (auction_date.weekday() - 2) % 7  # 2 = Wednesday
    if days_to_wednesday == 0:
        days_to_wednesday = 7  # If auction date is Wednesday, use previous Wednesday
        
    ad_date = auction_date - timedelta(days=days_to_wednesday)
    return ad_date

def format_auction_ad(auction_date, vin_list):
    """Format newspaper ad text with proper date and VIN list"""
    # Format date as MM/DD
    if isinstance(auction_date, str):
        auction_date = datetime.strptime(auction_date, '%Y-%m-%d')
        
    formatted_date = auction_date.strftime('%m/%d')
    
    # Format VIN list with limited characters
    formatted_vins = []
    for vin in vin_list:
        if len(vin) > 8:
            # Use last 8 characters of VIN
            formatted_vins.append(vin[-8:])
        else:
            formatted_vins.append(vin)
    
    # Join VINs with commas
    vin_text = ', '.join(formatted_vins)
    
    # Create ad text
    ad_text = f"iTow Auto Auction - Monday {formatted_date} - 3490 Dolan Dr, Flint - {vin_text}"
    return ad_text

def validate_date_format(date_str):
    """Validate a date string is in YYYY-MM-DD format"""
    try:
        datetime.strptime(date_str, '%Y-%m-%d')
        return True
    except ValueError:
        return False
        
def format_date_for_display(date_str):
    """Format a date string for display (MM/DD/YYYY)"""
    if not date_str:
        return ''
        
    try:
        # Try to convert from ISO format
        dt = datetime.strptime(date_str, '%Y-%m-%d')
        return dt.strftime('%m/%d/%Y')
    except ValueError:
        # If it's already in another format, just return as is
        return date_str
        
def convert_frontend_status(frontend_status):
    """Convert frontend status value to database status"""
    status_map = {
        'New': 'New',
        'TOP_Sent': 'TOP Generated',
        'Ready': 'Ready for Disposition',
        'Paperwork': 'Paperwork Received',
        'Action': 'Ready for Action',
        'InAuction': 'In Auction',
        'Completed': 'Released'
    }
    
    return status_map.get(frontend_status, frontend_status)

def convert_database_status(db_status):
    """Convert database status to frontend status"""
    status_map = {
        'New': 'New',
        'TOP Generated': 'TOP_Sent',
        'Ready for Disposition': 'Ready',
        'Paperwork Received': 'Paperwork',
        'Ready for Auction': 'Action',
        'Ready for Scrap': 'Action',
        'In Auction': 'InAuction',
        'Released': 'Completed',
        'Auctioned': 'Completed',
        'Scrapped': 'Completed'
    }
    
    return status_map.get(db_status, db_status)

def get_status_filter(status_type):
    """Get database status values for a frontend status type"""
    status_filters = {
        'New': ['New'],
        'TOP_Sent': ['TOP Generated'],
        'Ready': ['Ready for Disposition'],
        'Paperwork': ['Paperwork Received'],
        'Action': ['Ready for Auction', 'Ready for Scrap'],
        'InAuction': ['In Auction'],
        'Completed': ['Released', 'Auctioned', 'Scrapped']
    }
    
    return status_filters.get(status_type, [])
    
def ensure_directories():
    """Ensure required directories exist"""
    directories = [
        'static/generated_pdfs',
        'logs'
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        
def setup_logging():
    """Set up logging configuration"""
    # Ensure logs directory exists
    ensure_directories()
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('logs/app.log'),
            logging.StreamHandler()
        ]
    )
    
    logging.info("Logging initialized")