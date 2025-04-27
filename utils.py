from datetime import datetime, timedelta
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

# Configure email settings - replace with your own
EMAIL_SETTINGS = {
    'smtp_server': 'smtp.gmail.com',
    'smtp_port': 587,
    'username': 'your-email@gmail.com',
    'password': 'your-app-password',
    'from_email': 'iTow Vehicle Management <your-email@gmail.com>'
}

# Configure SMS settings - replace with your own
SMS_SETTINGS = {
    'api_key': 'your-sms-api-key',
    'from_number': 'your-from-number'
}

def get_db_connection():
    conn = sqlite3.connect('database.db')  # Changed from vehicles.db to database.db to match the auth system
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
        
        # Also log to user_logs if the table exists
        try:
            cursor.execute(
                "INSERT INTO user_logs (timestamp, username, action_type, details) VALUES (?, ?, ?, ?)",
                (timestamp, user_id, action_type, details)
            )
        except:
            # If user_logs table doesn't exist yet, that's okay
            pass
            
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
    if ad_placement_date and ad_placement_date != 'N/A':
        if isinstance(ad_placement_date, str):
            try:
                ad_date = datetime.strptime(ad_placement_date, '%Y-%m-%d').date()
            except ValueError:
                return calculate_next_auction_date(None)  # Fall back to default calculation
        else:
            ad_date = ad_placement_date
        min_auction_date = ad_date + timedelta(days=5)
        days_to_monday = (7 - min_auction_date.weekday()) % 7
        if days_to_monday == 0:
            days_to_monday = 7
        return min_auction_date + timedelta(days=days_to_monday)
    else:
        # If no ad date provided, schedule next auction on the next Monday, at least 2 weeks out
        days_to_monday = (7 - today.weekday()) % 7 or 7  # If today is Monday, go to next Monday
        # Add an additional week to ensure enough time for ad placement
        return today + timedelta(days=days_to_monday + 7)

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

def get_status_filter(status_type):
    filters = {
        'New': ['New'],
        'TOP_Generated': ['TOP Generated'],
        'TR52_Ready': ['TR52 Ready'],
        'Ready_Auction': ['Ready for Auction'],
        'Ready_Scrap': ['Ready for Scrap'],
        'Auction': ['Auction'],
        'Completed': ['Released', 'Scrapped', 'Auctioned', 'Transferred']
    }
    backward_compat = {
        'Ready': ['TR52 Ready', 'Ready for Auction', 'Ready for Scrap'],
        'Scheduled': ['Scheduled for Release']
    }
    return filters.get(status_type, backward_compat.get(status_type, []))

def calculate_tr52_countdown(top_sent_date):
    if not top_sent_date or top_sent_date == 'N/A':
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
    """Determine jurisdiction based on address using geocoding"""
    if not address or address == 'N/A':
        return 'Unknown'
        
    try:
        # Create a geocoder with custom user agent
        geolocator = Nominatim(user_agent="iTow_Manager")
        
        # Clean up the address
        address_clean = re.sub(r'\s*\(.*?\)', '', address).strip()
        
        # Add Genesee County, MI to improve accuracy
        search_address = f"{address_clean}, Genesee County, MI"
        
        # Try geocoding with retry logic
        for attempt in range(3):
            try:
                location = geolocator.geocode(search_address, exactly_one=True, timeout=10, addressdetails=True)
                break
            except (GeocoderTimedOut, GeocoderServiceError):
                if attempt < 2:
                    time.sleep(1)
                    continue
                return 'Unknown'
        
        if not location or 'address' not in location.raw:
            return 'Unknown'
            
        # Extract address components
        addr = location.raw['address']
        
        # Verify we're in Genesee County
        county = addr.get('county', '')
        if 'Genesee' not in county and 'genesee' not in county.lower():
            return 'Out of County'
            
        # Try various fields to determine jurisdiction
        jurisdiction = addr.get('township', addr.get('city', addr.get('municipality', 'Unknown')))
        
        # Clean up the jurisdiction name
        if jurisdiction:
            jurisdiction = jurisdiction.replace(" Charter Township", " Township")
            
        return jurisdiction
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
    """Calculate storage fees based on tow date and daily rate"""
    if not tow_date or tow_date == 'N/A':
        return 0.00, 0
        
    try:
        if isinstance(tow_date, str):
            tow_date = datetime.strptime(tow_date, '%Y-%m-%d').date()
            
        today = datetime.now().date()
        days = (today - tow_date).days
        
        # Minimum 1 day charge
        days = max(1, days)
        
        # Calculate the fee
        fee = days * daily_rate
        
        return round(fee, 2), days
    except Exception as e:
        logging.error(f"Storage fee calculation error: {e}")
        return 0.00, 0

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

def is_eligible_for_tr208(vehicle_data):
    """
    Determine if a vehicle is eligible for TR208 (scrap) processing
    based on Michigan requirements:
    1. 7+ years old
    2. Inoperable
    3. Extensively damaged
    
    Returns: (bool, dict) - eligible status and reasons
    """
    eligible = True
    reasons = {}
    
    # Check vehicle age (7+ years old)
    current_year = datetime.now().year
    try:
        if vehicle_data.get('year') and vehicle_data['year'] != 'N/A':
            vehicle_year = int(vehicle_data['year'])
            age = current_year - vehicle_year
            eligible = eligible and age >= 7
            reasons['age'] = f"{age} years old" if age >= 7 else f"Only {age} years old (must be 7+)"
        else:
            eligible = False
            reasons['age'] = "Unknown year"
    except (ValueError, TypeError):
        eligible = False
        reasons['age'] = f"Invalid year format: {vehicle_data.get('year')}"
    
    # Check operability status (assume stored in a field like 'inoperable' or 'condition')
    if vehicle_data.get('inoperable') == 1 or vehicle_data.get('condition') == 'Inoperable':
        reasons['operable'] = "Inoperable"
    else:
        eligible = False
        reasons['operable'] = "Vehicle appears operable or status unknown"
    
    # Check damage extent (assume stored in a field like 'damage' or 'condition_notes')
    if vehicle_data.get('damage') == 'Extensive' or 'extensive damage' in str(vehicle_data.get('condition_notes', '')).lower():
        reasons['damage'] = "Extensively damaged"
    else:
        eligible = False
        reasons['damage'] = "Not extensively damaged or damage status unknown"
    
    return eligible, reasons

def generate_tr208_form(vehicle_data, output_path):
    """
    Generate a TR208 form for scrapping a vehicle
    
    Args:
        vehicle_data (dict): Vehicle information
        output_path (str): Path to save the PDF
        
    Returns:
        (bool, str): Success status and error message if any
    """
    from generator import PDFGenerator  # Assuming PDFGenerator is your PDF generation class
    
    try:
        pdf_gen = PDFGenerator()
        # You may need to customize the PDF generation for TR208
        # This assumes your PDFGenerator class has a method for TR208 forms
        success, error = pdf_gen.generate_tr208_form(vehicle_data, output_path)
        
        if success:
            # Log the action
            log_action("GENERATE_TR208", vehicle_data['towbook_call_number'], "TR208 form generated for scrap vehicle")
            
        return success, error
    except Exception as e:
        logging.error(f"Error generating TR208: {e}")
        return False, str(e)

def calculate_tr208_timeline(tow_date):
    """
    Calculate the TR208 timeline (27 days from tow)
    
    Args:
        tow_date (str): Tow date in YYYY-MM-DD format
        
    Returns:
        (datetime.date): Date when TR208 can be processed
    """
    if isinstance(tow_date, str):
        tow_date = datetime.strptime(tow_date, '%Y-%m-%d').date()
    
    # 27 days from tow (7 for police notification + 20 for owner redemption)
    return tow_date + timedelta(days=27)

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
        'TR52': {
            'subject': 'TR52 Notification - {complaint_number}',
            'body': """
                <html>
                <body>
                <h2>TR52 Notification</h2>
                <p>The 20-day redemption period has expired for the following vehicle:</p>
                <p><strong>Complaint #:</strong> {complaint_number}</p>
                <p><strong>Date of Tow:</strong> {tow_date}</p>
                <p><strong>TOP Sent Date:</strong> {top_form_sent_date}</p>
                <p><strong>Vehicle Description:</strong> {vehicle_description}</p>
                <p><strong>VIN:</strong> {vin}</p>
                <p><strong>Plate:</strong> {plate} ({state})</p>
                <p>The vehicle is now eligible for TR52 processing.</p>
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