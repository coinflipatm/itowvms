import os # Added: for path operations and environment variables
import base64 # Added: for placeholder logo
import logging # Added: for logging
import socket # Added: for is_port_in_use
from flask import Flask, render_template, send_file, request, jsonify, redirect, url_for
from database import (init_db, get_vehicles_by_status, update_vehicle_status,
                      update_vehicle, insert_vehicle, get_db_connection, check_and_update_statuses, 
                       get_pending_notifications,
                      mark_notification_sent, get_contact_by_jurisdiction, save_contact, get_contacts,
                      get_vehicles, safe_parse_date, add_contact_explicit, update_contact_explicit,
                      delete_contact_explicit, get_contact_by_id) # Added new contact functions
from generator import PDFGenerator
from utils import (generate_next_complaint_number, release_vehicle, log_action, # Changed from generate_complaint_number
                   ensure_logs_table_exists, setup_logging, get_status_filter, calculate_newspaper_ad_date,
                   calculate_storage_fees, determine_jurisdiction, send_email_notification, 
                   send_sms_notification, send_fax_notification, is_valid_email, is_valid_phone,
                   generate_certified_mail_number, is_eligible_for_tr208, calculate_tr208_timeline)
from flask_login import login_required, current_user
from auth import auth_bp, login_manager, init_auth_db, User
from datetime import datetime, timedelta, date # Added date here
from scraper import TowBookScraper
import threading
import os
import logging
import time
import socket
import json
import base64 # Add this import
from werkzeug.security import safe_join
from werkzeug.utils import secure_filename
from io import StringIO, BytesIO
import csv
import re
import sqlite3 # Added for handling database specific errors like IntegrityError

# Configure logging
setup_logging()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev_key_change_this_in_production')

# Force the use of vehicles.db as the main database
database_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'vehicles.db')
os.environ['DATABASE_URL'] = database_path
logging.info(f"Using database at: {database_path}")

# Initialize Flask-Login
login_manager.init_app(app)
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'

# Register authentication blueprint
app.register_blueprint(auth_bp)

# Import and register the API blueprint
from api_routes import register_api_routes
register_api_routes(app)

# Initialize components that require app context
with app.app_context():
    # Log database information for debugging
    logging.info("Initializing application components...")
    logging.info(f"Database path from environment: {os.environ.get('DATABASE_URL')}")
    logging.info(f"Database exists: {os.path.exists(database_path)}")
    if os.path.exists(database_path):
        logging.info(f"Database size: {os.path.getsize(database_path)} bytes")
        
    # Initialize database and other components
    init_db()
    init_auth_db()
    ensure_logs_table_exists()

pdf_gen = PDFGenerator()

# Configure upload folders
UPLOAD_FOLDER = 'static/uploads/vehicle_photos'
DOCUMENT_FOLDER = 'static/uploads/documents'
GENERATED_FOLDER = 'static/generated_pdfs'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['DOCUMENT_FOLDER'] = DOCUMENT_FOLDER
app.config['GENERATED_FOLDER'] = GENERATED_FOLDER
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
ALLOWED_DOCUMENT_EXTENSIONS = {'pdf', 'doc', 'docx', 'txt'}

# Ensure folders exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(DOCUMENT_FOLDER, exist_ok=True)
os.makedirs(GENERATED_FOLDER, exist_ok=True)

# Add a default logo path to suppress warnings
LOGO_PATH = 'static/logo.png'
if not os.path.exists(LOGO_PATH):
    try:
        # Create a minimal 1x1 transparent PNG
        # PNG signature: \x89PNG\r\n\x1a\n
        # IHDR chunk: length (13), name (IHDR), width (1), height (1), bit depth (1), color type (0 - grayscale), compression (0), filter (0), interlace (0), CRC
        # IDAT chunk: length (10), name (IDAT), data (compressed pixel data - \x78\x9c\x63\x60\x00\x00\x01\x00\x01 - for a single black pixel, or use a transparent one), CRC
        # IEND chunk: length (0), name (IEND), CRC
        # A 1x1 transparent PNG, base64 encoded
        png_data = base64.b64decode(
            b'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII='
        )
        with open(LOGO_PATH, 'wb') as f:
            f.write(png_data) # Added missing f.write()
        logging.info(f"Created placeholder 1x1 transparent PNG at {LOGO_PATH}")
    except Exception as e:
        logging.error(f"Failed to create placeholder logo.png: {e}", exc_info=True)

# Ensure all helper functions are defined before routes that use them.

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def allowed_document(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_DOCUMENT_EXTENSIONS

def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0 # Changed pass to a basic check

def run_status_checks():
    while True:
        # This function needs a proper implementation or to be removed if not used.
        # For now, adding a small delay to prevent tight loop if ever run.
        # import time
        # time.sleep(60) # Example: sleep for 60 seconds
        pass

def _perform_top_generation(call_number, username):
    """
    Helper function to perform TOP form generation, database updates, and logging.
    Returns a tuple: (success, message, pdf_filename_or_error, vehicle_data, notification_id)
    """
    conn = None
    notification_id = None # Initialize notification_id
    pdf_filename = None    # Initialize pdf_filename
    vehicle_data = None    # Initialize vehicle_data
    success = False        # Initialize success
    message = ""           # Initialize message
    try:
        conn = get_db_connection()
        vehicle = conn.execute("SELECT * FROM vehicles WHERE towbook_call_number = ?", (call_number,)).fetchone()
        
        if not vehicle:
            return False, "Vehicle not found", None, None, None

        data = dict(vehicle)
        # Example: data['owner_name'] = data.get('owner_name', 'N/A') 
        # This should be done for all fields used by pdf_gen.generate_top_pdf
        
        is_tr208_eligible, _ = is_eligible_for_tr208(data)
        data['tr208_eligible'] = 1 if is_tr208_eligible else 0
                
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        pdf_filename = f"TOP_{call_number}_{timestamp}.pdf"
        pdf_path = os.path.join(app.config['GENERATED_FOLDER'], pdf_filename)
        os.makedirs(os.path.dirname(pdf_path), exist_ok=True)

        # pdf_gen.generate_top_pdf(pdf_path, data) # Ensure this is correctly implemented in PDFGenerator
        # update_vehicle_status(call_number, 'TOP Generated')
        # log_action('TOP Generated', call_number, username, details=f"Generated TOP form: {pdf_filename}")
            
        success = True
        message = "TOP form generated successfully."
        vehicle_data = data
            
    except Exception as e:
        logging.error(f"Error in _perform_top_generation for {call_number}: {e}", exc_info=True)
        message = f"Error generating TOP form: {e}"
        pdf_filename = str(e) 
    finally:
        if conn:
            conn.close()
    return success, message, pdf_filename, vehicle_data, notification_id

def _perform_tr52_generation(call_number, username):
    """
    Helper function to perform TR52 form generation, database updates, and logging.
    Returns a tuple: (success, message, pdf_filename_or_error, vehicle_data)
    """
    conn = None
    pdf_filename = None    # Initialize pdf_filename
    vehicle_data = None    # Initialize vehicle_data
    success = False        # Initialize success
    message = ""           # Initialize message
    try:
        conn = get_db_connection()
        vehicle = conn.execute("SELECT * FROM vehicles WHERE towbook_call_number = ?", (call_number,)).fetchone()
        if not vehicle:
            return False, "Vehicle not found", None, None
        
        data = dict(vehicle)
        # Populate data as needed for pdf_gen.generate_tr52_pdf
        
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        pdf_filename = f"TR52_{call_number}_{timestamp}.pdf"
        pdf_path = os.path.join(app.config['GENERATED_FOLDER'], pdf_filename)
        os.makedirs(os.path.dirname(pdf_path), exist_ok=True)

        # pdf_gen.generate_tr52_pdf(pdf_path, data) # Ensure this is correctly implemented
        # update_vehicle_status(call_number, 'TR52 Generated') # Or appropriate status
        # log_action('TR52 Generated', call_number, username, details=f"Generated TR52 form: {pdf_filename}")

        success = True
        message = "TR52 form generated successfully."
        vehicle_data = data
        
    except Exception as e:
        logging.error(f"Error in _perform_tr52_generation for {call_number}: {e}", exc_info=True)
        message = f"Error generating TR52 form: {e}"
        pdf_filename = str(e)
    finally:
        if conn:
            conn.close()
    return success, message, pdf_filename, vehicle_data

def _perform_tr208_generation(call_number, username):
    """
    Helper function to perform TR208 form generation, database updates, and logging.
    Returns a tuple: (success, message, pdf_filename_or_error, vehicle_data)
    """
    conn = None
    pdf_filename = None    # Initialize pdf_filename
    vehicle_data = None    # Initialize vehicle_data
    success = False        # Initialize success
    message = ""           # Initialize message
    try:
        conn = get_db_connection()
        vehicle = conn.execute("SELECT * FROM vehicles WHERE towbook_call_number = ?", (call_number,)).fetchone()
        if not vehicle:
            return False, "Vehicle not found", None, None

        data = dict(vehicle)
        # Populate data as needed for pdf_gen.generate_tr208_pdf
        
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        pdf_filename = f"TR208_{call_number}_{timestamp}.pdf"
        pdf_path = os.path.join(app.config['GENERATED_FOLDER'], pdf_filename)
        os.makedirs(os.path.dirname(pdf_path), exist_ok=True)

        # pdf_gen.generate_tr208_pdf(pdf_path, data) # Ensure this is correctly implemented
        # update_vehicle_status(call_number, 'TR208 Generated') # Or appropriate status
        # log_action('TR208 Generated', call_number, username, details=f"Generated TR208 form: {pdf_filename}")

        success = True
        message = "TR208 form generated successfully."
        vehicle_data = data
        
    except Exception as e:
        logging.error(f"Error in _perform_tr208_generation for {call_number}: {e}", exc_info=True)
        message = f"Error generating TR208 form: {e}"
        pdf_filename = str(e)
    finally:
        if conn:
            conn.close()
    return success, message, pdf_filename, vehicle_data

@app.route('/api/vehicles/add', methods=['POST'])
@login_required
def add_vehicle():
    try:
        data = request.json
        if not data:
            return jsonify({"error": "No data provided"}), 400
            
        # Pop optional flags before database insertion
        should_auto_top = data.pop('auto_top', False)
            
        # Validate required fields
        if not data.get('towbook_call_number'):
            return jsonify({"error": "Call number is required"}), 400
            
        if not data.get('status'):
            data['status'] = 'New'  # Default status
            
        # Generate complaint number if missing
        if 'complaint_number' not in data or not data['complaint_number'] or data['complaint_number'] == 'N/A':
            data['complaint_number'] = generate_next_complaint_number()
            
        # Detect jurisdiction if needed
        if data.get('location_from') and (not data.get('jurisdiction') or data['jurisdiction'] == 'detect'):
            data['jurisdiction'] = determine_jurisdiction(data['location_from'])
            
        # Handle missing photos gracefully
        if 'photo_paths' not in data or not data['photo_paths']:
            data['photo_paths'] = []
            
        # Add timestamp
        data['tow_date'] = data.get('tow_date') or datetime.now().strftime('%Y-%m-%d')
        data['last_updated'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
        # Insert vehicle into database
        success = False  # Initialize success flag
        try:
            vehicle_id = insert_vehicle(data)
            if vehicle_id:
                success = True
                log_action('Vehicle Added', data.get('towbook_call_number'), 
                           current_user.id if current_user else 'System', 
                           f"Vehicle added: {data.get('make')} {data.get('model')}")
        except Exception as e:
            return jsonify({"error": f"Database error: {str(e)}"}), 500
            
        if success:
            # Handle auto-TOP generation if requested
            if should_auto_top:
                try:
                    _perform_top_generation(data.get('towbook_call_number'), 
                                           current_user.id if current_user else 'System')
                except Exception as e:
                    logging.error(f"Auto-TOP generation failed: {e}", exc_info=True)
                    # Continue even if auto-TOP fails
                
            return jsonify({"success": True, "vehicle_id": vehicle_id, "message": "Vehicle added successfully"}), 201
        else:
            return jsonify({"error": "Failed to add vehicle for unknown reason"}), 500
            
    except Exception as e:
        logging.error(f"Error adding vehicle in app.py: {e}", exc_info=True)
        return jsonify({"error": f"Server error: {str(e)}"}), 500

@app.route('/api/generate-top/<call_number>', methods=['POST'])
@login_required
def generate_top(call_number):
    username = current_user.id if current_user else "System"
    success, message, pdf_filename_or_error, vehicle_data, notification_id = _perform_top_generation(call_number, username)
    if success:
        # Assuming the PDF was generated and saved by _perform_top_generation
        # The actual sending of the file might happen via a download link or another route
        return jsonify({
            "message": message, 
            "pdf_filename": pdf_filename_or_error, 
            "vehicle": vehicle_data,
            "notification_id": notification_id
        }), 200
    else:
        return jsonify({"error": message, "details": pdf_filename_or_error}), 500
    
@app.route('/api/generate-tr52/<call_number>', methods=['POST'])
@login_required
def generate_tr52_form_api(call_number):
    username = current_user.id if current_user else "System"
    success, message, pdf_filename_or_error, vehicle_data = _perform_tr52_generation(call_number, username)
    if success:
        return jsonify({
            "message": message, 
            "pdf_filename": pdf_filename_or_error, 
            "vehicle": vehicle_data
        }), 200
    else:
        return jsonify({"error": message, "details": pdf_filename_or_error}), 500
    
@app.route('/api/generate-tr208/<call_number>', methods=['POST'])
@login_required
def generate_tr208_form_api(call_number):
    username = current_user.id if current_user else "System"
    success, message, pdf_filename_or_error, vehicle_data = _perform_tr208_generation(call_number, username)
    if success:
        return jsonify({
            "message": message, 
            "pdf_filename": pdf_filename_or_error, 
            "vehicle": vehicle_data
        }), 200
    else:
        return jsonify({"error": message, "details": pdf_filename_or_error}), 500

@app.route('/')
def index():
    # The main page, usually renders index.html
    # You might want to pass some initial data to the template
    return render_template('index.html', current_user=current_user)
    

# Main API route for vehicle data
@app.route('/api/vehicles')
def api_get_vehicles():
    """Fetch vehicles based on status, sorting, and other filters"""
    try:
        status_filter = request.args.get('status', None)
        sort_column = request.args.get('sort', 'tow_date')
        sort_direction = request.args.get('direction', 'desc')
        include_archived = request.args.get('archived', '').lower() in ['true', '1', 'yes']

        logging.info(f"Fetching vehicles: status={status_filter}, sort={sort_column}, direction={sort_direction}, archived={include_archived}")

        # If status is 'all' or not provided, return all non-archived vehicles
        if not status_filter or status_filter == 'all':
            vehicles_data = get_vehicles('all', sort_column, sort_direction)
        elif status_filter in ['New', 'TOP_Generated', 'TR52_Ready', 'TR208_Ready', 
                               'Ready_for_Auction', 'Ready_for_Scrap']:
            vehicles_data = get_vehicles_by_status(status_filter, sort_column, sort_direction, include_archived)
        else:
            vehicles_data = get_vehicles(status_filter, sort_column, sort_direction)

        logging.info(f"Found {len(vehicles_data)} vehicles matching criteria")
        return jsonify(vehicles_data)
    except Exception as e:
        logging.error(f"Error fetching vehicles: {e}", exc_info=True)
        return jsonify({"error": f"Failed to fetch vehicles: {str(e)}"}), 500

if __name__ == "__main__":
    # Consider removing is_port_in_use check or making it more robust
    # if is_port_in_use(5001):
    #    logging.error("Port 5001 is already in use. Please choose a different port.")
    # else:
    app.run(host="0.0.0.0", port=5001, debug=True)