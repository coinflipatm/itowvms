import os # Added: for path operations and environment variables
import base64 # Added: for placeholder logo
import logging # Added: for logging
from flask import Flask, render_template, send_file, request, jsonify, redirect, url_for
from database import (init_db, get_vehicles_by_status, update_vehicle_status,
                      update_vehicle, update_vehicle_by_call_number, insert_vehicle, get_db_connection, check_and_update_statuses, 
                       get_pending_notifications,
                      mark_notification_sent, get_contact_by_jurisdiction, save_contact, get_contacts,
                      get_vehicles, safe_parse_date, add_contact_explicit, update_contact_explicit,
                      delete_contact_explicit, get_contact_by_id, get_vehicle_by_id, get_vehicle_by_call_number) # Added functions for call number support
from generator import PDFGenerator
from utils import (generate_next_complaint_number, release_vehicle, log_action, # Changed from generate_complaint_number
                   ensure_logs_table_exists, setup_logging, get_status_filter, calculate_newspaper_ad_date,
                   calculate_storage_fees, determine_jurisdiction, send_email_notification, 
                   send_sms_notification, send_fax_notification, is_valid_email, is_valid_phone,
                   generate_certified_mail_number, get_status_list_for_filter)
from flask_login import login_required, current_user
from auth import auth_bp, login_manager, init_auth_db, User, api_login_required
from datetime import datetime, timedelta, date # Added date here
from scraper import TowBookScraper
import threading
import subprocess # Added for running shell commands
from werkzeug.security import safe_join
from werkzeug.utils import secure_filename
from io import StringIO, BytesIO
import csv
import re
import sqlite3 # Added for handling database specific errors like IntegrityError
import time # Added for time.sleep

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
        # Database now uses 'location' field directly
        
        # Explicitly populate all fields required by generator.py's generate_top
        data['jurisdiction'] = data.get('jurisdiction', 'N/A')
        data['tow_date'] = data.get('tow_date') or datetime.now().strftime('%Y-%m-%d')
        data['tow_time'] = data.get('tow_time', 'N/A')
        # Database uses 'location' and 'requestor' directly
        data['requestor'] = data.get('requestor', 'N/A')
        data['year'] = data.get('year', 'N/A')
        data['make'] = data.get('make', 'N/A')
        data['model'] = data.get('model', 'N/A')
        data['color'] = data.get('color', 'N/A')
        data['vin'] = data.get('vin', 'N/A')
        data['plate'] = data.get('plate', 'N/A')
        data['state'] = data.get('state', 'N/A')
        data['complaint_number'] = data.get('complaint_number', 'N/A')
        # Keep case_number and officer_name as-is so generator can handle empty values
        data['case_number'] = data.get('case_number', '')
        data['officer_name'] = data.get('officer_name', '')
        # towbook_call_number is implicitly used for logging if present in data
        
        # TR-208 functionality removed
        
        # Add generation user info for PDF
        data['generated_by'] = username
                
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        pdf_filename = f"TOP_{call_number}_{timestamp}.pdf"
        pdf_path = os.path.join(app.config['GENERATED_FOLDER'], pdf_filename)
        os.makedirs(os.path.dirname(pdf_path), exist_ok=True)

        # Call the correct PDF generation method
        pdf_success, pdf_message = pdf_gen.generate_top(data, pdf_path)

        if pdf_success:
            # Database updates and logging for successful TOP generation
            log_action('TOP Form Generated', username, f"{call_number}: TOP form generated: {pdf_filename}")
            
            # Automatically update vehicle status to 'TOP Generated'
            from database import update_vehicle_status
            generation_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            status_success = update_vehicle_status(call_number, 'TOP Generated', {
                'top_form_sent_date': datetime.now().strftime('%Y-%m-%d'),
                'top_form_generated_at': generation_time,
                'top_form_generated_by': username
            })
            
            if status_success:
                logging.info(f"Vehicle {call_number} status updated to 'TOP Generated'")
            else:
                logging.warning(f"Failed to update status for vehicle {call_number} after TOP generation")
            
            success = True
            message = "TOP form generated successfully."
            vehicle_data = data
        else:
            success = False
            message = f"PDF generation failed: {pdf_message}"
            pdf_filename = pdf_message # Store error message in pdf_filename if generation fails
            
    except Exception as e:
        logging.error(f"Error in _perform_top_generation for {call_number}: {e}", exc_info=True)
        message = f"Error generating TOP form: {e}"
        pdf_filename = str(e) 
    finally:
        if conn:
            conn.close()
    return success, message, pdf_filename, vehicle_data, notification_id



@app.route('/api/vehicles/add', methods=['POST'])
@api_login_required
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
                log_action('Vehicle Added', 
                           current_user.id if current_user else 'System', 
                           f"Vehicle added: {data.get('towbook_call_number')} - {data.get('make')} {data.get('model')}")
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
# @login_required (disabled for testing)
def generate_top(call_number):
    logging.info(f"API called: generate_top for call_number={call_number}")
    username = getattr(current_user, 'id', 'System')
    success, message, pdf_filename_or_error, vehicle_data, notification_id = _perform_top_generation(call_number, username)
    if success:
        logging.info(f"TOP form generated successfully for call_number={call_number}")
        # Provide URL for accessing generated PDF
        pdf_url = url_for('static', filename=f"generated_pdfs/{pdf_filename_or_error}")
        return jsonify({
            "message": message, 
            "pdf_filename": pdf_filename_or_error, 
            "pdf_url": pdf_url,
            "vehicle": vehicle_data,
            "notification_id": notification_id
        }), 200
    else:
        logging.error(f"Failed to generate TOP form for call_number={call_number}: {message}")
        return jsonify({"error": message, "details": pdf_filename_or_error}), 500

def _perform_release_notice_generation(call_number, username):
    """
    Helper function to perform Release Notice generation, database updates, and logging.
    Returns (success, message, pdf_filename_or_error, vehicle_data, notification_id)
    """
    conn = None
    notification_id = None
    pdf_filename = None
    vehicle_data = None
    success = False
    message = ""
    try:
        conn = get_db_connection()
        vehicle = conn.execute("SELECT * FROM vehicles WHERE towbook_call_number = ?", (call_number,)).fetchone()
        if not vehicle:
            return False, "Vehicle not found", None, None, None
        data = dict(vehicle)
        # Prepare data fields for release notice
        data['jurisdiction'] = data.get('jurisdiction', 'N/A')
        data['tow_date'] = data.get('tow_date') or datetime.now().strftime('%Y-%m-%d')
        data['release_date'] = datetime.now().strftime('%Y-%m-%d')
        data['release_time'] = datetime.now().strftime('%H:%M:%S')
        data['recipient'] = data.get('released_to', 'N/A')
        data['release_reason'] = data.get('release_reason', 'Released')
        data['compliance_text'] = data.get('compliance_text', 'This notice is for vehicle release.')
        data['generated_by'] = username
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        pdf_filename = f"ReleaseNotice_{call_number}_{timestamp}.pdf"
        pdf_path = os.path.join(app.config['GENERATED_FOLDER'], pdf_filename)
        os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
        pdf_success, pdf_message = pdf_gen.generate_release_notice(data, pdf_path)
        if pdf_success:
            # Log and update vehicle status to 'Released'
            log_action('Release Notice Generated', username, f"{call_number}: Release notice generated: {pdf_filename}")
            from database import update_vehicle_status
            status_success = update_vehicle_status(call_number, 'Released', {
                'release_date': data['release_date'],
                'released_to': data['recipient']
            })
            if not status_success:
                logging.warning(f"Failed to update status for vehicle {call_number} after release notice generation")
            success = True
            message = "Release notice generated successfully."
            vehicle_data = data
        else:
            success = False
            message = f"PDF generation failed: {pdf_message}"
            pdf_filename = pdf_message
    except Exception as e:
        logging.error(f"Error in _perform_release_notice_generation for {call_number}: {e}", exc_info=True)
        message = f"Error generating release notice: {e}"
        pdf_filename = str(e)
    finally:
        if conn:
            conn.close()
    return success, message, pdf_filename, vehicle_data, notification_id

@app.route('/api/generate-release-notice/<call_number>', methods=['POST'])
# @login_required (disabled for testing)
def generate_release_notice(call_number):
    logging.info(f"API called: generate_release_notice for call_number={call_number}")
    username = getattr(current_user, 'id', 'System')
    success, message, pdf_filename_or_error, vehicle_data, notification_id = _perform_release_notice_generation(call_number, username)
    if success:
        pdf_url = url_for('static', filename=f"generated_pdfs/{pdf_filename_or_error}")
        return jsonify({
            "message": message,
            "pdf_filename": pdf_filename_or_error,
            "pdf_url": pdf_url,
            "vehicle": vehicle_data,
            "notification_id": notification_id
        }), 200
    else:
        logging.error(f"Failed to generate release notice for call_number={call_number}: {message}")
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
        status_filter_param = request.args.get('status', None)
        sort_column = request.args.get('sort', 'tow_date')
        sort_direction = request.args.get('direction', 'desc')

        logging.info(f"Fetching vehicles: status_param={status_filter_param}, sort={sort_column}, direction={sort_direction}")

        statuses_to_query = []
        if not status_filter_param or status_filter_param.lower() == 'all' or status_filter_param.lower() == 'active':
            statuses_to_query = get_status_list_for_filter('active') 
        elif status_filter_param.lower() == 'completed':
            statuses_to_query = get_status_list_for_filter('completed')
        else:
            statuses_to_query = [status_filter_param]

        if not statuses_to_query:
            logging.warning(f"No valid statuses to query for filter: {status_filter_param}")
            return jsonify([])

        vehicles_data = get_vehicles_by_status(statuses_to_query, sort_column, sort_direction)

        logging.info(f"Found {len(vehicles_data)} vehicles matching criteria for {status_filter_param}")
        return jsonify(vehicles_data)
    except Exception as e:
        logging.error(f"Error fetching vehicles: {e}", exc_info=True)
        return jsonify({"error": f"Failed to fetch vehicles: {str(e)}"}), 500

@app.route('/api/vehicle/<vehicle_id>', methods=['GET'])
@app.route('/api/vehicles/<vehicle_id>', methods=['GET'])
# @login_required (disabled for testing)
def get_vehicle_detail_api(vehicle_id):
    """API endpoint to get detailed information for a single vehicle."""
    try:
        # Try to get by towbook_call_number first (which is the primary identifier)
        vehicle = get_vehicle_by_call_number(vehicle_id)
        if vehicle:
            return jsonify(dict(vehicle))
        else:
            return jsonify({"error": "Vehicle not found"}), 404
    except Exception as e:
        logging.error(f"Error fetching vehicle details for call number {vehicle_id}: {e}", exc_info=True)
        return jsonify({"error": f"Failed to fetch vehicle details: {str(e)}"}), 500

@app.route('/api/vehicle/edit/<vehicle_id>', methods=['POST'])
@api_login_required
def edit_vehicle_api(vehicle_id):
    """API endpoint to update vehicle information."""
    try:
        data = request.json
        if not data:
            return jsonify({"error": "No data provided"}), 400

        # Ensure 'last_updated' is set
        data['last_updated'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # Update by towbook_call_number
        success, message = update_vehicle_by_call_number(vehicle_id, data)
        if success:
            log_action('Vehicle Updated', 
                       current_user.id if hasattr(current_user, 'id') else 'System', 
                       f"Vehicle details updated for call number: {vehicle_id}")
            # Fetch the updated vehicle data to return it
            updated_vehicle = get_vehicle_by_call_number(vehicle_id)
            if updated_vehicle:
                 return jsonify({"success": True, "message": "Vehicle updated successfully", "vehicle": dict(updated_vehicle)}), 200
            else: # Should not happen if update was successful and call number is correct
                 return jsonify({"success": True, "message": "Vehicle updated, but failed to retrieve updated data"}), 200
        else:
            # update_vehicle might return False if vehicle not found or on other db errors
            # Check if vehicle exists first to give a more specific error
            existing_vehicle = get_vehicle_by_call_number(vehicle_id)
            if not existing_vehicle:
                return jsonify({"error": "Vehicle not found, cannot update"}), 404
            return jsonify({"error": "Failed to update vehicle"}), 500
            
    except Exception as e:
        logging.error(f"Error updating vehicle call number {vehicle_id}: {e}", exc_info=True)
        return jsonify({"error": f"Server error: {str(e)}"}), 500

@app.route('/api/vehicles/<vehicle_id>', methods=['DELETE'])
@api_login_required
def delete_vehicle_api(vehicle_id):
    """API endpoint to delete a vehicle from the system."""
    try:
        # Check if vehicle exists first
        existing_vehicle = get_vehicle_by_call_number(vehicle_id)
        if not existing_vehicle:
            return jsonify({"error": "Vehicle not found"}), 404
        
        # Delete the vehicle from the database
        from database import delete_vehicle_by_call_number
        success = delete_vehicle_by_call_number(vehicle_id)
        
        if success:
            log_action('Vehicle Deleted', 
                       current_user.id if hasattr(current_user, 'id') else 'System', 
                       f"Vehicle deleted: call number {vehicle_id}")
            return jsonify({"success": True, "message": f"Vehicle {vehicle_id} deleted successfully"}), 200
        else:
            return jsonify({"error": "Failed to delete vehicle"}), 500
            
    except Exception as e:
        logging.error(f"Error deleting vehicle call number {vehicle_id}: {e}", exc_info=True)
        return jsonify({"error": f"Server error: {str(e)}"}), 500

@app.route('/api/diagnostic', methods=['GET'])
@api_login_required
def api_diagnostic():
    """Provides diagnostic information about the application."""
    db_conn = None
    cursor = None  # Initialize cursor
    try:
        db_conn = get_db_connection()
        cursor = db_conn.cursor() # Define cursor here
        
        # Check vehicle count
        cursor.execute("SELECT COUNT(*) FROM vehicles")
        vehicle_count = cursor.fetchone()[0]
        
        # Check contacts count
        cursor.execute("SELECT COUNT(*) FROM contacts")
        contacts_count = cursor.fetchone()[0]
        
        # Check users count
        cursor.execute("SELECT COUNT(*) FROM users")
        users_count = cursor.fetchone()[0]

        # Check logs count
        cursor.execute("SELECT COUNT(*) FROM action_logs")
        logs_count = cursor.fetchone()[0]
        
        db_status = "connected"
        db_path = os.environ.get('DATABASE_URL', 'Not set')
        
    except Exception as e:
        logging.error(f"Diagnostic check failed: {e}", exc_info=True)
        db_status = f"error: {str(e)}"
        vehicle_count = -1
        contacts_count = -1
        users_count = -1
        logs_count = -1
        db_path = os.environ.get('DATABASE_URL', 'Not set, or connection failed')
        
    finally:
        # Cursor does not need to be closed separately if the connection is closed.
        if db_conn:
            db_conn.close()
            
    return jsonify({
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "database": {
            "status": db_status,
            "path": db_path,
            "vehicle_count": vehicle_count,
            "contacts_count": contacts_count,
            "users_count": users_count,
            "logs_count": logs_count
        },
        "logging_level": logging.getLogger().getEffectiveLevel(), # Get root logger level
        "upload_folder_exists": os.path.exists(app.config['UPLOAD_FOLDER']),
        "document_folder_exists": os.path.exists(app.config['DOCUMENT_FOLDER']),
        "generated_folder_exists": os.path.exists(app.config['GENERATED_FOLDER'])
    }), 200

@app.route('/auth-diagnostics')
def auth_diagnostics():
    """Serve the authentication diagnostics page"""
    return send_file('auth_diagnostics.html')

@app.route('/api/vehicles/<vehicle_id>', methods=['PUT'])
@api_login_required
def update_vehicle_api(vehicle_id):
    """API endpoint to update a vehicle's information."""
    try:
        # Check if vehicle exists first
        existing_vehicle = get_vehicle_by_call_number(vehicle_id)
        if not existing_vehicle:
            return jsonify({"error": "Vehicle not found"}), 404
        
        data = request.json
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        # Update the vehicle in the database
        from database import update_vehicle_by_call_number
        success = update_vehicle_by_call_number(vehicle_id, data)
        
        if success:
            log_action('Vehicle Updated', 
                       current_user.id if hasattr(current_user, 'id') else 'System', 
                       f"Vehicle {vehicle_id} updated: {', '.join(data.keys())}")
            return jsonify({"message": "Vehicle updated successfully"}), 200
        else:
            return jsonify({"error": "Failed to update vehicle"}), 500
        
    except Exception as e:
        logging.error(f"Error updating vehicle {vehicle_id}: {e}", exc_info=True)
        return jsonify({"error": f"Server error: {str(e)}"}), 500

if __name__ == "__main__":
    PORT = 5001
    # Only run fuser logic if this is the main process and not the reloader's child
    if os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        logging.info(f"Preparing to start Flask app on port {PORT} (main process)")
        fuser_command_section_completed_normally = False
        try:
            # Command to kill any process using the port
            kill_command = f"fuser -k -n tcp {PORT}"
            logging.info(f"Attempting to free port {PORT} by running: '{kill_command}'")
            
            # Using print with flush=True for immediate output, in case logging is buffered or interrupted
            print(f"DEBUG: About to execute fuser command.", flush=True)

            result = subprocess.run(kill_command, shell=True, capture_output=True, text=True, check=False)
            
            print(f"DEBUG: fuser subprocess.run finished. RC: {result.returncode}. Stdout: '{result.stdout.strip()}'. Stderr: '{result.stderr.strip()}'", flush=True)
            logging.info(f"DEBUG: fuser subprocess.run finished. RC: {result.returncode}. Stdout: '{result.stdout.strip()}', Stderr: '{result.stderr.strip()}'")

            logging.info(f"fuser command processed with return code: {result.returncode}") # Changed log message slightly for clarity
            if result.stdout:
                logging.info(f"fuser stdout: {result.stdout.strip()}")
            if result.stderr:
                logging.info(f"fuser stderr: {result.stderr.strip()}")

            if result.returncode == 0:
                logging.info(f"fuser command likely succeeded in signalling process(es) on port {PORT}.")
            elif "command not found" in result.stderr.lower() or "not found" in result.stderr.lower() or result.returncode == 127:
                logging.warning(f"fuser command not found. Please ensure 'psmisc' package (which provides fuser) is installed. Stderr: {result.stderr.strip()}")
            elif result.returncode == 1:
                logging.info(f"fuser: No process found on port {PORT} (return code 1). This is normal if the port was already free.")
            else:
                logging.warning(f"fuser command may have encountered an issue. Return code: {result.returncode}. Stdout: '{result.stdout.strip()}', Stderr: '{result.stderr.strip()}'")
            
            fuser_command_section_completed_normally = True
            logging.info("Waiting 2 seconds for port to be fully released...")
            time.sleep(2) # Increased delay to 2 seconds

        except FileNotFoundError:
            logging.warning("fuser command not found (FileNotFoundError during subprocess.run). Please ensure 'psmisc' package is installed.")
        except Exception as e:
            logging.error(f"Error trying to free port {PORT} using fuser: {e}", exc_info=True)
        finally:
            print(f"DEBUG: Reached finally block after fuser attempt. Normal completion: {fuser_command_section_completed_normally}", flush=True)
            logging.info(f"DEBUG: Reached finally block after fuser attempt. Normal completion: {fuser_command_section_completed_normally}")
    else:
        logging.info(f"Flask app reloader active, skipping fuser command for port {PORT}.")

    logging.info("Starting Flask application...")
    # Pass use_reloader=False if you want to completely disable it,
    # but the WERKZEUG_RUN_MAIN check should be sufficient for the fuser issue.
    app.run(host="0.0.0.0", port=PORT, debug=True)