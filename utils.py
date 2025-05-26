from datetime import datetime, timedelta, date
import sqlite3
import logging
import os
import json
import re
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
import requests
import random
import string
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Replace hardcoded email settings with environment variables
EMAIL_SETTINGS = {
    'smtp_server': os.getenv('SMTP_SERVER', 'smtp.gmail.com'),
    'smtp_port': int(os.getenv('SMTP_PORT', 587)),
    'username': os.getenv('EMAIL_USERNAME', 'your-email@gmail.com'),
    'password': os.getenv('EMAIL_PASSWORD', 'your-app-password'),
    'from_email': os.getenv('FROM_EMAIL', 'iTow Vehicle Management <your-email@gmail.com>')
}

# Replace hardcoded SMS settings with environment variables
SMS_SETTINGS = {
    'api_key': os.getenv('SMS_API_KEY', 'your-sms-api-key'),
    'from_number': os.getenv('SMS_FROM_NUMBER', 'your-from-number')
}

# Existing get_db_connection for 'database.db' (used for logs, auth, etc.)
def get_db_connection():
    conn = sqlite3.connect('database.db')  # Changed from vehicles.db to database.db to match the auth system
    conn.row_factory = sqlite3.Row
    return conn

# New database connection function specifically for 'vehicles.db'
def get_vehicles_db_connection_for_utils():
    try:
        db_name = 'vehicles.db'
        # Assumes utils.py is in the root of the workspace, and vehicles.db is also there.
        script_dir = os.path.dirname(os.path.abspath(__file__))
        db_path = os.path.join(script_dir, db_name)

        if not os.path.exists(db_path):
            logging.warning(f"utils.py: vehicles.db not found at {db_path}. Trying direct name '{db_name}' as CWD might be workspace root.")
            db_path = db_name # Try 'vehicles.db' directly
            if not os.path.exists(db_path):
                current_cwd = os.getcwd()
                logging.error(f"utils.py: vehicles.db still not found at direct path '{db_name}'. Workspace root: {current_cwd}")
                raise Exception(f"utils.py: Vehicles database '{db_name}' not found. Looked in {script_dir} and {current_cwd}.")
        
        # logging.info(f"utils.py: Connecting to vehicles.db at {db_path}") # Reduce verbose logging
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as e:
        # Log the original error and the path it tried if db_path is set
        path_info = f" (path attempted: {locals().get('db_path', 'unknown')})"
        logging.error(f"utils.py: Database connection error to vehicles.db{path_info}: {e}", exc_info=True)
        raise Exception(f"utils.py: Failed to connect to vehicles database. Error: {str(e)}")

def generate_complaint_number():
    try:
        conn = get_vehicles_db_connection_for_utils() # Use the new connection for vehicles.db
        cursor = conn.cursor()
        current_year_short = datetime.now().strftime('%y')  # e.g., "25"

        # Fetch the highest complaint_sequence for the current year
        cursor.execute(
            "SELECT MAX(complaint_sequence) FROM vehicles WHERE complaint_year = ?",
            (current_year_short,)
        )
        result = cursor.fetchone()

        if result and result[0] is not None:
            # Increment the existing sequence for the current year
            next_sequence = int(result[0]) + 1
        else:
            # No records for this year yet, or complaint_sequence was NULL/empty, so start at 1
            next_sequence = 1
        
        conn.close()
        
        # Format: ITXXXX-YY (e.g., IT0001-25, IT0104-25)
        complaint_number_str = f"IT{next_sequence:04d}-{current_year_short}"
        logging.info(f"Generated complaint number: {complaint_number_str}, sequence: {next_sequence}, year: {current_year_short}")
        return complaint_number_str, next_sequence, current_year_short
    except Exception as e:
        current_year_short_fallback = datetime.now().strftime('%y')
        logging.error(f"Error generating complaint number: {e}", exc_info=True) # MODIFIED: Added exc_info=True
        # Fallback in case of error; sequence 0 indicates an issue.
        return f"ITERR0000-{current_year_short_fallback}", 0, current_year_short_fallback

def ensure_logs_table_exists():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('CREATE TABLE IF NOT EXISTS logs (id INTEGER PRIMARY KEY AUTOINCREMENT, action_type TEXT, vehicle_id TEXT, details TEXT, timestamp TEXT)')
        
        # Create user_logs table if it doesn't exist
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            username TEXT NOT NULL,
            action_type TEXT NOT NULL,
            details TEXT
        )
        ''')
        
        conn.commit()
        conn.close()
    except Exception as e:
        logging.error(f"Logs table error: {e}")

def log_action(action_type, user_id, details):
    """
    Log an action in the system.
    
    Args:
        action_type (str): Type of action (UPDATE, INSERT, etc.)
        user_id (str): User who performed the action
        details (str): Details about the action
    """
    ensure_logs_table_exists()
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute(
            "INSERT INTO logs (action_type, vehicle_id, details, timestamp) VALUES (?, ?, ?, ?)",
            (action_type, user_id, details, timestamp)
        )
        cursor.execute(
            "INSERT INTO user_logs (timestamp, username, action_type, details) VALUES (?, ?, ?, ?)",
            (timestamp, user_id, action_type, details)
        )
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
        'Ready_Auction': 'Ready for Auction',
        'Ready_Scrap': 'Ready for Scrap',
        'Auction': 'Auction',
        'Scrapped': 'Scrapped',
        'Released': 'Released',
        'Completed': 'Released',
        'TOP Generated': 'TOP Generated',
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
    """Calculate the next auction date based on ad placement date."""
    try:
        if ad_placement_date and isinstance(ad_placement_date, str):
            ad_date = datetime.strptime(ad_placement_date, '%Y-%m-%d')
        elif isinstance(ad_placement_date, datetime):
            ad_date = ad_placement_date
        else:
            ad_date = datetime.now()
        # Auctions are held on Mondays
        days_to_monday = (7 - ad_date.weekday()) % 7
        if days_to_monday < 3:
            days_to_monday += 7
        return ad_date + timedelta(days=days_to_monday)
    except Exception as e:
        logging.error(f"Error calculating next auction date: {e}")
        return datetime.now() + timedelta(days=7)

def calculate_newspaper_ad_date(auction_date):
    if isinstance(auction_date, str):
        auction_date = datetime.strptime(auction_date, '%Y-%m-%d').date()
    
    # Ads must be placed at least 5 days before auction, preferably on a Wednesday
    # for Sunday paper publication
    target_date = auction_date - timedelta(days=5)
    
    # Find the previous Wednesday (day 2)
    days_to_subtract = (target_date.weekday() - 2) % 7
    ad_date = target_date - timedelta(days=days_to_subtract)
    
    # Make sure the ad date is at least 5 days before the auction
    if (auction_date - ad_date).days < 5:
        ad_date = ad_date - timedelta(days=7)  # Go back another week
    
    return ad_date

# Update this function in your utils.py file
def get_status_filter(status_type):
    """
    Convert frontend status types to backend status filters
    This function handles the conversion between frontend status naming conventions
    (with underscores) to backend status naming (with spaces)
    """
    if not status_type or status_type == 'all':
        return '', []

    # First convert any underscored status types to spaced format
    if status_type == 'TOP_Generated':
        status_type = 'TOP Generated'
    elif status_type == 'Ready_for_Auction':
        status_type = 'Ready for Auction'
    elif status_type == 'Ready_for_Scrap':
        status_type = 'Ready for Scrap'
    elif status_type == 'Ready_Auction':  # Handle old format
        status_type = 'Ready for Auction'
    elif status_type == 'Ready_Scrap':    # Handle old format  
        status_type = 'Ready for Scrap'
        
    # Log the status type for debugging
    logging.info(f"Status filter requested for: {status_type}")
    
    # Standard status mappings
    filters = {
        'New': ['New'],
        'TOP Generated': ['TOP Generated'],
        'Ready for Auction': ['Ready for Auction'],
        'Ready for Scrap': ['Ready for Scrap'],
        'Auction': ['Auction'],
        'Completed': ['Released', 'Scrapped', 'Auctioned', 'Transferred']
    }
    
    # Backward compatibility mappings
    backward_compat = {
        'Ready': ['Ready for Auction', 'Ready for Scrap'],
        'Scheduled': ['Scheduled for Release']
    }
    
    # Return the appropriate filter list
    return filters.get(status_type, backward_compat.get(status_type, [status_type]))

def safe_parse_date(date_str):
    """Safely parse a date string, returning None if invalid"""
    if not date_str or date_str == 'N/A':
        return None
    
    # Try ISO format YYYY-MM-DD
    try:
        return datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        pass
    # Try full format MM/DD/YYYY
    try:
        return datetime.strptime(date_str, '%m/%d/%Y').date()
    except ValueError:
        pass
    # Try short format MM/DD assuming current year
    parts = date_str.split('/')
    if len(parts) == 2:
        try:
            month, day = map(int, parts)
            current_year = datetime.now().year
            return date(current_year, month, day)
        except Exception:
            pass
    # Could not parse date
    return None

def send_email_notification(to_email, subject, body, attachment_path=None):
    """Send an email notification with optional attachment"""
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_SETTINGS['from_email']
        msg['To'] = to_email
        msg['Subject'] = subject
        
        # Attach the message body
        msg.attach(MIMEText(body, 'html'))
        
        # Attach the file if provided
        if attachment_path and os.path.exists(attachment_path):
            with open(attachment_path, 'rb') as file:
                part = MIMEApplication(file.read(), Name=os.path.basename(attachment_path))
                part['Content-Disposition'] = f'attachment; filename="{os.path.basename(attachment_path)}"'
                msg.attach(part)
        
        # Connect to the server and send
        with smtplib.SMTP(EMAIL_SETTINGS['smtp_server'], EMAIL_SETTINGS['smtp_port']) as server:
            server.starttls()
            server.login(EMAIL_SETTINGS['username'], EMAIL_SETTINGS['password'])
            server.send_message(msg)
        
        logging.info(f"Email sent to {to_email}: {subject}")
        return True, "Email sent successfully"
    except Exception as e:
        logging.error(f"Email sending error: {e}")
        return False, str(e)

def send_sms_notification(phone_number, message):
    """Send an SMS notification using API"""
    try:
        # This is a placeholder - replace with your actual SMS API provider
        # Example using Twilio-like API
        url = "https://api.yoursmsprovider.com/send"
        payload = {
            'api_key': SMS_SETTINGS['api_key'],
            'from': SMS_SETTINGS['from_number'],
            'to': phone_number,
            'message': message
        }
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            logging.info(f"SMS sent to {phone_number}")
            return True, "SMS sent successfully"
        else:
            logging.error(f"SMS error: {response.status_code} - {response.text}")
            return False, f"Error: {response.status_code}"
    except Exception as e:
        logging.error(f"SMS sending error: {e}")
        return False, str(e)

def send_fax_notification(fax_number, message, attachment_path=None):
    """Send a fax notification using API"""
    try:
        # This is a placeholder - replace with your actual fax API provider
        # Example using generic fax API
        url = "https://api.yourfaxprovider.com/send"
        
        files = {}
        if attachment_path and os.path.exists(attachment_path):
            files = {'file': open(attachment_path, 'rb')}
            
        payload = {
            'api_key': 'your-fax-api-key',
            'to': fax_number,
            'message': message
        }
        
        response = requests.post(url, data=payload, files=files)
        if response.status_code == 200:
            logging.info(f"Fax sent to {fax_number}")
            return True, "Fax sent successfully"
        else:
            logging.error(f"Fax error: {response.status_code} - {response.text}")
            return False, f"Error: {response.status_code}"
    except Exception as e:
        logging.error(f"Fax sending error: {e}")
        return False, str(e)

def determine_jurisdiction(address):
    """Determine jurisdiction based on address using geocoding."""
    if not address or address == 'N/A':
        return 'Unknown'
    try:
        geolocator = Nominatim(user_agent="iTow_Manager")
        address_clean = re.sub(r'\s*\(.*?\)', '', address).strip()
        search_address = f"{address_clean}, Genesee County, MI"
        for _ in range(3):  # Retry up to 3 times
            try:
                location = geolocator.geocode(search_address, timeout=10)
                if location and 'address' in location.raw:
                    addr = location.raw['address']
                    county = addr.get('county', '')
                    if 'Genesee' not in county:
                        return 'Out of County'
                    jurisdiction = addr.get('township', addr.get('city', 'Unknown'))
                    return jurisdiction.replace(" Charter Township", " Township") if jurisdiction else 'Unknown'
            except GeocoderTimedOut:
                logging.warning("Geocoding timed out, retrying...")
                time.sleep(2)
        return 'Unknown'
    except Exception as e:
        logging.error(f"Geocoding error: {e}")
        return 'Unknown'

def generate_certified_mail_number():
    """Generate a unique certified mail tracking number"""
    prefix = "9407"  # Standard USPS prefix
    # 16 digits total, 4 are prefix, so need 12 more
    random_digits = ''.join(random.choices(string.digits, k=12))
    return f"{prefix}{random_digits}"

def calculate_storage_fees(tow_date, daily_rate=25.00):
    """Calculate storage fees based on tow date."""
    try:
        if isinstance(tow_date, str):
            tow_date = datetime.strptime(tow_date, '%Y-%m-%d').date()
        elif hasattr(tow_date, 'date'):  # Check if it's a datetime object
            tow_date = tow_date.date()
        # If it's already a date object, use it directly
            
        today = datetime.now().date()
        days = (today - tow_date).days
        return max(0, days * daily_rate), days
    except Exception as e:
        logging.error(f"Error calculating storage fees: {e}")
        return 0, 0

def generate_confirmation_code():
    """Generate a short confirmation code for vehicle releases"""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

def validate_vin(vin):
    """Validate a vehicle identification number (VIN)"""
    if not vin or vin == 'N/A':
        return False
        
    # Basic validation: 17 characters, no I, O, Q
    vin = vin.upper()
    if len(vin) != 17:
        return False
        
    if any(c in "IOQ" for c in vin):
        return False
        
    # Check for valid characters (alphanumeric except I, O, Q)
    valid_chars = set("ABCDEFGHJKLMNPRSTUVWXYZ1234567890")
    if not all(c in valid_chars for c in vin):
        return False
        
    return True

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
            # Redemption period is 20 days for property recovery
            redemption_date = datetime.now() + timedelta(days=20)
            update_fields['days_until_next_step'] = 20
            update_fields['redemption_end_date'] = redemption_date.strftime('%Y-%m-%d')
        
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
                try:
                    sale_amount = float(update_fields['sale_amount'])
                    fees = float(update_fields['fees'])
                    update_fields['net_proceeds'] = sale_amount - fees
                except (ValueError, TypeError):
                    update_fields['net_proceeds'] = 0
        
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

def is_valid_email(email):
    """Validate an email address"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

def is_valid_phone(phone):
    """Validate a phone number"""
    # Remove any non-digit characters
    phone = re.sub(r'\D', '', phone)
    # Check if we have 10 or 11 digits (with or without country code)
    return len(phone) in (10, 11)

def format_phone(phone):
    """Format a phone number as (XXX) XXX-XXXX"""
    # Remove any non-digit characters
    phone = re.sub(r'\D', '', phone)
    
    if len(phone) == 10:
        return f"({phone[:3]}) {phone[3:6]}-{phone[6:]}"
    elif len(phone) == 11:
        return f"({phone[1:4]}) {phone[4:7]}-{phone[7:]}"
    else:
        return phone

def format_currency(amount):
    """Format a number as currency: $X,XXX.XX"""
    try:
        return "${:,.2f}".format(float(amount))
    except (ValueError, TypeError):
        return "$0.00"

def get_vehicle_description(vehicle_data):
    """Get a formatted vehicle description"""
    parts = []
    
    if vehicle_data.get('year') and vehicle_data['year'] != 'N/A':
        parts.append(vehicle_data['year'])
    
    if vehicle_data.get('color') and vehicle_data['color'] != 'N/A':
        parts.append(vehicle_data['color'])
    
    if vehicle_data.get('make') and vehicle_data['make'] != 'N/A':
        parts.append(vehicle_data['make'])
    
    if vehicle_data.get('model') and vehicle_data['model'] != 'N/A':
        parts.append(vehicle_data['model'])
    
    if not parts:
        return "Unknown Vehicle"
        
    return " ".join(parts)

def map_field_names(data):
    """Map alternative field names to the actual database column names"""
    field_mapping = {
        'requested_by': 'requestor'
    }
    
    result = data.copy()
    for alt_name, db_name in field_mapping.items():
        if alt_name in data:
            result[db_name] = data[alt_name]
            del result[alt_name]
    
    return result

def setup_logging():
    """Configure application logging"""
    log_dir = 'logs'
    os.makedirs(log_dir, exist_ok=True)
    
    log_file = os.path.join(log_dir, f"itow_{datetime.now().strftime('%Y%m%d')}.log")
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    
    # Log startup message
    logging.info("===== iTow Impound Manager Started =====")

def get_notification_templates():
    """Get templates for different notification types"""
    return {
        'TOP': {
            'subject': 'Private Property Impound Notification - {complaint_number}',
            'body': """
                <html>
                <body>
                <h2>Private Property Impound Notification</h2>
                <p>This is notification of a vehicle removal off of private property per MCL 257.252a(9).</p>
                <p><strong>Complaint #:</strong> {complaint_number}</p>
                <p><strong>Date of Tow:</strong> {tow_date}</p>
                <p><strong>Vehicle Description:</strong> {vehicle_description}</p>
                <p><strong>VIN:</strong> {vin}</p>
                <p><strong>Plate:</strong> {plate} ({state})</p>
                <p>Please see attached TOP form for complete details.</p>
                <p>Sincerely,<br>iTow Management</p>
                </body>
                </html>
            """
        },
        'Auction_Ad': {
            'subject': 'Vehicle Auction Advertisement - {complaint_number}',
            'body': """
                <html>
                <body>
                <h2>Vehicle Auction Advertisement</h2>
                <p>Please publish the following vehicle auction notice in your newspaper:</p>
                <p><strong>Publication Date:</strong> {ad_placement_date}</p>
                <p><strong>Auction Date:</strong> {auction_date}</p>
                <hr>
                <h3>ABANDONED VEHICLE AUCTION</h3>
                <p>The following vehicles will be sold at public auction on {auction_date} at 10:00 AM at iTow, 205 W Johnson St, Clio, MI 48420:</p>
                <p>{year} {make} {model}, VIN: {vin}, Complaint #: {complaint_number}</p>
                <hr>
                <p>Please confirm receipt and publication date.</p>
                <p>Sincerely,<br>iTow Management</p>
                </body>
                </html>
            """
        },
        'Release_Notice': {
            'subject': 'Vehicle Release Notification - {complaint_number}',
            'body': """
                <html>
                <body>
                <h2>Vehicle Release Notification</h2>
                <p>This notification confirms the release of the following vehicle:</p>
                <p><strong>Complaint #:</strong> {complaint_number}</p>
                <p><strong>Vehicle Description:</strong> {vehicle_description}</p>
                <p><strong>VIN:</strong> {vin}</p>
                <p><strong>Release Date:</strong> {release_date}</p>
                <p><strong>Release Reason:</strong> {release_reason}</p>
                <p><strong>Released To:</strong> {recipient}</p>
                <p>Please see attached release form for complete details.</p>
                <p>Sincerely,<br>iTow Management</p>
                </body>
                </html>
            """
        }
    }

def get_element_value_by_css(driver, css_selector):
    """Get element value with fallback"""
    try:
        element = WebDriverWait(driver, 3).until(EC.presence_of_element_located((By.CSS_SELECTOR, css_selector)))
        value = driver.execute_script("return arguments[0].value;", element) or element.get_attribute("value")
        return value.strip() if value else ""
    except Exception:
        # Don't log this as it's too verbose for selectors that won't match
        return ""

def get_select_value_by_css(driver, css_selector):
    """Get selected option text"""
    try:
        select = WebDriverWait(driver, 3).until(EC.presence_of_element_located((By.CSS_SELECTOR, css_selector)))
        value = driver.execute_script("return arguments[0].options[arguments[0].selectedIndex]?.text || '';", select)
        return value.strip() if value else ""
    except:
        return ""

def extract_datetime_fields(driver, vehicle_data):
    """Extract date and time with multiple fallback methods"""
    # Define various selectors for different field types
    date_selectors = ["input#x-impound-date-date", "input[id*='impound'][id*='date']", "input.datepicker", "input[name*='date']", "#serviceDate"]
    time_selectors = ["input#x-impound-date-time", "input[id*='impound'][id*='time']", "input.timepicker", "input[name*='time']", "#serviceTime"]
    po_selectors = ["input#poNumber", "input[id*='poNumber']", "input[name*='poNumber']", "input[placeholder*='PO']", "input[placeholder*='po']"]

    # Get tow date
    date_value = ""
    for selector in date_selectors:
        date_value = get_element_value_by_css(driver, selector)
        if date_value:
            logging.info(f"Found date: {date_value} with {selector}")
            break

    # Get tow time - improved to ensure we get this value
    time_value = ""
    for selector in time_selectors:
        time_value = get_element_value_by_css(driver, selector)
        if time_value:
            logging.info(f"Found time: {time_value} with {selector}")
            break
    
    # Try additional time selectors if not found
    if not time_value:
        # Try JavaScript approach to find time input
        try:
            time_value = driver.execute_script("""
                return Array.from(document.querySelectorAll('input')).find(i => 
                    (i.placeholder && i.placeholder.toLowerCase().includes('time')) || 
                    (i.id && i.id.toLowerCase().includes('time')) ||
                    (i.name && i.name.toLowerCase().includes('time'))
                )?.value || '';
            """)
            if time_value:
                logging.info(f"Found time using JavaScript: {time_value}")
        except Exception as e:
            logging.warning(f"JavaScript time extraction error: {e}")
    
    # If still no time value, use current time as fallback
    if not time_value:
        time_value = datetime.now().strftime('%H:%M')
        logging.info(f"Using current time as fallback: {time_value}")
    
    # Get PO number for complaint number
    po_value = ""
    for selector in po_selectors:
        po_value = get_element_value_by_css(driver, selector)
        if po_value:
            logging.info(f"Found PO#: {po_value} with {selector}")
            break
    
    # Try additional PO selectors if not found
    if not po_value:
        try:
            # Try JavaScript approach to find PO input
            po_value = driver.execute_script("""
                return Array.from(document.querySelectorAll('input')).find(i => 
                    (i.placeholder && i.placeholder.toLowerCase().includes('po')) || 
                    (i.id && i.id.toLowerCase().includes('po')) ||
                    (i.name && i.name.toLowerCase().includes('po'))
                )?.value || '';
            """)
            if po_value:
                logging.info(f"Found PO# using JavaScript: {po_value}")
                
            # If still not found, try to look for a field with 'reference' or 'ref' in its attributes
            if not po_value:
                po_value = driver.execute_script("""
                    return Array.from(document.querySelectorAll('input')).find(i => 
                        (i.placeholder && (i.placeholder.toLowerCase().includes('reference') || i.placeholder.toLowerCase().includes('ref'))) || 
                        (i.id && (i.id.toLowerCase().includes('reference') || i.id.toLowerCase().includes('ref'))) ||
                        (i.name && (i.name.toLowerCase().includes('reference') || i.name.toLowerCase().includes('ref')))
                    )?.value || '';
                """)
                if po_value:
                    logging.info(f"Found PO# as reference number using JavaScript: {po_value}")
        except Exception as e:
            logging.warning(f"JavaScript PO extraction error: {e}")

    # Update vehicle data
    if date_value:
        vehicle_data['tow_date'] = date_value
        
        # Format the date properly if found
        try:
            if '/' in date_value:
                # MM/DD/YYYY format
                tow_date = datetime.strptime(date_value, '%m/%d/%Y')
                vehicle_data['tow_date'] = tow_date.strftime('%Y-%m-%d')
            else:
                # Try another common format
                tow_date = datetime.strptime(date_value, '%Y-%m-%d')
                # Already in the right format
        except Exception as e:
            logging.warning(f"Date format conversion error: {e}")
            # If we can't parse it, leave it as is
            
    if time_value:
        vehicle_data['tow_time'] = time_value
    
    if po_value:
        vehicle_data['complaint_number'] = po_value
    
    return vehicle_data

def generate_next_complaint_number(db_path="vehicles.db"):
    """
    Generates the next sequential complaint number in ITXXXX-YY format.
    Connects to the database, checks for an override, then finds the highest 
    sequence for the current year, increments it, and returns the new 
    complaint number, sequence, and year.
    """
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        current_year_short = datetime.now().strftime('%y')  # e.g., "25"

        # Check for an override for the current year
        cursor.execute(
            "SELECT next_sequence_number FROM complaint_sequence_override WHERE year = ?",
            (current_year_short,)
        )
        override_result = cursor.fetchone()

        if override_result:
            next_seq_num = override_result[0]
            # Optionally, one might want to remove the override after using it,
            # or have a flag to indicate it's a one-time use.
            # For now, we'll assume it stays until changed/deleted.
            logging.info(f"Using overridden next complaint sequence {next_seq_num} for year {current_year_short}")
        else:
            # No override, proceed with normal sequence generation
            query = f"SELECT complaint_number FROM vehicles WHERE complaint_number LIKE 'IT____-{current_year_short}'"
            cursor.execute(query)
            all_complaints_for_year = cursor.fetchall()

            max_seq = 0
            if all_complaints_for_year:
                for row in all_complaints_for_year:
                    cn = row[0]
                    if cn and len(cn) == 9 and cn.startswith("IT") and cn[6] == '-':
                        try:
                            seq_part_str = cn[2:6]
                            seq_part_int = int(seq_part_str)
                            if seq_part_int > max_seq:
                                max_seq = seq_part_int
                        except ValueError:
                            logging.warning(f"Could not parse sequence from complaint number: {cn} in utils.generate_next_complaint_number")
                            continue
            next_seq_num = max_seq + 1
        
        new_complaint_number = f"IT{next_seq_num:04d}-{current_year_short}"
        logging.info(f"Generated next complaint number: {new_complaint_number}, sequence: {next_seq_num}, year: {current_year_short}")
        # Return all three components
        return new_complaint_number, next_seq_num, current_year_short
        
    except sqlite3.Error as e:
        logging.error(f"Database error in generate_next_complaint_number: {e}")
        current_year_short_fallback = datetime.now().strftime('%y')
        # Fallback in case of error; sequence 0 indicates an issue.
        return f"ITERR0000-{current_year_short_fallback}", 0, current_year_short_fallback
    finally:
        if conn:
            conn.close()

def get_current_complaint_sequence_info(db_path="vehicles.db"):
    """
    Retrieves the current state of the complaint number sequence.
    Returns the next expected sequence number and the current year.
    Checks for overrides first.
    """
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        current_year_short = datetime.now().strftime('%y')

        # Check for an override for the current year
        cursor.execute(
            "SELECT next_sequence_number FROM complaint_sequence_override WHERE year = ?",
            (current_year_short,)
        )
        override_result = cursor.fetchone()

        if override_result:
            next_seq_num = override_result[0]
            is_overridden = True
        else:
            # No override, calculate next based on existing data
            query = f"SELECT complaint_number FROM vehicles WHERE complaint_number LIKE 'IT____-{current_year_short}'"
            cursor.execute(query)
            all_complaints_for_year = cursor.fetchall()
            max_seq = 0
            if all_complaints_for_year:
                for row in all_complaints_for_year:
                    cn = row[0]
                    if cn and len(cn) == 9 and cn.startswith("IT") and cn[6] == '-':
                        try:
                            seq_part_str = cn[2:6]
                            seq_part_int = int(seq_part_str)
                            if seq_part_int > max_seq:
                                max_seq = seq_part_int
                        except ValueError:
                            continue # Skip malformed ones
            next_seq_num = max_seq + 1
            is_overridden = False
        
        return {
            "next_sequence_number": next_seq_num,
            "current_year": current_year_short,
            "is_overridden": is_overridden
        }
    except sqlite3.Error as e:
        logging.error(f"Database error in get_current_complaint_sequence_info: {e}")
        return {
            "next_sequence_number": 0, # Indicate error
            "current_year": datetime.now().strftime('%y'),
            "is_overridden": False,
            "error": str(e)
        }
    finally:
        if conn:
            conn.close()

def set_complaint_sequence_override(next_sequence_number, year=None, db_path="vehicles.db"):
    """
    Sets or updates an override for the next complaint sequence number for a given year.
    If year is None, defaults to the current year.
    """
    conn = None
    if year is None:
        year = datetime.now().strftime('%y')
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Use INSERT OR REPLACE to either insert a new override or update an existing one
        cursor.execute(
            "INSERT OR REPLACE INTO complaint_sequence_override (year, next_sequence_number) VALUES (?, ?)",
            (year, next_sequence_number)
        )
        conn.commit()
        logging.info(f"Set complaint sequence override for year {year} to {next_sequence_number}")
        return True, f"Next complaint number for year {year} set to IT{next_sequence_number:04d}-{year}."
    except sqlite3.Error as e:
        logging.error(f"Database error in set_complaint_sequence_override: {e}")
        return False, str(e)
    finally:
        if conn:
            conn.close()

def clear_complaint_sequence_override(year=None, db_path="vehicles.db"):
    """
    Clears an override for the complaint sequence number for a given year.
    If year is None, defaults to the current year.
    """
    conn = None
    if year is None:
        year = datetime.now().strftime('%y')
        
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM complaint_sequence_override WHERE year = ?", (year,))
        conn.commit()
        
        if cursor.rowcount > 0:
            logging.info(f"Cleared complaint sequence override for year {year}.")
            return True, f"Override for year {year} cleared. System will use standard sequence."
        else:
            logging.info(f"No complaint sequence override found for year {year} to clear.")
            return True, f"No override was set for year {year}."
            
    except sqlite3.Error as e:
        logging.error(f"Database error in clear_complaint_sequence_override: {e}")
        return False, str(e)
    finally:
        if conn:
            conn.close()

def get_status_list_for_filter(filter_name):
    """
    Returns a list of vehicle statuses based on a general filter name.
    """
    if filter_name == 'active':
        return ['New', 'TOP Generated', 'Ready for Auction', 'Ready for Scrap']
    elif filter_name == 'completed':
        return ['Released', 'Auctioned', 'Scrapped', 'Transferred']
    # If a specific status is passed (e.g., "New"), the caller can handle it directly.
    # This function is for aggregate terms like "active" or "completed".
    return None

# Ensure all functions are defined above this line if they are to be used by others.
