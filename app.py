import os
import base64
import logging
import secrets
import importlib.util
from flask import Flask, render_template, send_file, request, jsonify, redirect, url_for, send_from_directory, g
from database import (init_db, get_vehicles_by_status, update_vehicle_status,
                      update_vehicle, update_vehicle_by_call_number, insert_vehicle, get_db_connection, check_and_update_statuses, 
                      get_pending_notifications,
                      mark_notification_sent, get_contact_by_jurisdiction, save_contact, get_contacts,
                      get_vehicles, safe_parse_date, add_contact_explicit, update_contact_explicit,
                      delete_contact_explicit, get_contact_by_id, get_vehicle_by_id, get_vehicle_by_call_number,
                      get_vehicle_documents, delete_vehicle_document, add_document, update_document_delivery_status)
from generator import PDFGenerator
from utils import (generate_complaint_number, release_vehicle, log_action,
                   ensure_logs_table_exists, setup_logging, get_status_filter, calculate_newspaper_ad_date,
                   calculate_storage_fees, determine_jurisdiction, send_email_notification, 
                   send_sms_notification, send_fax_notification, is_valid_email, is_valid_phone,
                   generate_certified_mail_number, get_status_list_for_filter)
from flask_login import login_required, current_user
from auth import auth_bp, login_manager, init_auth_db, User, api_login_required
from datetime import datetime, timedelta, date
from werkzeug.utils import secure_filename
import sqlite3
import time
import subprocess
from utils_package.logging_utils import setup_logging

# Import route modules
from auction_routes import auction_bp
from cluster_routes import cluster_bp

# Configure logging
setup_logging()

app = Flask(__name__)

app.config.update(
    SECRET_KEY=secrets.token_urlsafe(32),  # Randomize on each start for dev: forces logout on restart
    PERMANENT_SESSION_LIFETIME=timedelta(hours=24),
    SESSION_COOKIE_SECURE=False,  # Set to True in production with HTTPS
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    SESSION_PERMANENT=False
)

database_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'vehicles.db')
os.environ['DATABASE_URL'] = database_path
logging.info(f"Using database at: {database_path}")

login_manager.init_app(app)
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'
app.register_blueprint(auth_bp)

# Register new blueprints for auction and cluster functionality
app.register_blueprint(auction_bp, url_prefix='/api')
app.register_blueprint(cluster_bp, url_prefix='/api')

# Import from the main api_routes.py file (not the directory)
import sys
import os
api_routes_file = os.path.join(os.path.dirname(__file__), 'api_routes.py')
spec = importlib.util.spec_from_file_location("api_routes_main", api_routes_file)
api_routes_main = importlib.util.module_from_spec(spec)
spec.loader.exec_module(api_routes_main)
api_routes_main.register_api_routes(app)

# Also register the new API routes from the directory
from api_routes import register_api_routes as register_new_api_routes
register_new_api_routes(app)

# Register vehicle tracking routes
from tracking_routes import register_tracking_routes
register_tracking_routes(app)

# Initialize AI integration - temporarily disabled
try:
    # from app.ai.integration import init_ai_integration
    # from app.api.ai_routes import ai_bp
    
    # Register AI API routes
    # app.register_blueprint(ai_bp)
    pass
    
    # Initialize AI integration manager
    # init_ai_integration(app)
    logging.info("AI integration disabled temporarily")
except ImportError as e:
    logging.warning(f"AI integration not available: {e}")
except Exception as e:
    logging.error(f"Failed to initialize AI integration: {e}")

from scheduler import init_scheduler
scheduler = init_scheduler(app)

with app.app_context():
    logging.info("Initializing application components...")
    logging.info(f"Database path from environment: {os.environ.get('DATABASE_URL')}")
    logging.info(f"Database exists: {os.path.exists(database_path)}")
    if os.path.exists(database_path):
        logging.info(f"Database size: {os.path.getsize(database_path)} bytes")
    init_db()
    init_auth_db()
    ensure_logs_table_exists()

pdf_gen = PDFGenerator()

UPLOAD_FOLDER = 'static/uploads/vehicle_photos'
DOCUMENT_FOLDER = 'static/uploads/documents'
GENERATED_FOLDER = 'static/generated_pdfs'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['DOCUMENT_FOLDER'] = DOCUMENT_FOLDER
app.config['GENERATED_FOLDER'] = GENERATED_FOLDER
app.config.setdefault('AUTO_DISPATCH_TOP', False)  # Disable auto-send by default
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
ALLOWED_DOCUMENT_EXTENSIONS = {'pdf', 'doc', 'docx', 'txt'}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(DOCUMENT_FOLDER, exist_ok=True)
os.makedirs(GENERATED_FOLDER, exist_ok=True)

# ---------------- Communication Endpoints ----------------
@app.route('/api/documents/<int:document_id>/send', methods=['POST'])
@login_required
def send_document(document_id):
    """Send a document (TOP / auction, etc.) to a jurisdictional contact via email/fax/text and log it."""
    from database import get_vehicle_by_call_number, log_document_communication, update_communication_status, get_db_connection
    try:
        data = request.json or {}
        method = (data.get('method') or '').lower()
        contact_id = data.get('contact_id')
        destination = data.get('destination')
        subject = data.get('subject') or 'Document Delivery'
        message = data.get('message') or 'Please see attached document.'
        if method not in ['email','fax','sms']:
            return jsonify({'error':'Invalid method. Use email, fax, or sms'}), 400
        conn = get_db_connection()
        doc = conn.execute("SELECT * FROM documents WHERE id=?", (document_id,)).fetchone()
        if not doc:
            return jsonify({'error':'Document not found'}), 404
        vehicle_id = doc['vehicle_id']
        call_number = doc['towbook_call_number']
        # Resolve file path: extend candidates with legacy filename/document_name fields
        attachment_path = None
        candidate_paths = []
        for key in ['file_path','filename','document_name']:
            val = doc[key] if key in doc.keys() else None
            if val:
                candidate_paths.append(val)
                candidate_paths.append(os.path.join(app.config['GENERATED_FOLDER'], val))
                candidate_paths.append(os.path.join(app.config['DOCUMENT_FOLDER'], val))
        for p in candidate_paths:
            if p and os.path.exists(p):
                attachment_path = p; break
        jurisdiction = None
        if contact_id and not destination:
            contact_row = conn.execute("SELECT * FROM contacts WHERE id=?", (contact_id,)).fetchone()
            if not contact_row:
                return jsonify({'error':'Contact not found'}), 404
            contact = dict(contact_row)
            jurisdiction = contact.get('jurisdiction')
            if method=='email':
                destination = contact.get('email_address') or contact.get('email')
            elif method=='fax':
                destination = contact.get('fax_number')
            elif method=='sms':
                destination = contact.get('mobile_number') or contact.get('phone_number') or contact.get('phone')
        if not destination:
            return jsonify({'error':'Destination not provided or not found on contact'}), 400
        if method=='email' and not is_valid_email(destination):
            return jsonify({'error':'Invalid email destination'}), 400
        if method in ['sms','fax'] and not is_valid_phone(destination):
            return jsonify({'error':'Invalid phone/fax destination'}), 400
        comm_id = log_document_communication(
            document_id=document_id,
            vehicle_id=vehicle_id,
            towbook_call_number=call_number,
            method=method,
            destination=destination,
            status='pending',
            subject=subject,
            message_preview=message[:200],
            contact_id=contact_id,
            jurisdiction=jurisdiction,
            attachment_path=attachment_path
        )
        success=False; error=None; provider_message_id=None
        if method=='email': success, error_or_msg = send_email_notification(destination, subject, message, attachment_path); error=None if success else error_or_msg
        elif method=='sms': success, error_or_msg = send_sms_notification(destination, message[:140]); error=None if success else error_or_msg
        elif method=='fax': success, error_or_msg = send_fax_notification(destination, message, attachment_path); error=None if success else error_or_msg
        try:
            update_communication_status(comm_id, 'sent' if success else 'failed', error=error, provider_message_id=provider_message_id)
        except Exception as ce:
            logging.error(f"Communication status update failed: {ce}")
        if success:
            try:
                from database import update_document_delivery_status
                update_document_delivery_status(document_id, sent_to=destination, sent_via=method)
            except Exception as de:
                logging.error(f"Delivery status update failed: {de}")
            log_action('Document Sent', current_user.username, f"Document {document_id} via {method} to {destination}")
            return jsonify({'status':'sent','communication_id':comm_id})
        else:
            log_action('Document Send Failed', current_user.username, f"Document {document_id} via {method} to {destination}: {error}")
            return jsonify({'status':'failed','error': error or 'Unknown send failure','communication_id':comm_id}), 500
    except Exception as e:
        logging.error(f"Unhandled send_document error for {document_id}: {e}", exc_info=True)
        return jsonify({'error':'Server error sending document','detail':str(e)}), 500

@app.route('/api/documents/<int:document_id>/communications', methods=['GET'])
@login_required
def list_document_communications(document_id):
    from database import get_document_communications
    comms = get_document_communications(document_id)
    return jsonify(comms)

@app.route('/api/vehicles/<call_number>/send-documents', methods=['POST'])
@login_required
def send_vehicle_documents(call_number):
    """Send one or more documents for a single vehicle via email.

    Request JSON:
    {
      "document_ids": [1,2,3] OR null (send all for vehicle),
      "destination": "recipient@example.com",  (optional if contact_id provided)
      "contact_id": 5, (optional -> resolves destination from contact email)
      "subject": "Optional subject", (default includes call number)
      "message": "HTML or plain body", (optional default generic)
    }
    """
    from database import get_vehicle_by_call_number, get_vehicle_documents, log_document_communication, update_communication_status, get_db_connection, update_document_delivery_status
    try:
        vehicle = get_vehicle_by_call_number(call_number)
        if not vehicle:
            return jsonify({'error': 'Vehicle not found'}), 404
        payload = request.json or {}
        doc_ids = payload.get('document_ids')
        destination = payload.get('destination')
        contact_id = payload.get('contact_id')
        subject = payload.get('subject') or f"Vehicle Documents for {call_number}"
        message = payload.get('message') or f"Attached are the selected documents for vehicle call number {call_number}."

        conn = get_db_connection()
        # Resolve contact if provided
        if contact_id and not destination:
            c_row = conn.execute('SELECT * FROM contacts WHERE id = ?', (contact_id,)).fetchone()
            if not c_row:
                return jsonify({'error': 'Contact not found'}), 404
            destination = c_row.get('email_address') or c_row.get('email')
        if not destination:
            return jsonify({'error': 'Destination email required'}), 400
        if not is_valid_email(destination):
            return jsonify({'error': 'Invalid email'}), 400

        # Collect documents
        vehicle_docs = get_vehicle_documents(call_number)
        if doc_ids:
            selected = [d for d in vehicle_docs if d['id'] in doc_ids]
        else:
            selected = vehicle_docs
        if not selected:
            return jsonify({'error': 'No documents found for selection'}), 400

        # Build file paths list
        attachment_files = []
        for d in selected:
            fp = d.get('file_path')
            if fp:
                attachment_files.append(fp)

        # Log a communication row per document (so tracking works per doc) but only send one email.
        comm_ids = []
        for d in selected:
            comm_id = log_document_communication(
                document_id=d['id'],
                vehicle_id=vehicle.get('id'),
                towbook_call_number=call_number,
                method='email',
                destination=destination,
                status='pending',
                subject=subject,
                message_preview=message[:200],
                contact_id=contact_id,
                jurisdiction=vehicle.get('jurisdiction'),
                attachment_path=d.get('file_path')
            )
            if comm_id:
                comm_ids.append(comm_id)

        # Perform single email send with all attachments
        send_ok, send_msg = send_email_notification(destination, subject, message, attachments=attachment_files)

        # Update all communication statuses
        for cid in comm_ids:
            update_communication_status(cid, 'sent' if send_ok else 'failed', None if send_ok else send_msg)

        if send_ok:
            # Mark documents as sent (delivery status) - one by one
            for d in selected:
                try:
                    update_document_delivery_status(d['id'], sent_to=destination, sent_via='email')
                except Exception as _e:
                    logging.warning(f"Failed to update document {d['id']} delivery status: {_e}")
            log_action('Documents Sent', getattr(current_user, 'username', 'System'), f"{len(selected)} docs for {call_number} to {destination}")
            return jsonify({'status': 'sent', 'documents': [d['id'] for d in selected], 'communication_ids': comm_ids, 'message': send_msg})
        else:
            log_action('Documents Send Failed', getattr(current_user, 'username', 'System'), f"{len(selected)} docs for {call_number} to {destination}: {send_msg}")
            return jsonify({'status': 'failed', 'error': send_msg, 'communication_ids': comm_ids}), 500
    except Exception as e:
        logging.error(f"send_vehicle_documents error for {call_number}: {e}", exc_info=True)
        return jsonify({'error': 'Server error sending documents'}), 500

@app.route('/api/dashboard/summary')
@login_required
def dashboard_summary():
    """Lightweight KPI summary for dashboard cards."""
    try:
        conn = get_db_connection()
        vehicles = conn.execute('SELECT COUNT(*) c FROM vehicles').fetchone()['c']
        documents = conn.execute('SELECT COUNT(*) c FROM documents').fetchone()['c'] if conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='documents'").fetchone() else 0
        auctions = conn.execute('SELECT COUNT(*) c FROM auctions').fetchone()['c'] if conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='auctions'").fetchone() else 0
        pending_actions = conn.execute("SELECT COUNT(*) c FROM vehicles WHERE status IS NULL OR status='' OR status LIKE '%Pending%'").fetchone()['c']
        return jsonify({
            'vehicles': vehicles,
            'documents': documents,
            'auctions': auctions,
            'pending_actions': pending_actions
        })
    except Exception as e:
        logging.error(f"dashboard_summary error: {e}")
        return jsonify({'error':'Failed to load summary'}), 500
LOGO_PATH = 'static/logo.png'
if not os.path.exists(LOGO_PATH):
    try:
        png_data = base64.b64decode(
            b'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII='
        )
        with open(LOGO_PATH, 'wb') as f:
            f.write(png_data)
        logging.info(f"Created placeholder 1x1 transparent PNG at {LOGO_PATH}")
    except Exception as e:
        logging.error(f"Failed to create placeholder logo.png: {e}", exc_info=True)

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
    conn = None
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
            # Automatically add the generated TOP form to documents table with compliance tracking
            from database import add_document
            doc_id = add_document(
                call_number=call_number,
                document_name=pdf_filename,
                document_type='TOP',
                file_path=pdf_filename,
                uploaded_by=username,
                compliance_requirement='MCL 257.252b - Owner Notification'
            )
            
            if doc_id:
                logging.info(f"TOP form automatically added to documents table with ID {doc_id}")
                # Auto dispatch intentionally disabled by default; controlled via config flag
                if app.config.get('AUTO_DISPATCH_TOP'):
                    try:
                        from database import get_vehicle_by_call_number, get_contact_by_jurisdiction, log_document_communication, update_document_delivery_status, update_communication_status
                        vehicle_row = get_vehicle_by_call_number(call_number)
                        jurisdiction = (vehicle_row or {}).get('jurisdiction') or (vehicle_row or {}).get('location')
                        contact_row = get_contact_by_jurisdiction(jurisdiction) if jurisdiction else None
                        contact = dict(contact_row) if contact_row else None
                        if contact:
                            preferred = (contact.get('preferred_contact_method') or '').lower()
                            order = [m for m in [preferred, 'email', 'fax', 'sms'] if m in ['email','fax','sms']]
                            seen=set(); method_order=[]
                            for m in order:
                                if m and m not in seen:
                                    seen.add(m); method_order.append(m)
                            destination=None; chosen_method=None
                            for m in method_order:
                                if m=='email': destination = contact.get('email_address') or contact.get('email')
                                elif m=='fax': destination = contact.get('fax_number')
                                elif m=='sms': destination = contact.get('mobile_number') or contact.get('phone_number') or contact.get('phone')
                                if destination:
                                    chosen_method=m; break
                            if destination and chosen_method:
                                if chosen_method=='email' and not is_valid_email(destination):
                                    raise ValueError('Invalid email destination')
                                if chosen_method in ['fax','sms'] and not is_valid_phone(destination):
                                    raise ValueError('Invalid phone/fax destination')
                                subject=f"TOP Form {call_number}"; message=f"Attached TOP form for vehicle call number {call_number}."
                                attachment_path=os.path.join(app.config['GENERATED_FOLDER'], pdf_filename)
                                comm_id = log_document_communication(doc_id, vehicle_row.get('id') if vehicle_row else None, call_number, chosen_method, destination, 'pending', subject, message[:200], contact.get('id'), jurisdiction, None, None, None, attachment_path)
                                send_success=False; error=None
                                if chosen_method=='email': send_success, res = send_email_notification(destination, subject, message, attachment_path); error=None if send_success else res
                                elif chosen_method=='sms': send_success, res = send_sms_notification(destination, message[:140]); error=None if send_success else res
                                elif chosen_method=='fax': send_success, res = send_fax_notification(destination, message, attachment_path); error=None if send_success else res
                                update_communication_status(comm_id, 'sent' if send_success else 'failed', error=error)
                                if send_success:
                                    update_document_delivery_status(doc_id, sent_to=destination, sent_via=chosen_method)
                                    log_action('TOP Sent Automatically', username, f"TOP doc {doc_id} via {chosen_method} to {destination}")
                                else:
                                    log_action('TOP Auto-Send Failed', username, f"TOP doc {doc_id} via {chosen_method} to {destination} failed: {error}")
                        else:
                            logging.info(f"Auto dispatch skipped: no contact for jurisdiction {jurisdiction}")
                    except Exception as e:
                        logging.error(f"Auto TOP dispatch failed for {call_number}: {e}", exc_info=True)
            
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
        # Only close the connection if it's not managed by Flask's g object
        if conn and (not hasattr(g, '_database') or g._database != conn):
            conn.close()
    return success, message, pdf_filename, vehicle_data, notification_id



@app.route('/api/vehicles/add', methods=['POST'])
@api_login_required  # Re-enable authentication
def add_vehicle():
    try:
        # Handle both JSON and multipart form data
        if request.content_type and 'application/json' in request.content_type:
            # JSON data (backward compatibility)
            data = request.json
            if not data:
                return jsonify({"error": "No data provided"}), 400
        else:
            # Multipart form data (with files)
            data = {}
            for key in request.form:
                value = request.form.get(key)  # Use get() to get single value, not getlist()
                if value and value.strip():  # Only include non-empty values
                    data[key] = value.strip()
            
            # Handle file uploads
            uploaded_photos = []
            uploaded_documents = []
            
            # Process vehicle photos
            if 'vehicle_photos' in request.files:
                photo_files = request.files.getlist('vehicle_photos')
                for photo_file in photo_files:
                    if photo_file and photo_file.filename and allowed_file(photo_file.filename):
                        filename = secure_filename(photo_file.filename)
                        # Create unique filename with timestamp
                        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                        filename = f"{timestamp}_{filename}"
                        photo_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                        photo_file.save(photo_path)
                        uploaded_photos.append(filename)
                        logging.info(f"Saved vehicle photo: {filename}")
            
            # Process vehicle documents
            if 'vehicle_documents' in request.files:
                doc_files = request.files.getlist('vehicle_documents')
                for doc_file in doc_files:
                    if doc_file and doc_file.filename and allowed_document(doc_file.filename):
                        filename = secure_filename(doc_file.filename)
                        # Create unique filename with timestamp
                        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                        filename = f"{timestamp}_{filename}"
                        doc_path = os.path.join(app.config['DOCUMENT_FOLDER'], filename)
                        doc_file.save(doc_path)
                        uploaded_documents.append(filename)
                        logging.info(f"Saved vehicle document: {filename}")
            
            # Store file paths in database-compatible format
            if uploaded_photos:
                data['photos'] = ','.join(uploaded_photos)
            if uploaded_documents:
                data['documents'] = ','.join(uploaded_documents)
            
        # Pop optional flags before database insertion
        should_auto_top = data.pop('auto_top', False)
            
        # Validate required fields
        if not data.get('towbook_call_number'):
            return jsonify({"error": "Call number is required"}), 400
            
        if not data.get('status'):
            data['status'] = 'New'  # Default status
            
        # Generate complaint number if missing
        if 'complaint_number' not in data or not data['complaint_number'] or data['complaint_number'] == 'N/A':
            complaint_data = generate_complaint_number()
            # Always use only the string part for complaint_number
            if isinstance(complaint_data, tuple):
                data['complaint_number'] = complaint_data[0]
                # Optionally store sequence/year if those columns exist, otherwise ignore
            else:
                data['complaint_number'] = complaint_data
            
        # Detect jurisdiction if needed
        if data.get('location_from') and (not data.get('jurisdiction') or data['jurisdiction'] == 'detect'):
            data['jurisdiction'] = determine_jurisdiction(data['location_from'])
        elif data.get('location') and (not data.get('jurisdiction') or data['jurisdiction'] == 'detect'):
            data['jurisdiction'] = determine_jurisdiction(data['location'])
            
        # Handle missing photos/documents gracefully and ensure string type
        if 'photos' not in data or not data['photos']:
            data['photos'] = ''
        elif isinstance(data['photos'], (list, tuple)):
            data['photos'] = ','.join([str(p) for p in data['photos']])
        if 'documents' not in data or not data['documents']:
            data['documents'] = ''
        elif isinstance(data['documents'], (list, tuple)):
            data['documents'] = ','.join([str(d) for d in data['documents']])
            
        # Add timestamp
        data['tow_date'] = data.get('tow_date') or datetime.now().strftime('%Y-%m-%d')
        data['last_updated'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Debug logging
        logging.info(f"About to insert vehicle data: {list(data.keys())}")
        for key, value in data.items():
            logging.info(f"  {key}: {type(value)} = {repr(value)}")
            
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
            logging.error(f"Database error in add_vehicle: {e}", exc_info=True)
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
                
            response_data = {
                "success": True, 
                "vehicle_id": vehicle_id, 
                "message": "Vehicle added successfully"
            }
            
            # Include file upload info in response
            if uploaded_photos:
                response_data["photos_uploaded"] = len(uploaded_photos)
            if uploaded_documents:
                response_data["documents_uploaded"] = len(uploaded_documents)
                
            return jsonify(response_data), 201
        else:
            return jsonify({"error": "Failed to add vehicle for unknown reason"}), 500
            
    except Exception as e:
        logging.error(f"Error adding vehicle in app.py: {e}", exc_info=True)
        return jsonify({"error": f"Server error: {str(e)}"}), 500

@app.route('/api/vehicles/<call_number>/documents', methods=['POST'])
@api_login_required
def add_vehicle_documents(call_number):
    """Add documents to an existing vehicle"""
    try:
        # Check if vehicle exists
        existing_vehicle = get_vehicle_by_call_number(call_number)
        if not existing_vehicle:
            return jsonify({"error": "Vehicle not found"}), 404
        
        uploaded_documents = []
        success_count = 0
        error_messages = []
        
        # Process vehicle documents from file upload
        if 'documents' in request.files:
            doc_files = request.files.getlist('documents')
            for doc_file in doc_files:
                if doc_file and doc_file.filename and allowed_document(doc_file.filename):
                    try:
                        filename = secure_filename(doc_file.filename)
                        # Create unique filename with timestamp
                        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                        unique_filename = f"{timestamp}_{filename}"
                        doc_path = os.path.join(app.config['DOCUMENT_FOLDER'], unique_filename)
                        doc_file.save(doc_path)
                        
                        # Add to database using the structured documents table
                        from database import add_document
                        doc_id = add_document(
                            call_number=call_number,
                            document_name=filename,
                            document_type=request.form.get('document_type', 'General'),
                            file_path=unique_filename,
                            uploaded_by=current_user.id if current_user else 'System'
                        )
                        
                        if doc_id:
                            uploaded_documents.append({
                                'id': doc_id,
                                'filename': filename,
                                'unique_filename': unique_filename,
                                'document_type': request.form.get('document_type', 'General')
                            })
                            success_count += 1
                            logging.info(f"Document uploaded for vehicle {call_number}: {filename}")
                        else:
                            error_messages.append(f"Failed to save {filename} to database")
                            # Clean up file if database insert failed
                            if os.path.exists(doc_path):
                                os.remove(doc_path)
                                
                    except Exception as e:
                        error_messages.append(f"Error processing {doc_file.filename}: {str(e)}")
                        logging.error(f"Error processing document {doc_file.filename}: {e}", exc_info=True)
                else:
                    if doc_file.filename:
                        error_messages.append(f"File type not allowed: {doc_file.filename}")
                        
        # Also update the vehicles.documents field with the new documents (append to existing)
        if uploaded_documents:
            try:
                existing_docs = existing_vehicle.get('documents', '') or ''
                new_doc_filenames = [doc['unique_filename'] for doc in uploaded_documents]
                
                # Combine existing and new documents
                if existing_docs:
                    all_docs = existing_docs + ',' + ','.join(new_doc_filenames)
                else:
                    all_docs = ','.join(new_doc_filenames)
                    
                # Update the vehicle record
                from database import update_vehicle_by_call_number
                update_success = update_vehicle_by_call_number(call_number, {'documents': all_docs})
                
                if not update_success:
                    logging.warning(f"Failed to update vehicle {call_number} documents field")
                    
            except Exception as e:
                logging.error(f"Error updating vehicle documents field: {e}", exc_info=True)
        
        # Log the action
        if success_count > 0:
            log_action('Documents Added', 
                      current_user.id if current_user else 'System',
                      f"Added {success_count} document(s) to vehicle {call_number}")
        
        # Prepare response
        response_data = {
            "success": success_count > 0,
            "message": f"Successfully uploaded {success_count} document(s)",
            "documents_uploaded": success_count,
            "uploaded_documents": uploaded_documents
        }
        
        if error_messages:
            response_data["errors"] = error_messages
            response_data["message"] += f" ({len(error_messages)} error(s))"
        
        status_code = 201 if success_count > 0 else 400
        return jsonify(response_data), status_code
        
    except Exception as e:
        logging.error(f"Error adding documents to vehicle {call_number}: {e}", exc_info=True)
        return jsonify({"error": f"Server error: {str(e)}"}), 500

@app.route('/api/vehicles/<call_number>/documents', methods=['GET'])
@api_login_required
def get_vehicle_documents_api(call_number):
    """Get all documents for a vehicle"""
    try:
        # Check if vehicle exists
        existing_vehicle = get_vehicle_by_call_number(call_number)
        if not existing_vehicle:
            return jsonify({"error": "Vehicle not found"}), 404
            
        from database import get_vehicle_documents
        documents = get_vehicle_documents(call_number)
        
        return jsonify({
            "success": True,
            "documents": documents,
            "count": len(documents)
        }), 200
        
    except Exception as e:
        logging.error(f"Error getting documents for vehicle {call_number}: {e}", exc_info=True)
        return jsonify({"error": f"Server error: {str(e)}"}), 500

@app.route('/api/documents/<int:document_id>', methods=['DELETE'])
@api_login_required  
def delete_document_api(document_id):
    """Delete a vehicle document"""
    try:
        from database import delete_vehicle_document
        success, message = delete_vehicle_document(document_id)
        
        if success:
            log_action('Document Deleted', 
                      current_user.id if current_user else 'System',
                      f"Deleted document ID {document_id}")
            return jsonify({"success": True, "message": message}), 200
        else:
            return jsonify({"error": message}), 404
            
    except Exception as e:
        logging.error(f"Error deleting document {document_id}: {e}", exc_info=True)
        return jsonify({"error": f"Server error: {str(e)}"}), 500

@app.route('/api/generate-top/<call_number>', methods=['POST'])
@api_login_required
def generate_top(call_number):
    logging.info(f"API called: generate_top for call_number={call_number}")
    username = getattr(current_user, 'username', 'System')
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

@app.route('/api/generate-release/<call_number>', methods=['POST'])
@api_login_required
def generate_release(call_number):
    """Generate a release notice PDF for a vehicle (owner claimed, auctioned, scrapped, transferred)."""
    try:
        vehicle = get_vehicle_by_call_number(call_number)
        if not vehicle:
            return jsonify({'error': 'Vehicle not found'}), 404
        data = request.json or {}
        # Map expected fields
        release_reason = data.get('release_reason') or vehicle.get('status') or 'Released'
        release_payload = {
            'complaint_number': vehicle.get('complaint_number'),
            'release_date': data.get('release_date') or datetime.now().strftime('%Y-%m-%d'),
            'release_time': data.get('release_time') or datetime.now().strftime('%H:%M'),
            'recipient': data.get('recipient') or data.get('released_to') or 'Unknown',
            'release_reason': release_reason,
            'compliance_text': data.get('compliance_text') or 'Released pursuant to MCL 257.252 and related statutes.',
            'year': vehicle.get('year'), 'make': vehicle.get('make'), 'model': vehicle.get('model'), 'color': vehicle.get('color'),
            'vin': vehicle.get('vin'), 'plate': vehicle.get('plate'), 'state': vehicle.get('state'), 'tow_date': vehicle.get('tow_date')
        }
        pdf_gen = PDFGenerator()
        filename = f"release_{call_number}_{int(time.time())}.pdf"
        pdf_path = os.path.join('static', 'generated_pdfs', filename)
        ok, err = pdf_gen.generate_release_notice(release_payload, pdf_path)
        if not ok:
            return jsonify({'error': 'Failed to generate release document', 'detail': err}), 500
        # Log document in documents table
        add_document(call_number, filename, 'RELEASE', pdf_path, getattr(current_user, 'username', 'System'))
        log_action('Release Generated', getattr(current_user, 'username', 'System'), f'Release notice generated for {call_number}')
        return jsonify({'message': 'Release generated', 'pdf_filename': filename, 'pdf_url': url_for('static', filename=f'generated_pdfs/{filename}')})
    except Exception as e:
        logging.error(f"Error generating release for {call_number}: {e}", exc_info=True)
        return jsonify({'error': 'Server error generating release'}), 500

@app.route('/api/generate-auction-ad/<int:auction_id>', methods=['POST'])
@api_login_required
def generate_newspaper_ad_api(auction_id):
    """Generate a combined newspaper ad PDF for vehicles in an auction and capture ad metadata (newspaper name, date, content)."""
    try:
        conn = get_db_connection()
        auction = conn.execute('SELECT * FROM auctions WHERE id = ?', (auction_id,)).fetchone()
        if not auction:
            return jsonify({'error': 'Auction not found'}), 404
        rows = conn.execute("""
            SELECT v.* FROM auction_vehicles av
            JOIN vehicles v ON av.vehicle_id = v.id
            WHERE av.auction_id = ?
        """, (auction_id,)).fetchall()
        vehicles = [dict(r) for r in rows]
        if not vehicles:
            return jsonify({'error': 'No vehicles in auction'}), 400
        data = request.json or {}
        newspaper_name = data.get('newspaper_name', 'Unknown Newspaper')
        ad_date = data.get('ad_date') or datetime.now().strftime('%Y-%m-%d')
        ad_content = data.get('ad_content') or ''
        # Inject auction date & ad meta into each vehicle record for generator
        for v in vehicles:
            v['auction_date'] = auction['auction_date']
            v['ad_placement_date'] = ad_date
            v['newspaper_name'] = newspaper_name
        pdf_gen = PDFGenerator()
        filename = f"auction_ad_{auction_id}_{int(time.time())}.pdf"
        pdf_path = os.path.join('static', 'generated_pdfs', filename)
        ok, err = pdf_gen.generate_newspaper_ad(vehicles, pdf_path)
        if not ok:
            return jsonify({'error': 'Failed to generate newspaper ad', 'detail': err}), 500
        # Store as auction document (type: NEWSPAPER_AD) - reuse existing mechanism if any else documents table
        add_document(vehicles[0].get('towbook_call_number'), filename, 'NEWSPAPER_AD', pdf_path, getattr(current_user, 'username', 'System'))
        log_action('Auction Ad Generated', getattr(current_user, 'username', 'System'), f'Auction ad generated for auction {auction_id} ({newspaper_name} {ad_date})')
        # Persist ad metadata to auctions table if columns exist, else ignore
        try:
            conn.execute('ALTER TABLE auctions ADD COLUMN newspaper_name TEXT')
        except Exception:
            pass
        try:
            conn.execute('ALTER TABLE auctions ADD COLUMN newspaper_ad_date TEXT')
        except Exception:
            pass
        try:
            conn.execute('ALTER TABLE auctions ADD COLUMN newspaper_ad_content TEXT')
        except Exception:
            pass
        conn.execute('UPDATE auctions SET newspaper_name = ?, newspaper_ad_date = ?, newspaper_ad_content = ? WHERE id = ?',
                     (newspaper_name, ad_date, ad_content, auction_id))
        conn.commit()
        return jsonify({'message': 'Auction ad generated', 'pdf_filename': filename, 'pdf_url': url_for('static', filename=f'generated_pdfs/{filename}')})
    except Exception as e:
        logging.error(f"Error generating newspaper ad for auction {auction_id}: {e}", exc_info=True)
        return jsonify({'error': 'Server error generating auction ad'}), 500

@app.route('/api/top-forms/<call_number>/send', methods=['POST'])
@api_login_required
def send_top_form(call_number):
    """Mark TOP form as sent and update delivery tracking"""
    try:
        data = request.json
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        # Get vehicle to validate it exists
        existing_vehicle = get_vehicle_by_call_number(call_number)
        if not existing_vehicle:
            return jsonify({"error": "Vehicle not found"}), 404
        
        sent_to = data.get('sent_to')  # e.g., "Owner", "Lienholder", "Both"
        sent_via = data.get('sent_via')  # e.g., "Certified Mail", "Email", "Fax"
        tracking_number = data.get('tracking_number', '')
        notes = data.get('notes', '')
        
        if not sent_to or not sent_via:
            return jsonify({"error": "sent_to and sent_via are required"}), 400
        
        # Find the TOP document for this vehicle
        from database import get_db_connection
        conn = get_db_connection()
        
        top_doc = conn.execute("""
            SELECT id FROM documents 
            WHERE towbook_call_number = ? AND document_type = 'TOP'
            ORDER BY uploaded_at DESC LIMIT 1
        """, (call_number,)).fetchone()
        
        if not top_doc:
            return jsonify({"error": "No TOP form found for this vehicle"}), 404
        
        # Update document delivery tracking
        from database import update_document_delivery_status
        success = update_document_delivery_status(
            document_id=top_doc['id'],
            sent_to=sent_to,
            sent_via=sent_via,
            tracking_number=tracking_number
        )
        
        if success:
            # Update vehicle's TOP sent date
            update_vehicle_by_call_number(call_number, {
                'top_form_sent_date': datetime.now().strftime('%Y-%m-%d')
            })
            
            log_action('TOP Form Sent',
                      current_user.id if current_user else 'System',
                      f"TOP form for {call_number} sent to {sent_to} via {sent_via}")
            
            return jsonify({
                "success": True,
                "message": f"TOP form marked as sent to {sent_to} via {sent_via}"
            }), 200
        else:
            return jsonify({"error": "Failed to update delivery status"}), 500
            
    except Exception as e:
        logging.error(f"Error marking TOP form as sent: {e}", exc_info=True)
        return jsonify({"error": f"Server error: {str(e)}"}), 500

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
        # Only close the connection if it's not managed by Flask's g object
        if conn and (not hasattr(g, '_database') or g._database != conn):
            conn.close()
    return success, message, pdf_filename, vehicle_data, notification_id

@app.route('/api/generate-release-notice/<call_number>', methods=['POST'])
@api_login_required
def generate_release_notice(call_number):
    logging.info(f"API called: generate_release_notice for call_number={call_number}")
    username = getattr(current_user, 'username', 'System')
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

@app.route('/api/release-forms/<call_number>/send', methods=['POST'])
@api_login_required
def send_release_form(call_number):
    """Send (log) a release notice via chosen method (email/fax/sms)."""
    try:
        from database import log_document_communication, update_communication_status
        vehicle = get_vehicle_by_call_number(call_number)
        if not vehicle:
            return jsonify({'error': 'Vehicle not found'}), 404
        data = request.json or {}
        document_id = data.get('document_id')
        method = (data.get('method') or '').lower()
        destination = data.get('destination')
        if method not in {'email', 'fax', 'sms'}:
            return jsonify({'error': 'Invalid method'}), 400
        if not destination:
            return jsonify({'error': 'Destination required'}), 400
        if method == 'email' and not is_valid_email(destination):
            return jsonify({'error': 'Invalid email'}), 400
        if method in {'fax', 'sms'} and not is_valid_phone(destination):
            return jsonify({'error': 'Invalid phone/fax'}), 400
        if not document_id:
            docs = get_vehicle_documents(call_number)
            release_docs = [d for d in docs if (d.get('document_type') or '').upper() == 'RELEASE']
            if not release_docs:
                return jsonify({'error': 'No release document found'}), 400
            document_id = release_docs[0]['id']
        comm_id = log_document_communication(document_id=document_id,
                                             vehicle_id=vehicle.get('id'),
                                             towbook_call_number=call_number,
                                             method=method,
                                             destination=destination,
                                             status='pending',
                                             jurisdiction=vehicle.get('jurisdiction'))
        try:
            conn = get_db_connection()
            doc_row = conn.execute('SELECT * FROM documents WHERE id = ?', (document_id,)).fetchone()
            file_path = doc_row['file_path'] if doc_row else None
            subject = f"Vehicle Release Notice {call_number}"
            preview = subject
            send_ok = True
            if method == 'email':
                send_ok = send_email_notification(destination, subject, preview, attachments=[file_path] if file_path else None)
            elif method == 'sms':
                send_ok = send_sms_notification(destination, preview)
            elif method == 'fax':
                send_ok = send_fax_notification(destination, file_path) if file_path else False
            update_communication_status(comm_id, 'sent' if send_ok else 'failed', None if send_ok else 'Send failed')
        except Exception as e2:
            logging.error(f"Error actually sending release notice: {e2}", exc_info=True)
            update_communication_status(comm_id, 'failed', str(e2))
            return jsonify({'error': 'Failed to send release', 'detail': str(e2)}), 500
        log_action('Release Sent', getattr(current_user, 'username', 'System'), f'Release notice sent for {call_number} via {method} to {destination}')
        return jsonify({'message': 'Release sent', 'communication_id': comm_id})
    except Exception as e:
        logging.error(f"Error in send_release_form for {call_number}: {e}", exc_info=True)
        return jsonify({'error': 'Server error sending release'}), 500

@app.route('/')
def index():
    if not current_user.is_authenticated:
        return redirect(url_for('auth.login'))
    return redirect(url_for('document_management'))

@app.route('/document-management')
@login_required
def document_management():
    """Document management interface with TOP forms, auctions, and clusters"""
    return render_template('document_management.html', current_user=current_user)

@app.route('/tracking')
@login_required
def vehicle_tracking():
    """Vehicle tracking dashboard"""
    return render_template('vehicle_tracking.html', current_user=current_user)

@app.route('/auction-management')
@login_required
def auction_management():
    """Auction management interface"""
    return render_template('auction_management.html', current_user=current_user)

@app.route('/auctions')
@login_required
def auctions_redirect():
    return redirect(url_for('auction_management'))

@app.route('/contacts')
@login_required
def contacts_page():
    return render_template('contacts.html', current_user=current_user)

@app.route('/locations')
@login_required
def locations_page():
    return render_template('locations.html', current_user=current_user)

@app.route('/dashboard')
@login_required
def simplified_dashboard():
    """Dedicated dashboard distinct from vehicle/document management."""
    kpis = {}
    recent_completed = []
    try:
        conn = get_db_connection()
        total = conn.execute("SELECT COUNT(*) c FROM vehicles").fetchone()['c']
        active = conn.execute("SELECT COUNT(*) c FROM vehicles WHERE status NOT IN ('Released','Scrapped','Auctioned','Transferred','Completed')").fetchone()['c']
        status_rows = conn.execute("SELECT COALESCE(status,'(None)') status, COUNT(*) c FROM vehicles GROUP BY status ORDER BY c DESC").fetchall()
        doc_rows = conn.execute("SELECT document_type, COUNT(*) c FROM documents GROUP BY document_type ORDER BY c DESC LIMIT 8").fetchall() if conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='documents'").fetchone() else []
        auctions = conn.execute("SELECT COUNT(*) c FROM auctions").fetchone()['c'] if conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='auctions'").fetchone() else 0
        recent_completed_rows = conn.execute("SELECT towbook_call_number, year, make, model, status, tow_date, updated_at FROM vehicles WHERE status IN ('Released','Scrapped','Auctioned','Transferred','Completed') ORDER BY updated_at DESC LIMIT 5").fetchall()
        kpis = {
            'total_vehicles': total,
            'active_vehicles': active,
            'auction_count': auctions,
            'status_breakdown': [dict(r) for r in status_rows],
            'doc_breakdown': [dict(r) for r in doc_rows]
        }
        recent_completed = [dict(r) for r in recent_completed_rows]
    except Exception as e:
        logging.error(f"Dashboard KPI error: {e}")
    return render_template('dashboard.html', current_user=current_user, kpis=kpis, recent_completed=recent_completed)

@app.route('/ui/vehicles', methods=['GET'])
@login_required
def ui_list_vehicles():
    """Vehicle list with scope filtering: ?scope=active|completed|all (default active)."""
    scope = request.args.get('scope','active').lower()
    completed_statuses = ['Released','Scrapped','Auctioned','Transferred','Completed']
    try:
        conn = get_db_connection()
        if scope == 'completed':
            rows = conn.execute("SELECT * FROM vehicles WHERE status IN ({seq}) ORDER BY tow_date DESC LIMIT 500".format(seq=','.join('?'*len(completed_statuses))), completed_statuses).fetchall()
        elif scope == 'all':
            rows = conn.execute("SELECT * FROM vehicles ORDER BY tow_date DESC LIMIT 500").fetchall()
        else:  # active
            rows = conn.execute("SELECT * FROM vehicles WHERE (status NOT IN ({seq}) OR status IS NULL OR status='') ORDER BY tow_date DESC LIMIT 500".format(seq=','.join('?'*len(completed_statuses))), completed_statuses).fetchall()
        vehicles = [dict(r) for r in rows]
        minimal = [{
            'towbook_call_number': v.get('towbook_call_number'),
            'year': v.get('year'),
            'make': v.get('make'),
            'model': v.get('model'),
            'plate': v.get('plate'),
            'state': v.get('state'),
            'status': v.get('status'),
            'tow_date': v.get('tow_date'),
            'jurisdiction': v.get('jurisdiction') or v.get('location'),
            'vin': v.get('vin'),
            'complaint_number': v.get('complaint_number')
        } for v in vehicles]
        return jsonify({'vehicles': minimal, 'count': len(minimal), 'scope': scope})
    except Exception as e:
        logging.error(f"Error in ui_list_vehicles: {e}", exc_info=True)
        return jsonify({'error':'Failed to fetch vehicles'}), 500

@app.route('/ui/vehicles/<call_number>/context', methods=['GET'])
@login_required
def ui_vehicle_context(call_number):
    """Return consolidated context for a vehicle: vehicle info, documents, communications, contact, suggested actions."""
    try:
        logging.debug(f"Building UI vehicle context for {call_number}")
        vehicle = get_vehicle_by_call_number(call_number)
        if not vehicle:
            logging.warning(f"Vehicle not found for context: {call_number}")
            return jsonify({'error': 'Vehicle not found'}), 404
        logging.debug(f"Vehicle row retrieved: keys={list(vehicle.keys())}")
        try:
            documents = get_vehicle_documents(call_number) or []
            logging.debug(f"Documents fetched: count={len(documents)}")
        except Exception as d_err:
            logging.error(f"Document fetch failed for {call_number}: {d_err}", exc_info=True)
            documents = []
        try:
            from database import get_vehicle_communications
            communications = get_vehicle_communications(call_number)
            logging.debug(f"Communications fetched: count={len(communications)}")
        except Exception as c_err:
            logging.error(f"Comm fetch failed for {call_number}: {c_err}", exc_info=True)
            communications = []

        # Normalize potential sqlite3.Row instances (defensive)
        try:
            import sqlite3 as _sqlite3
            if isinstance(vehicle, _sqlite3.Row):
                vehicle = dict(vehicle)
            norm_docs = []
            for d in documents:
                if isinstance(d, _sqlite3.Row):
                    norm_docs.append(dict(d))
                else:
                    norm_docs.append(d)
            documents = norm_docs
            norm_comms = []
            for c in communications:
                if isinstance(c, _sqlite3.Row):
                    norm_comms.append(dict(c))
                else:
                    norm_comms.append(c)
            communications = norm_comms
        except Exception as norm_err:
            logging.warning(f"Normalization issue for {call_number}: {norm_err}")

        jurisdiction = vehicle.get('jurisdiction') or vehicle.get('location')
        try:
            contact = get_contact_by_jurisdiction(jurisdiction) if jurisdiction else None
        except Exception as contact_err:
            logging.error(f"Contact lookup failed for jurisdiction '{jurisdiction}': {contact_err}")
            contact = None
        # Convert contact if Row
        try:
            import sqlite3 as _sqlite3
            if contact and isinstance(contact, _sqlite3.Row):
                contact = dict(contact)
        except Exception:
            pass

        top_docs = [d for d in documents if (d.get('document_type') or '').upper() == 'TOP']
        latest_top = top_docs[0] if top_docs else None
        top_sent = False
        if latest_top:
            sent_matches = [c for c in communications if c.get('document_id') == latest_top.get('id') and c.get('status') == 'sent']
            top_sent = bool(sent_matches) or bool(latest_top.get('sent_date')) or bool(latest_top.get('sent_via'))

        suggested_actions = []
        tow_date_str = vehicle.get('tow_date')
        due_top_date = None
        if tow_date_str:
            try:
                tow_dt = datetime.strptime(tow_date_str, '%Y-%m-%d')
                due_top_date = tow_dt + timedelta(days=1)
                days_since_tow = (datetime.now() - tow_dt).days
            except Exception:
                due_top_date = None
                days_since_tow = None
        else:
            days_since_tow = None
        now = datetime.now()
        if due_top_date:
            if not latest_top:
                suggested_actions.append({'type': 'generate_top', 'label': 'Generate TOP Form', 'due_date': due_top_date.strftime('%Y-%m-%d'), 'overdue': now > due_top_date, 'status': 'pending'})
            elif latest_top and not top_sent:
                suggested_actions.append({'type': 'send_top', 'label': 'Send TOP Form', 'document_id': latest_top.get('id'), 'due_date': due_top_date.strftime('%Y-%m-%d'), 'overdue': now > due_top_date, 'status': 'generated'})

        # Release notice action: if vehicle status indicates disposition and no RELEASE doc exists
        release_docs = [d for d in documents if (d.get('document_type') or '').upper() == 'RELEASE']
        disposition_statuses = {'Released', 'Scrapped', 'Auctioned', 'Transferred'}
        if vehicle.get('status') in disposition_statuses and not release_docs:
            suggested_actions.append({'type': 'generate_release', 'label': 'Generate Release Notice', 'status': 'pending'})

        comm_sent_by_doc = {c.get('document_id'): True for c in communications if c.get('status') == 'sent'}
        for d in documents:
            d['has_sent_comm'] = bool(comm_sent_by_doc.get(d.get('id')))

        auction_info = []
        try:
            conn = get_db_connection()
            # Detect auction_vehicles schema to decide join columns
            try:
                av_cols = {r[1] for r in conn.execute("PRAGMA table_info(auction_vehicles)").fetchall()}
            except Exception:
                av_cols = set()
            # Prefer vehicle_id join if present, else fall back to vehicle_call_number
            if 'vehicle_id' in av_cols:
                auction_query = (
                    "SELECT a.id, a.auction_date, a.auction_house, a.status "
                    "FROM auction_vehicles av "
                    "JOIN auctions a ON av.auction_id = a.id "
                    "JOIN vehicles v ON av.vehicle_id = v.id "
                    "WHERE v.towbook_call_number = ?"
                )
            else:
                auction_query = (
                    "SELECT a.id, a.auction_date, a.auction_house, a.status "
                    "FROM auction_vehicles av "
                    "JOIN auctions a ON av.auction_id = a.id "
                    "JOIN vehicles v ON av.vehicle_call_number = v.towbook_call_number "
                    "WHERE v.towbook_call_number = ?"
                )
            rows = conn.execute(auction_query, (call_number,)).fetchall()
            auction_info = [dict(r) for r in rows]
        except Exception as e2:
            logging.error(f"Auction info fetch error for {call_number}: {e2}")

        logging.debug(f"Context assembled for {call_number}: docs={len(documents)}, comms={len(communications)}, auctions={len(auction_info)}, actions={len(suggested_actions)}")
        return jsonify({
            'vehicle': vehicle,
            'documents': documents,
            'communications': communications,
            'contact': contact,
            'suggested_actions': suggested_actions,
            'auctions': auction_info,
            'metrics': {'days_since_tow': days_since_tow},
            'assumptions': {'top_due_rule': 'Assumed TOP must be generated and sent within 1 day of tow date.'}
        })
    except Exception as e:
        logging.error(f"Error building vehicle context for {call_number}: {e}", exc_info=True)
        # Temporarily expose error detail to help diagnose front-end issue; remove in production
        return jsonify({'error': 'Failed to build context', 'detail': str(e), 'call_number': call_number}), 500

# DEBUG ONLY: unauthenticated quick context check (remove in production)
@app.route('/debug/context/<call_number>')
def debug_vehicle_context(call_number):
    return ui_vehicle_context(call_number)

@app.route('/ui/auctions', methods=['GET'])
@login_required
def ui_list_auctions():
    try:
        conn = get_db_connection()
        rows = conn.execute("SELECT id, auction_date, auction_house, status FROM auctions ORDER BY auction_date DESC LIMIT 200").fetchall()
        return jsonify({'auctions':[dict(r) for r in rows]})
    except Exception as e:
        logging.error(f"Error listing auctions: {e}", exc_info=True)
        return jsonify({'error':'Failed to list auctions'}), 500

@app.route('/ui/auctions/<int:auction_id>/assign/<call_number>', methods=['POST'])
@login_required
def ui_assign_vehicle_to_auction(auction_id, call_number):
    try:
        vehicle = get_vehicle_by_call_number(call_number)
        if not vehicle:
            return jsonify({'error':'Vehicle not found'}), 404
        conn = get_db_connection()
        # Check auction exists
        a = conn.execute("SELECT id FROM auctions WHERE id = ?", (auction_id,)).fetchone()
        if not a:
            return jsonify({'error':'Auction not found'}), 404
        # Determine auction_vehicles schema
        av_cols = {r[1] for r in conn.execute("PRAGMA table_info(auction_vehicles)").fetchall()}
        # Build insert based on available columns
        insert_cols = ['auction_id']
        values = [auction_id]
        placeholders = ['?']
        # vehicle_id path if both vehicle_id column and numeric id present
        if 'vehicle_id' in av_cols and 'id' in vehicle.keys():
            insert_cols.append('vehicle_id'); values.append(vehicle['id']); placeholders.append('?')
        # Always include vehicle_call_number if column exists
        if 'vehicle_call_number' in av_cols:
            insert_cols.append('vehicle_call_number'); values.append(call_number); placeholders.append('?')
        # Optional lot_number (none for now)
        if 'lot_number' in av_cols:
            insert_cols.append('lot_number'); values.append(None); placeholders.append('?')
        if 'status' in av_cols:
            insert_cols.append('status'); values.append('Scheduled'); placeholders.append('?')
        insert_sql = f"INSERT OR IGNORE INTO auction_vehicles ({', '.join(insert_cols)}) VALUES ({', '.join(placeholders)})"
        conn.execute(insert_sql, tuple(values))
        conn.commit()
        log_action('Vehicle Assigned To Auction', current_user.username, f"Vehicle {call_number} -> auction {auction_id}")
        return jsonify({'status':'assigned'})
    except Exception as e:
        logging.error(f"Error assigning vehicle {call_number} to auction {auction_id}: {e}", exc_info=True)
        return jsonify({'error':'Failed to assign vehicle','detail':str(e)}), 500

@app.route('/ui/auctions/<int:auction_id>/documents', methods=['POST'])
@login_required
def ui_upload_auction_document(auction_id):
    try:
        conn = get_db_connection()
        a = conn.execute("SELECT id FROM auctions WHERE id = ?", (auction_id,)).fetchone()
        if not a:
            return jsonify({'error':'Auction not found'}), 404
        if 'documents' not in request.files:
            return jsonify({'error':'No files provided'}), 400
        files = request.files.getlist('documents')
        saved = []
        for f in files:
            if not f or not f.filename:
                continue
            filename = secure_filename(f.filename)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            unique = f"{timestamp}_{filename}"
            path = os.path.join(app.config['DOCUMENT_FOLDER'], unique)
            f.save(path)
            from database import add_auction_document
            doc_id = add_auction_document(auction_id, filename, request.form.get('document_type','Auction Doc'), request.form.get('document_category','General'), unique, current_user.username)
            saved.append({'id': doc_id, 'name': filename})
        return jsonify({'uploaded': saved, 'count': len(saved)})
    except Exception as e:
        logging.error(f"Error uploading auction document for auction {auction_id}: {e}", exc_info=True)
        return jsonify({'error':'Failed to upload documents'}), 500

@app.route('/ui/auctions/<int:auction_id>/documents', methods=['GET'])
@login_required
def ui_list_auction_documents(auction_id):
    try:
        conn = get_db_connection()
        a = conn.execute("SELECT id FROM auctions WHERE id = ?", (auction_id,)).fetchone()
        if not a:
            return jsonify({'error':'Auction not found'}), 404
        rows = conn.execute("SELECT id, document_name, document_type, document_category, file_path, uploaded_at FROM documents WHERE auction_id = ? ORDER BY uploaded_at DESC", (auction_id,)).fetchall()
        docs = [dict(r) for r in rows]
        return jsonify({'documents': docs, 'count': len(docs)})
    except Exception as e:
        logging.error(f"Error listing auction documents for auction {auction_id}: {e}", exc_info=True)
        return jsonify({'error':'Failed to list documents'}), 500
    

@app.route('/api/vehicles')
@api_login_required
def api_get_vehicles():
    """Fetch vehicles based on status, sorting, and other filters"""
    try:
        status_filter_param = request.args.get('status', None)
        sort_column = request.args.get('sort', 'tow_date')
        sort_direction = request.args.get('direction', 'desc')
        include_tracking = request.args.get('include_tracking', 'false').lower() == 'true'

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

        # Add tracking information if requested
        if include_tracking:
            from vehicle_tracker import get_vehicle_tracker
            tracker = get_vehicle_tracker()
            for vehicle in vehicles_data:
                tracking_info = tracker.get_vehicle_tracking_info(vehicle.get('towbook_call_number'))
                if tracking_info:
                    vehicle['tracking_info'] = {
                        'compliance': {
                            'is_auction_ready': tracking_info.compliance.is_auction_ready(),
                            'missing_requirements': tracking_info.compliance.get_missing_requirements()
                        },
                        'next_action': tracking_info.next_action,
                        'urgency_level': tracking_info.urgency_level,
                        'progress_percentage': tracking_info.progress_percentage,
                        'days_in_custody': tracking_info.days_in_custody,
                        'auction_eligible_date': tracking_info.auction_eligible_date.isoformat() if tracking_info.auction_eligible_date else None,
                        'is_auction_eligible': tracking_info.is_auction_eligible
                    }

        logging.info(f"Found {len(vehicles_data)} vehicles matching criteria for {status_filter_param}")
        logging.info(f"Statuses queried: {statuses_to_query}")
        logging.info(f"First few vehicles: {[v.get('towbook_call_number', 'N/A') for v in vehicles_data[:5]]}")
        
        # URGENT DEBUG: Check what we're about to return
        json_response = jsonify(vehicles_data)
        logging.error(f"URGENT DEBUG: About to return JSON with {len(vehicles_data)} vehicles")
        logging.error(f"URGENT DEBUG: Type of vehicles_data: {type(vehicles_data)}")
        if vehicles_data:
            logging.error(f"URGENT DEBUG: First vehicle call number: {vehicles_data[0].get('towbook_call_number', 'N/A')}")
        
        return json_response
    except Exception as e:
        logging.error(f"Error fetching vehicles: {e}", exc_info=True)
        return jsonify({"error": f"Failed to fetch vehicles: {str(e)}"}), 500

@app.route('/api/vehicles/<vehicle_id>', methods=['GET', 'PUT', 'DELETE'])
@api_login_required
def vehicle_detail_api(vehicle_id):
    if request.method == 'GET':
        try:
            vehicle = get_vehicle_by_call_number(vehicle_id)
            if vehicle:
                return jsonify(dict(vehicle))
            else:
                return jsonify({"error": "Vehicle not found"}), 404
        except Exception as e:
            logging.error(f"Error fetching vehicle details for call number {vehicle_id}: {e}", exc_info=True)
            return jsonify({"error": f"Failed to fetch vehicle details: {str(e)}"}), 500
    elif request.method == 'PUT':
        try:
            existing_vehicle = get_vehicle_by_call_number(vehicle_id)
            if not existing_vehicle:
                return jsonify({"error": "Vehicle not found"}), 404
            data = request.json
            if not data:
                return jsonify({"error": "No data provided"}), 400
            success = update_vehicle_by_call_number(vehicle_id, data)
            if success:
                log_action('Vehicle Updated', current_user.id if hasattr(current_user, 'id') else 'System', f"Vehicle {vehicle_id} updated: {', '.join(data.keys())}")
                return jsonify({"message": "Vehicle updated successfully"}), 200
            else:
                return jsonify({"error": "Failed to update vehicle"}), 500
        except Exception as e:
            logging.error(f"Error updating vehicle {vehicle_id}: {e}", exc_info=True)
            return jsonify({"error": f"Server error: {str(e)}"}), 500
    elif request.method == 'DELETE':
        try:
            existing_vehicle = get_vehicle_by_call_number(vehicle_id)
            if not existing_vehicle:
                return jsonify({"error": "Vehicle not found"}), 404
            from database import delete_vehicle_by_call_number
            success = delete_vehicle_by_call_number(vehicle_id)
            if success:
                log_action('Vehicle Deleted', current_user.id if hasattr(current_user, 'id') else 'System', f"Vehicle deleted: call number {vehicle_id}")
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
        # Only close the connection if it's not managed by Flask's g object
        if db_conn and (not hasattr(g, '_database') or g._database != db_conn):
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

@app.route('/debug_frontend.html')
def debug_frontend():
    """Serve the debug frontend test page"""
    return send_file('debug_frontend.html')

@app.route('/simple_vehicle_test.html')
def simple_vehicle_test():
    """Serve the simple vehicle test page"""
    return send_file('simple_vehicle_test.html')

@app.route('/js_debug_test.html')
def js_debug_test():
    """Serve the JavaScript debug test page"""
    return send_file('js_debug_test.html')

@app.route('/comprehensive_debug.html')
def comprehensive_debug():
    """Serve the comprehensive debug page"""
    return send_file('comprehensive_debug.html')

@app.route('/js-test')
def js_execution_test():
    """JavaScript execution diagnostic test page"""
    return send_from_directory('.', 'js_execution_test.html')

@app.route('/direct-vehicle-test')
def direct_vehicle_test():
    """Direct vehicle data test page"""
    return send_from_directory('.', 'direct_vehicle_test.html')

@app.route('/frontend-debug-test')
def frontend_debug_test():
    """Frontend debug test page"""
    return send_from_directory('.', 'frontend_debug_test.html')

# === PWA Static File Routes ===
@app.route('/pwa/', defaults={'path': 'index.html'})
@app.route('/pwa/<path:path>')
def serve_pwa(path):
    # Serve PWA files from the static/pwa directory
    return send_from_directory(
        os.path.join(app.root_path, 'static', 'pwa'),
        path
    )

# Blueprints are already registered in register_api_routes function

if __name__ == "__main__":
    PORT = 5001
    if os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        logging.info(f"Preparing to start Flask app on port {PORT} (main process)")
        try:
            kill_command = f"fuser -k -n tcp {PORT}"
            logging.info(f"Attempting to free port {PORT} by running: '{kill_command}'")
            result = subprocess.run(kill_command, shell=True, capture_output=True, text=True, check=False)
            logging.info(f"fuser subprocess.run finished. RC: {result.returncode}. Stdout: '{result.stdout.strip()}', Stderr: '{result.stderr.strip()}'")
            if result.returncode == 0:
                logging.info(f"fuser command likely succeeded in signalling process(es) on port {PORT}.")
            elif "command not found" in result.stderr.lower() or "not found" in result.stderr.lower() or result.returncode == 127:
                logging.warning(f"fuser command not found. Please ensure 'psmisc' package (which provides fuser) is installed. Stderr: {result.stderr.strip()}")
            elif result.returncode == 1:
                logging.info(f"fuser: No process found on port {PORT} (return code 1). This is normal if the port was already free.")
            else:
                logging.warning(f"fuser command may have encountered an issue. Return code: {result.returncode}. Stdout: '{result.stdout.strip()}', Stderr: '{result.stderr.strip()}'")
            logging.info("Waiting 2 seconds for port to be fully released...")
            time.sleep(2)
        except FileNotFoundError:
            logging.warning("fuser command not found (FileNotFoundError during subprocess.run). Please ensure 'psmisc' package is installed.")
        except Exception as e:
            logging.error(f"Error trying to free port {PORT} using fuser: {e}", exc_info=True)
    else:
        logging.info(f"Flask app reloader active, skipping fuser command for port {PORT}.")
    logging.info("Starting Flask application...")
    app.run(host="0.0.0.0", port=PORT, debug=True)
    