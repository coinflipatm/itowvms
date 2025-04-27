from flask import Flask, render_template, send_file, request, jsonify, redirect, url_for
from database import (init_db, get_vehicles_by_status, update_vehicle_status, 
                      update_vehicle, insert_vehicle, get_db_connection, check_and_update_statuses, 
                      get_logs, toggle_archive_status, create_auction, get_pending_notifications,
                      mark_notification_sent, get_contact_by_jurisdiction, save_contact, get_contacts,
                      get_vehicles)
from generator import PDFGenerator
from utils import (generate_complaint_number, release_vehicle, log_action, 
                   ensure_logs_table_exists, setup_logging, get_status_filter, calculate_newspaper_ad_date,
                   calculate_storage_fees, determine_jurisdiction, send_email_notification, 
                   send_sms_notification, send_fax_notification, is_valid_email, is_valid_phone,
                   generate_certified_mail_number, is_eligible_for_tr208, calculate_tr208_timeline)
from flask_login import login_required, current_user
from auth import auth_bp, login_manager, init_auth_db, User
from datetime import datetime, timedelta
import threading
import os
import logging
import time
import socket
import json
from werkzeug.utils import secure_filename
from io import StringIO, BytesIO
import csv
import re

# Configure logging
setup_logging()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev_key_change_this_in_production')

# Initialize Flask-Login
login_manager.init_app(app)
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'

# Register authentication blueprint
app.register_blueprint(auth_bp)

# Initialize components
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

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def allowed_document(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_DOCUMENT_EXTENSIONS

# Check if port is available
def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("0.0.0.0", port))
            return False
        except OSError:
            return True

def run_status_checks():
    while True:
        try:
            check_and_update_statuses()
            log_action("SYSTEM", "AUTO", "Ran automated status checks")
            time.sleep(3600)  # Check every hour
        except Exception as e:
            logging.error(f"Status check error: {e}")
            time.sleep(60)  # Retry after a minute if there's an error

@app.route('/')
@login_required
def index():
    status = request.args.get('status', 'New')
    return render_template('index.html', status=status)

@app.route('/admin_users')
@login_required
def admin_users():
    # Check if user is admin
    if current_user.role != 'admin':
        return redirect(url_for('index'))
    return render_template('admin_users.html')

@app.route('/create_invite')
@login_required
def create_invite():
    # Check if user is admin
    if current_user.role != 'admin':
        return redirect(url_for('index'))
    return render_template('create_invite.html')

@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html')

@app.route('/logs')
@login_required
def logs_page():
    return render_template('logs.html')

@app.route('/invitations')
@login_required
def invitations():
    # Check if user is admin
    if current_user.role != 'admin':
        return redirect(url_for('index'))
    return render_template('invitations.html')

@app.route('/api/vehicles')
@login_required
def api_get_vehicles():
    try:
        status_type = request.args.get('status_type')
        count_by_status = request.args.get('count_by_status') == 'true'
        auction_only = request.args.get('auction_only') == 'true'
        call_number = request.args.get('call_number')
        sort_column = request.args.get('sort')
        sort_direction = request.args.get('direction', 'desc')
        
        logging.info(f"API request: status_type={status_type}, sort={sort_column}, direction={sort_direction}")
        
        if count_by_status:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT status, COUNT(*) as count FROM vehicles GROUP BY status")
            status_breakdown = {row[0] or 'undefined': row[1] for row in cursor.fetchall()}
            counts = {
                'new': status_breakdown.get('New', 0),
                'topGenerated': status_breakdown.get('TOP Generated', 0),
                'tr52Ready': status_breakdown.get('TR52 Ready', 0),
                'tr208Ready': status_breakdown.get('TR208 Ready', 0),
                'readyAuction': status_breakdown.get('Ready for Auction', 0),
                'readyScrap': status_breakdown.get('Ready for Scrap', 0),
                'auction': status_breakdown.get('Auction', 0),
                'scrapped': status_breakdown.get('Scrapped', 0),
                'released': status_breakdown.get('Released', 0),
                'completed': sum([
                    status_breakdown.get('Released', 0),
                    status_breakdown.get('Scrapped', 0),
                    status_breakdown.get('Auctioned', 0),
                    status_breakdown.get('Transferred', 0)
                ]),
                'active': cursor.execute("SELECT COUNT(*) FROM vehicles WHERE archived = 0").fetchone()[0],
                'total': cursor.execute("SELECT COUNT(*) FROM vehicles").fetchone()[0]
            }
            conn.close()
            return jsonify({'status': 'success', 'counts': counts, 'statusBreakdown': status_breakdown})
        
        if call_number:
            conn = get_db_connection()
            vehicle = conn.execute("SELECT * FROM vehicles WHERE towbook_call_number = ? AND archived = 0", (call_number,)).fetchone()
            conn.close()
            vehicle_data = dict(vehicle) if vehicle else {}
            for key in vehicle_data:
                vehicle_data[key] = vehicle_data[key] if vehicle_data[key] else 'N/A'
            return jsonify([vehicle_data] if vehicle else [])
        
        if auction_only:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM vehicles WHERE status = 'Auction' AND archived = 0 ORDER BY tow_date DESC")
            vehicles = [dict(v) for v in cursor.fetchall()]
            conn.close()
            for vehicle in vehicles:
                for key in vehicle:
                    vehicle[key] = vehicle[key] if vehicle[key] else 'N/A'
            return jsonify(vehicles)
        
        if status_type:
            vehicles = get_vehicles_by_status(status_type, sort_column, sort_direction)
            logging.info(f"Found {len(vehicles)} vehicles for status type {status_type}")
        else:
            vehicles = get_vehicles('active', sort_column, sort_direction)
            logging.info(f"Found {len(vehicles)} active vehicles")
    
        for vehicle in vehicles:
            for key in vehicle:
                vehicle[key] = vehicle[key] if vehicle[key] else 'N/A'
            
            # Safely process dates and calculations
            if 'tow_date' in vehicle and vehicle['tow_date'] != 'N/A':
                try:
                    tow_date = datetime.strptime(vehicle['tow_date'], '%Y-%m-%d')
                    vehicle['days_since_tow'] = (datetime.now() - tow_date).days
                    
                    # Calculate storage fees
                    storage_fee, storage_days = calculate_storage_fees(vehicle['tow_date'])
                    vehicle['storage_fee'] = storage_fee
                    vehicle['storage_days'] = storage_days
                    
                    # Process status-specific dates safely
                    if vehicle['status'] == 'TOP Generated':
                        # Handle TR208 eligible vehicles
                        if vehicle.get('tr208_eligible') == 1 and vehicle.get('tr208_available_date') != 'N/A':
                            try:
                                tr208_date = datetime.strptime(vehicle['tr208_available_date'], '%Y-%m-%d')
                                vehicle['days_until_next_step'] = max(0, (tr208_date - datetime.now()).days)
                                vehicle['next_step_label'] = 'days until TR208 Ready'
                            except (ValueError, TypeError):
                                vehicle['days_until_next_step'] = 0
                                vehicle['next_step_label'] = 'days until TR208 Ready'
                        # Handle TR52 vehicles
                        elif vehicle.get('tr52_available_date') != 'N/A':
                            try:
                                tr52_date = datetime.strptime(vehicle['tr52_available_date'], '%Y-%m-%d')
                                vehicle['days_until_next_step'] = max(0, (tr52_date - datetime.now()).days)
                                vehicle['next_step_label'] = 'days until TR52 Ready'
                            except (ValueError, TypeError):
                                vehicle['days_until_next_step'] = 0
                                vehicle['next_step_label'] = 'days until TR52 Ready'
                    
                    # Handle TR52/TR208 Ready
                    elif vehicle['status'] in ['TR52 Ready', 'TR208 Ready']:
                        vehicle['next_step_label'] = f'days since {vehicle["status"]}'
                        vehicle['days_until_next_step'] = vehicle.get('days_until_next_step', 0)
                    
                    # Handle Ready for Scrap
                    elif vehicle['status'] == 'Ready for Scrap' and vehicle.get('estimated_date') != 'N/A':
                        try:
                            estimated_date = datetime.strptime(vehicle['estimated_date'], '%Y-%m-%d')
                            vehicle['days_until_next_step'] = max(0, (estimated_date - datetime.now()).days)
                            vehicle['next_step_label'] = 'days until legal scrap date'
                        except (ValueError, TypeError):
                            vehicle['days_until_next_step'] = 0
                            vehicle['next_step_label'] = 'days until legal scrap date'
                    
                    # Handle Ready for Auction
                    elif vehicle['status'] == 'Ready for Auction' and vehicle.get('auction_date') != 'N/A':
                        try:
                            auction_date = datetime.strptime(vehicle['auction_date'], '%Y-%m-%d')
                            vehicle['days_until_auction'] = max(0, (auction_date - datetime.now()).days)
                            vehicle['next_step_label'] = 'days until auction'
                        except (ValueError, TypeError):
                            vehicle['days_until_auction'] = 0
                            vehicle['next_step_label'] = 'days until auction'
                            
                except Exception as e:
                    logging.warning(f"Date processing error for {vehicle['towbook_call_number']}: {e}")
                    # Ensure default values if date processing fails
                    vehicle['days_since_tow'] = 0
                    vehicle['storage_fee'] = 0
                    vehicle['storage_days'] = 0
        
        return jsonify(vehicles)
    except Exception as e:
        logging.error(f"Error in api_get_vehicles: {e}")
        return jsonify({'error': str(e)}), 500
    
@app.route('/api/vehicles/<call_number>', methods=['PUT'])
@login_required
def update_vehicle_api(call_number):
    try:
        data = request.json
        for key in data:
            if data[key] is None or data[key] == '':
                data[key] = 'N/A'
                
        # Apply field name mapping before updating
        from utils import map_field_names
        mapped_data = map_field_names(data)
        
        # If we're updating jurisdiction, check if it's set to detect and update
        if 'location' in mapped_data and mapped_data.get('jurisdiction') == 'detect':
            location = mapped_data.get('location')
            if location and location != 'N/A':
                mapped_data['jurisdiction'] = determine_jurisdiction(location)
                logging.info(f"Detected jurisdiction: {mapped_data['jurisdiction']} from location: {location}")
                
        success, message = update_vehicle(call_number, mapped_data)
        if success:
            log_action("UPDATE", current_user.username, f"Vehicle {call_number} details updated: {json.dumps(mapped_data)}")
            return jsonify({'status': 'success', 'message': message})
        return jsonify({'status': 'error', 'message': message}), 400
    except Exception as e:
        logging.error(f"Error updating vehicle {call_number}: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/vehicles/delete/<call_number>', methods=['DELETE'])
@login_required
def delete_vehicle(call_number):
    try:
        # Check if user is admin
        if current_user.role != 'admin':
            return jsonify({'status': 'error', 'message': 'Admin privileges required for this action'}), 403
            
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM vehicles WHERE towbook_call_number = ?", (call_number,))
        if cursor.fetchone()[0] == 0:
            conn.close()
            return jsonify({'status': 'error', 'message': 'Vehicle not found'}), 404
        cursor.execute("DELETE FROM logs WHERE vehicle_id = ?", (call_number,))
        cursor.execute("DELETE FROM police_logs WHERE vehicle_id = ?", (call_number,))
        cursor.execute("DELETE FROM documents WHERE vehicle_id = ?", (call_number,))
        cursor.execute("DELETE FROM notifications WHERE vehicle_id = ?", (call_number,))
        cursor.execute("DELETE FROM vehicles WHERE towbook_call_number = ?", (call_number,))
        conn.commit()
        conn.close()
        log_action("DELETE", current_user.username, f"Vehicle {call_number} permanently deleted")
        return jsonify({'status': 'success', 'message': f'Vehicle {call_number} deleted'})
    except Exception as e:
        logging.error(f"Error deleting vehicle {call_number}: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/vehicles/add', methods=['POST'])
@login_required
def add_vehicle():
    try:
        data = request.json
        if not data.get('towbook_call_number'):
            data['towbook_call_number'] = f"MANUAL-{int(time.time())}"
        if not data.get('status'):
            data['status'] = 'New'
        if 'complaint_number' not in data or not data['complaint_number'] or data['complaint_number'] == 'N/A':
            complaint_number, sequence, year = generate_complaint_number()
            data['complaint_number'] = complaint_number
            data['complaint_sequence'] = sequence
            data['complaint_year'] = year
            
        # Auto-detect jurisdiction if location provided
        if data.get('location') and (not data.get('jurisdiction') or data['jurisdiction'] == 'detect'):
            data['jurisdiction'] = determine_jurisdiction(data['location'])
            logging.info(f"Auto-detected jurisdiction: {data['jurisdiction']} from location: {data['location']}")
            
        # Initialize photo_paths if not provided
        if 'photo_paths' not in data or not data['photo_paths']:
            data['photo_paths'] = json.dumps([])
            
        # Clean data - ensure no empty values
        for key in data:
            if data[key] is None or data[key] == '':
                data[key] = 'N/A'
                
        success, message = insert_vehicle(data)
        if success:
            log_action("INSERT", current_user.username, f"New vehicle added: {json.dumps(data)}")
            return jsonify({'status': 'success', 'message': message})
        return jsonify({'status': 'error', 'message': message}), 400
    except Exception as e:
        logging.error(f"Error adding vehicle: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/update-status/<call_number>', methods=['POST'])
@login_required
def api_update_status(call_number):
    try:
        data = request.get_json()
        new_status = data.get('status')
        if not new_status:
            return jsonify({"error": "No status provided"}), 400
        new_status = new_status.replace('_', ' ')
        logging.info(f"Attempting status update for {call_number} to {new_status}")
        success = update_vehicle_status(call_number, new_status, data)
        if success:
            logging.info(f"Status updated: {call_number} => {new_status}")
            log_action("STATUS_CHANGE", current_user.username, f"Vehicle {call_number} status updated to {new_status}")
            return jsonify({"status": "success", "message": "Status updated"}), 200
        else:
            logging.error(f"Failed to update status for {call_number} to {new_status}")
            return jsonify({"error": "Status update failed"}), 500
    except Exception as e:
        logging.error(f"Error in api_update_status: {e}")
        return jsonify({"error": str(e)}), 500
    
@app.route('/api/check-statuses', methods=['POST'])
@login_required
def check_statuses():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT towbook_call_number FROM vehicles WHERE status = 'Auction'")
        auction_vehicles = cursor.fetchall()
        fixed_count = 0
        if auction_vehicles:
            logging.info(f"Found {len(auction_vehicles)} vehicles with incorrect 'Auction' status")
            for vehicle in auction_vehicles:
                call_number = vehicle['towbook_call_number']
                cursor.execute("""
                    UPDATE vehicles 
                    SET status = ?, 
                        last_updated = ?
                    WHERE towbook_call_number = ?
                """, ('Ready for Auction', datetime.now().strftime('%Y-%m-%d %H:%M:%S'), call_number))
                today = datetime.now().date()
                days_to_monday = (7 - today.weekday()) % 7
                if days_to_monday < 3:
                    days_to_monday += 7
                auction_date = today + timedelta(days=days_to_monday)
                cursor.execute("""
                    UPDATE vehicles
                    SET auction_date = ?,
                        days_until_auction = ?
                    WHERE towbook_call_number = ?
                """, (auction_date.strftime('%Y-%m-%d'), days_to_monday, call_number))
                log_action("STATUS_CORRECTION", current_user.username, f"Vehicle {call_number} changed incorrect status 'Auction' to 'Ready for Auction'")
                logging.info(f"Fixed status for vehicle {call_number}")
                fixed_count += 1
        conn.commit()
        conn.close()
        return jsonify({'status': 'success', 'fixed': fixed_count})
    except Exception as e:
        logging.error(f"Error checking statuses: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/upload-photo/<call_number>', methods=['POST'])
@login_required
def upload_photo(call_number):
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        ext = filename.rsplit('.', 1)[1].lower()
        new_filename = f"{call_number}_{timestamp}.{ext}"
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], new_filename)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        file.save(file_path)
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT photo_paths FROM vehicles WHERE towbook_call_number = ?", (call_number,))
        result = cursor.fetchone()
        photo_paths = []
        if result and result['photo_paths']:
            try:
                photo_paths = json.loads(result['photo_paths'])
            except json.JSONDecodeError:
                photo_paths = []
        photo_paths.append(new_filename)
        cursor.execute("UPDATE vehicles SET photo_paths = ? WHERE towbook_call_number = ?",
                       (json.dumps(photo_paths), call_number))
        conn.commit()
        conn.close()
        log_action("PHOTO_UPLOAD", current_user.username, f"Vehicle {call_number} photo uploaded: {new_filename}")
        return jsonify({'status': 'success', 'filename': new_filename})
    return jsonify({'error': 'File type not allowed'}), 400

@app.route('/api/police-logs/<call_number>', methods=['GET'])
@login_required
def get_police_logs(call_number):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM police_logs WHERE vehicle_id = ? ORDER BY communication_date DESC", (call_number,))
    logs = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(logs)

@app.route('/api/police-logs/<call_number>', methods=['POST'])
@login_required
def add_police_log(call_number):
    data = request.json
    communication_date = data.get('communication_date', datetime.now().strftime('%Y-%m-%d'))
    communication_type = data.get('communication_type')
    notes = data.get('notes')
    recipient = data.get('recipient', 'N/A')
    contact_method = data.get('contact_method', 'N/A')
    
    if not communication_type or not notes:
        return jsonify({'error': 'Missing required fields'}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO police_logs 
        (vehicle_id, communication_date, communication_type, notes, recipient, contact_method) 
        VALUES (?, ?, ?, ?, ?, ?)
    """, (call_number, communication_date, communication_type, notes, recipient, contact_method))
    conn.commit()
    conn.close()
    log_action("POLICE_LOG", current_user.username, f"Vehicle {call_number} police communication log added: {communication_type}")
    return jsonify({'status': 'success'})

@app.route('/api/compliance-report', methods=['GET'])
@login_required
def compliance_report():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT towbook_call_number, tow_date, top_form_sent_date, tr52_available_date, 
               tr208_available_date, status, auction_date, release_date, photo_paths, 
               sale_amount, fees, net_proceeds, jurisdiction, complaint_number, release_reason,
               tr208_eligible, inoperable, damage_extent
        FROM vehicles WHERE archived = 0
    """)
    vehicles = cursor.fetchall()
    conn.close()
    
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['Call Number', 'Complaint #', 'Jurisdiction', 'Tow Date', 'Notice Sent Date', 
                    'TR52/TR208 Date', 'Status', 'TR208 Eligible', 'Auction Date', 'Release Date', 
                    'Release Reason', 'Photo Count', 'Sale Amount', 'Fees', 'Net Proceeds'])
    for vehicle in vehicles:
        photo_count = 0
        if vehicle['photo_paths']:
            try:
                photo_count = len(json.loads(vehicle['photo_paths']))
            except:
                photo_count = 0
                
        writer.writerow([
            vehicle['towbook_call_number'] or 'N/A', 
            vehicle['complaint_number'] or 'N/A',
            vehicle['jurisdiction'] or 'N/A',
            vehicle['tow_date'] or 'N/A', 
            vehicle['top_form_sent_date'] or 'N/A', 
            vehicle['tr52_available_date'] or vehicle['tr208_available_date'] or 'N/A', 
            vehicle['status'] or 'N/A', 
            'Yes' if vehicle['tr208_eligible'] == 1 else 'No',
            vehicle['auction_date'] or 'N/A', 
            vehicle['release_date'] or 'N/A', 
            vehicle['release_reason'] or 'N/A',
            photo_count, 
            vehicle['sale_amount'] or 0, 
            vehicle['fees'] or 0, 
            vehicle['net_proceeds'] or 0
        ])
    output.seek(0)
    return send_file(
        BytesIO(output.getvalue().encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        download_name='compliance_report.csv'
    )

@app.route('/api/compliance-report/pdf', methods=['GET'])
@login_required
def compliance_report_pdf():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT towbook_call_number, complaint_number, tow_date, top_form_sent_date, 
               tr52_available_date, tr208_available_date, status, auction_date, release_date, 
               photo_paths, sale_amount, fees, net_proceeds, jurisdiction, tr208_eligible
        FROM vehicles
    """)
    vehicles = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    # Generate PDF report
    pdf_path = os.path.join(app.config['GENERATED_FOLDER'], f"compliance_report_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf")
    success, error = pdf_gen.generate_compliance_report(vehicles, pdf_path)
    
    if success:
        return send_file(pdf_path, as_attachment=True)
    else:
        return jsonify({'error': error}), 500

@app.route('/api/upload-document/<call_number>', methods=['POST'])
@login_required
def upload_document(call_number):
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    document_type = request.form.get('type', 'Other')
    
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
        
    if file and allowed_document(file.filename):
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        ext = filename.rsplit('.', 1)[1].lower()
        new_filename = f"{document_type}_{call_number}_{timestamp}.{ext}"
        file_path = os.path.join(app.config['DOCUMENT_FOLDER'], new_filename)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        file.save(file_path)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO documents 
            (vehicle_id, type, filename, upload_date) 
            VALUES (?, ?, ?, ?)
        """, (call_number, document_type, new_filename, datetime.now().strftime('%Y-%m-%d')))
        
        # Add a police log entry for the document
        cursor.execute("""
            INSERT INTO police_logs 
            (vehicle_id, communication_date, communication_type, notes) 
            VALUES (?, ?, ?, ?)
        """, (
            call_number,
            datetime.now().strftime('%Y-%m-%d'),
            f"{document_type} Document",
            f"{document_type} document uploaded: {new_filename}"
        ))
        
        conn.commit()
        conn.close()
        
        log_action("DOCUMENT_UPLOAD", current_user.username, f"Vehicle {call_number} {document_type} document uploaded: {new_filename}")
        return jsonify({'status': 'success', 'filename': new_filename})
    
    return jsonify({'error': 'File type not allowed'}), 400

@app.route('/api/upload-tr52/<call_number>', methods=['POST'])
@login_required
def upload_tr52(call_number):
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    if file and allowed_document(file.filename):
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        ext = filename.rsplit('.', 1)[1].lower()
        new_filename = f"TR52_{call_number}_{timestamp}.{ext}"
        file_path = os.path.join(app.config['DOCUMENT_FOLDER'], new_filename)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        file.save(file_path)
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO documents (vehicle_id, type, filename, upload_date) VALUES (?, ?, ?, ?)",
                       (call_number, 'TR52', new_filename, datetime.now().strftime('%Y-%m-%d')))
        cursor.execute("INSERT INTO police_logs (vehicle_id, communication_date, communication_type, notes) VALUES (?, ?, ?, ?)",
                       (call_number, datetime.now().strftime('%Y-%m-%d'), 'TR52 Amended', 'Amended TR52 uploaded'))
        conn.commit()
        conn.close()
        log_action("TR52_UPLOAD", current_user.username, f"Vehicle {call_number} amended TR52 uploaded: {new_filename}")
        return jsonify({'status': 'success', 'filename': new_filename})
    return jsonify({'error': 'File type not allowed'}), 400

@app.route('/api/documents/<call_number>', methods=['GET'])
@login_required
def get_documents(call_number):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT type, filename, upload_date FROM documents WHERE vehicle_id = ? ORDER BY upload_date DESC",
                   (call_number,))
    documents = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(documents)

@app.route('/api/pending-notifications', methods=['GET'])
@login_required
def pending_notifications():
    notifications = get_pending_notifications()
    return jsonify(notifications)

@app.route('/api/notification/<notification_id>/send', methods=['POST'])
@login_required
def send_notification(notification_id):
    try:
        data = request.json
        method = data.get('method', 'email')
        recipient = data.get('recipient', 'N/A')
        
        if not notification_id:
            return jsonify({'error': 'No notification ID provided'}), 400
            
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get notification details
        cursor.execute("""
            SELECT n.*, v.* 
            FROM notifications n
            JOIN vehicles v ON n.vehicle_id = v.towbook_call_number
            WHERE n.id = ?
        """, (notification_id,))
        notification = cursor.fetchone()
        
        if not notification:
            conn.close()
            return jsonify({'error': 'Notification not found'}), 404
            
        # Get contact details based on jurisdiction
        jurisdiction = notification['jurisdiction']
        contact = get_contact_by_jurisdiction(jurisdiction)
        
        if not contact and method != 'manual':
            conn.close()
            return jsonify({'error': f'No contact found for jurisdiction: {jurisdiction}'}), 400
            
        # Prepare notification content
        vehicle_id = notification['vehicle_id']
        notification_type = notification['notification_type']
        
        # Generate document if needed
        document_path = None
        if notification_type == 'TOP':
            pdf_path = os.path.join(app.config['GENERATED_FOLDER'], f"TOP_{vehicle_id}.pdf")
            success, error = pdf_gen.generate_top(dict(notification), pdf_path)
            if success:
                document_path = pdf_path
                
        elif notification_type == 'TR52':
            pdf_path = os.path.join(app.config['GENERATED_FOLDER'], f"TR52_{vehicle_id}.pdf")
            success, error = pdf_gen.generate_tr52_form(dict(notification), pdf_path)
            if success:
                document_path = pdf_path
        
        elif notification_type == 'TR208':
            pdf_path = os.path.join(app.config['GENERATED_FOLDER'], f"TR208_{vehicle_id}.pdf")
            success, error = pdf_gen.generate_tr208_form(dict(notification), pdf_path)
            if success:
                document_path = pdf_path
                
        elif notification_type == 'Auction_Ad':
            pdf_path = os.path.join(app.config['GENERATED_FOLDER'], f"Auction_{vehicle_id}.pdf")
            success, error = pdf_gen.generate_auction_notice(dict(notification), pdf_path)
            if success:
                document_path = pdf_path
                
        elif notification_type == 'Release_Notice':
            pdf_path = os.path.join(app.config['GENERATED_FOLDER'], f"Release_{vehicle_id}.pdf")
            success, error = pdf_gen.generate_release_notice(dict(notification), pdf_path)
            if success:
                document_path = pdf_path
        
        # Send notification based on method
        success = False
        error_message = ""
        
        if method == 'email' and is_valid_email(recipient):
            # Get template
            from utils import get_notification_templates
            templates = get_notification_templates()
            template = templates.get(notification_type.split('_')[0], {})
            
            # Format subject and body
            subject = template.get('subject', f"Vehicle Notification: {notification_type}")
            body = template.get('body', f"Notification for vehicle {vehicle_id}")
            
            # Replace placeholders
            vehicle_data = dict(notification)
            subject = subject.format(**vehicle_data)
            body = body.format(**vehicle_data)
            
            # Send email
            success, error_message = send_email_notification(recipient, subject, body, document_path)
            
        elif method == 'sms' and is_valid_phone(recipient):
            message = f"iTow Notification: {notification_type} for {vehicle_id}. Please check your email for full details."
            success, error_message = send_sms_notification(recipient, message)
            
        elif method == 'fax' and recipient:
            message = f"iTow Notification: {notification_type} for {vehicle_id}. Please see attached document."
            success, error_message = send_fax_notification(recipient, message, document_path)
            
        elif method == 'manual':
            # Just mark as sent manually
            success = True
            
        # Update notification status
        if success:
            mark_notification_sent(notification_id, method, recipient)
            
            # Add document record if generated
            if document_path:
                cursor.execute("""
                    INSERT INTO documents 
                    (vehicle_id, type, filename, upload_date, sent_date, sent_to, sent_method) 
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    vehicle_id,
                    notification_type,
                    os.path.basename(document_path),
                    datetime.now().strftime('%Y-%m-%d'),
                    datetime.now().strftime('%Y-%m-%d'),
                    recipient,
                    method
                ))
            
            # Add police log entry
            cursor.execute("""
                INSERT INTO police_logs 
                (vehicle_id, communication_date, communication_type, notes, recipient, contact_method) 
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                vehicle_id,
                datetime.now().strftime('%Y-%m-%d'),
                notification_type,
                f"Sent {notification_type} notification",
                recipient,
                method
            ))
            
            conn.commit()
            
            # Update vehicle flags based on notification type
            if notification_type == 'TOP':
                cursor.execute("UPDATE vehicles SET top_notification_sent = 1 WHERE towbook_call_number = ?", (vehicle_id,))
            elif notification_type == 'Auction_Ad':
                cursor.execute("UPDATE vehicles SET auction_ad_sent = 1 WHERE towbook_call_number = ?", (vehicle_id,))
            elif notification_type == 'Release_Notice':
                cursor.execute("UPDATE vehicles SET release_notification_sent = 1 WHERE towbook_call_number = ?", (vehicle_id,))
            
            conn.commit()
            conn.close()
            
            log_action("NOTIFICATION", current_user.username, f"Vehicle {vehicle_id} {notification_type} notification sent via {method} to {recipient}")
            
            if document_path:
                return jsonify({
                    'status': 'success', 
                    'message': f"Notification sent via {method}",
                    'document': os.path.basename(document_path)
                })
            else:
                return jsonify({'status': 'success', 'message': f"Notification marked as sent via {method}"})
        else:
            conn.close()
            return jsonify({'status': 'error', 'message': error_message}), 500
            
    except Exception as e:
        logging.error(f"Error sending notification: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/generate-top/<call_number>', methods=['POST'])
@login_required
def generate_top(call_number):
    try:
        conn = get_db_connection()
        vehicle = conn.execute("SELECT * FROM vehicles WHERE towbook_call_number = ?", (call_number,)).fetchone()
        conn.close()
        if not vehicle:
            return jsonify({'error': 'Vehicle not found'}), 404
        data = dict(vehicle)
        for key in data:
            if data[key] is None or data[key] == '':
                data[key] = 'N/A'
                
        # Check if the vehicle is eligible for TR208
        is_tr208_eligible, _ = is_eligible_for_tr208(data)
        data['tr208_eligible'] = 1 if is_tr208_eligible else 0
                
        pdf_path = f"static/generated_pdfs/TOP_{call_number}.pdf"
        os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
        success, error = pdf_gen.generate_top(data, pdf_path)
        if success:
            update_fields = {
                'top_form_sent_date': datetime.now().strftime('%Y-%m-%d'),
                'top_notification_sent': 1,
                'tr208_eligible': 1 if is_tr208_eligible else 0
            }
            
            if is_tr208_eligible:
                # Set TR208 timeline (27 days = 7 days police + 20 days owner)
                tr208_date = calculate_tr208_timeline(datetime.now())
                update_fields['tr208_available_date'] = tr208_date.strftime('%Y-%m-%d')
                update_fields['days_until_next_step'] = 27
            else:
                # Standard TR52 timeline (20 days)
                tr52_date = datetime.now() + timedelta(days=20)
                update_fields['tr52_available_date'] = tr52_date.strftime('%Y-%m-%d')
                update_fields['days_until_next_step'] = 20
                
            update_fields['redemption_end_date'] = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
            update_vehicle_status(call_number, 'TOP Generated', update_fields)
            
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO police_logs (vehicle_id, communication_date, communication_type, notes) VALUES (?, ?, ?, ?)",
                           (call_number, datetime.now().strftime('%Y-%m-%d'), 'TOP Notification', 
                            f"TOP form sent to LEIN processor for jurisdiction: {data['jurisdiction']}"))
            cursor.execute("INSERT INTO documents (vehicle_id, type, filename, upload_date) VALUES (?, ?, ?, ?)",
                          (call_number, 'TOP Form', os.path.basename(pdf_path), datetime.now().strftime('%Y-%m-%d')))
            conn.commit()
            conn.close()
            log_action("GENERATE_TOP", current_user.username, f"Vehicle {call_number} TOP form generated and notified")
            
            # Create notification record
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO notifications 
                (vehicle_id, notification_type, due_date, status, document_path) 
                VALUES (?, ?, ?, ?, ?)
            """, (
                call_number, 
                'TOP', 
                datetime.now().strftime('%Y-%m-%d'),
                'pending',
                pdf_path
            ))
            conn.commit()
            conn.close()
            
            return send_file(pdf_path, as_attachment=True)
        logging.error(f"Failed to generate TOP: {error}")
        return jsonify({'error': error}), 500
    except Exception as e:
        logging.error(f"Error generating TOP: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/generate-tr52/<call_number>', methods=['POST'])
@login_required
def generate_tr52(call_number):
    try:
        conn = get_db_connection()
        vehicle = conn.execute("SELECT * FROM vehicles WHERE towbook_call_number = ?", (call_number,)).fetchone()
        conn.close()
        if not vehicle:
            return jsonify({'error': 'Vehicle not found'}), 404
        data = dict(vehicle)
        for key in data:
            if data[key] is None or data[key] == '':
                data[key] = 'N/A'
        pdf_path = f"static/generated_pdfs/TR52_{call_number}.pdf"
        os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
        success, error = pdf_gen.generate_tr52_form(data, pdf_path)
        if success:
            update_fields = {'tr52_received_date': datetime.now().strftime('%Y-%m-%d')}
            update_vehicle_status(call_number, 'TR52 Ready', update_fields)
            
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO documents (vehicle_id, type, filename, upload_date) VALUES (?, ?, ?, ?)",
                          (call_number, 'TR52 Form', os.path.basename(pdf_path), datetime.now().strftime('%Y-%m-%d')))
            cursor.execute("INSERT INTO police_logs (vehicle_id, communication_date, communication_type, notes) VALUES (?, ?, ?, ?)",
                           (call_number, datetime.now().strftime('%Y-%m-%d'), 'TR52 Form', 
                            f"TR52 form generated for jurisdiction: {data['jurisdiction']}"))
            conn.commit()
            conn.close()
            
            log_action("GENERATE_TR52", current_user.username, f"Vehicle {call_number} TR52 form generated")
            return send_file(pdf_path, as_attachment=True)
        logging.error(f"Failed to generate TR52: {error}")
        return jsonify({'error': error}), 500
    except Exception as e:
        logging.error(f"Error generating TR52: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/generate-tr208/<call_number>', methods=['POST'])
@login_required
def generate_tr208(call_number):
    try:
        conn = get_db_connection()
        vehicle = conn.execute("SELECT * FROM vehicles WHERE towbook_call_number = ?", (call_number,)).fetchone()
        conn.close()
        if not vehicle:
            return jsonify({'error': 'Vehicle not found'}), 404
        
        data = dict(vehicle)
        for key in data:
            if data[key] is None or data[key] == '':
                data[key] = 'N/A'
                
        # Check if the vehicle is eligible for TR208
        is_eligible, reasons = is_eligible_for_tr208(data)
        
        if not is_eligible:
            reason_str = ", ".join([f"{k}: {v}" for k, v in reasons.items()])
            return jsonify({'error': f'Vehicle not eligible for TR208: {reason_str}'}), 400
        
        pdf_path = f"static/generated_pdfs/TR208_{call_number}.pdf"
        os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
        
        success, error = pdf_gen.generate_tr208_form(data, pdf_path)
        
        if success:
            update_fields = {'tr208_received_date': datetime.now().strftime('%Y-%m-%d')}
            update_vehicle_status(call_number, 'TR208 Ready', update_fields)
            
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO documents (vehicle_id, type, filename, upload_date) VALUES (?, ?, ?, ?)",
                          (call_number, 'TR208 Form', os.path.basename(pdf_path), datetime.now().strftime('%Y-%m-%d')))
            cursor.execute("INSERT INTO police_logs (vehicle_id, communication_date, communication_type, notes) VALUES (?, ?, ?, ?)",
                           (call_number, datetime.now().strftime('%Y-%m-%d'), 'TR208 Form', 
                            f"TR208 form generated for jurisdiction: {data['jurisdiction']}"))
            conn.commit()
            conn.close()
            
            log_action("GENERATE_TR208", current_user.username, f"Vehicle {call_number} TR208 form generated for scrap vehicle")
            return send_file(pdf_path, as_attachment=True)
        
        logging.error(f"Failed to generate TR208: {error}")
        return jsonify({'error': error}), 500
    except Exception as e:
        logging.error(f"Error generating TR208: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/check-tr208-eligibility/<call_number>', methods=['GET'])
@login_required
def check_tr208_eligibility(call_number):
    try:
        conn = get_db_connection()
        vehicle = conn.execute("SELECT * FROM vehicles WHERE towbook_call_number = ?", (call_number,)).fetchone()
        conn.close()
        
        if not vehicle:
            return jsonify({'error': 'Vehicle not found'}), 404
        
        data = dict(vehicle)
        # Ensure no null values
        for key in data:
            if data[key] is None or data[key] == '':
                data[key] = 'N/A'
        
        # Check eligibility
        eligible, reasons = is_eligible_for_tr208(data)
        
        # Get the timeline
        timeline_date = None
        if eligible and data['tow_date'] != 'N/A':
            timeline_date = calculate_tr208_timeline(data['tow_date']).strftime('%Y-%m-%d')
        
        return jsonify({
            'eligible': eligible,
            'reasons': reasons,
            'timeline_date': timeline_date,
            'vehicle': {
                'year': data['year'],
                'make': data['make'],
                'model': data['model'],
                'vin': data['vin']
            }
        })
    except Exception as e:
        logging.error(f"Error checking TR208 eligibility: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/update-vehicle-condition/<call_number>', methods=['POST'])
@login_required
def update_vehicle_condition(call_number):
    try:
        data = request.json
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Update condition fields
        cursor.execute("""
            UPDATE vehicles 
            SET inoperable = ?, 
                damage_extent = ?, 
                condition_notes = ?,
                last_updated = ?
            WHERE towbook_call_number = ?
        """, (
            data.get('inoperable', 0),
            data.get('damage_extent', 'N/A'),
            data.get('condition_notes', 'N/A'),
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            call_number
        ))
        
        # Re-check TR208 eligibility
        cursor.execute("SELECT * FROM vehicles WHERE towbook_call_number = ?", (call_number,))
        vehicle = cursor.fetchone()
        
        if vehicle:
            vehicle_data = dict(vehicle)
            eligible, _ = is_eligible_for_tr208(vehicle_data)
            
            cursor.execute("UPDATE vehicles SET tr208_eligible = ? WHERE towbook_call_number = ?", 
                          (1 if eligible else 0, call_number))
            
            # If eligible and has tow date, update TR208 timeline
            if eligible and vehicle_data['tow_date'] and vehicle_data['tow_date'] != 'N/A':
                tr208_date = calculate_tr208_timeline(vehicle_data['tow_date'])
                cursor.execute("UPDATE vehicles SET tr208_available_date = ? WHERE towbook_call_number = ?",
                              (tr208_date.strftime('%Y-%m-%d'), call_number))
        
        conn.commit()
        
        # Add a log entry
        cursor.execute("""
            INSERT INTO police_logs 
            (vehicle_id, communication_date, communication_type, notes) 
            VALUES (?, ?, ?, ?)
        """, (
            call_number,
            datetime.now().strftime('%Y-%m-%d'),
            'Vehicle Condition',
            f"Vehicle condition updated: Inoperable: {data.get('inoperable')}, Damage: {data.get('damage_extent')}"
        ))
        
        conn.commit()
        conn.close()
        
        log_action("UPDATE_CONDITION", current_user.username, f"Vehicle {call_number} condition information updated")
        
        return jsonify({
            'status': 'success',
            'message': 'Vehicle condition updated',
            'tr208_eligible': eligible
        })
    except Exception as e:
        logging.error(f"Error updating vehicle condition: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/mark-tr52-ready/<call_number>', methods=['POST'])
@login_required
def mark_tr52_ready(call_number):
    try:
        update_fields = {'tr52_received_date': datetime.now().strftime('%Y-%m-%d')}
        success = update_vehicle_status(call_number, 'TR52 Ready', update_fields)
        if success:
            log_action("TR52_READY", current_user.username, f"Vehicle {call_number} marked as TR52 Ready")
            return jsonify({'status': 'success', 'message': 'Vehicle marked as TR52 Ready'})
        return jsonify({'status': 'error', 'message': 'Failed to update status'}), 500
    except Exception as e:
        logging.error(f"Error marking TR52 ready: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/mark-tr208-ready/<call_number>', methods=['POST'])
@login_required
def mark_tr208_ready(call_number):
    try:
        update_fields = {'tr208_received_date': datetime.now().strftime('%Y-%m-%d')}
        success = update_vehicle_status(call_number, 'TR208 Ready', update_fields)
        if success:
            log_action("TR208_READY", current_user.username, f"Vehicle {call_number} marked as TR208 Ready")
            return jsonify({'status': 'success', 'message': 'Vehicle marked as TR208 Ready'})
        return jsonify({'status': 'error', 'message': 'Failed to update status'}), 500
    except Exception as e:
        logging.error(f"Error marking TR208 ready: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/paperwork-received/<call_number>', methods=['POST'])
@login_required
def paperwork_received(call_number):
    try:
        update_fields = {'paperwork_received_date': datetime.now().strftime('%Y-%m-%d')}
        success = update_vehicle_status(call_number, 'Scheduled for Release', update_fields)
        if success:
            log_action("PAPERWORK_RECEIVED", current_user.username, f"Vehicle {call_number} paperwork received")
            return jsonify({'status': 'success', 'message': 'Paperwork received'})
        return jsonify({'status': 'error', 'message': 'Failed to update status'}), 500
    except Exception as e:
        logging.error(f"Error marking paperwork: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/decision/<call_number>', methods=['POST'])
@login_required
def api_decision(call_number):
    from utils import calculate_next_auction_date
    data = request.get_json()
    decision = data.get('decision')
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT ad_placement_date FROM vehicles WHERE towbook_call_number = ?", (call_number,))
    result = cursor.fetchone()
    ad_placement_date = result['ad_placement_date'] if result and result['ad_placement_date'] != 'N/A' else None

    if decision == 'auction':
        auction_date = calculate_next_auction_date(ad_placement_date)
        ad_date = calculate_newspaper_ad_date(auction_date)
        update_vehicle_status(call_number, 'Ready for Auction', {
            'auction_date': auction_date.strftime('%Y-%m-%d'),
            'ad_placement_date': ad_date.strftime('%Y-%m-%d')
        })
        cursor.execute("INSERT INTO police_logs (vehicle_id, communication_date, communication_type, notes) VALUES (?, ?, ?, ?)",
                       (call_number, datetime.now().strftime('%Y-%m-%d'), 'Auction Ad Receipt',
                        f"Auction ad placed for {auction_date.strftime('%Y-%m-%d')}"))
        cursor.execute("UPDATE vehicles SET auction_ad_sent = 1 WHERE towbook_call_number = ?", (call_number,))
        
        # Create notification record
        cursor.execute("""
            INSERT INTO notifications 
            (vehicle_id, notification_type, due_date, status) 
            VALUES (?, ?, ?, ?)
        """, (
            call_number, 
            'Auction_Ad', 
            ad_date.strftime('%Y-%m-%d'),
            'pending'
        ))
        
        log_action("DECISION", current_user.username, f"Vehicle {call_number} decision: Auction, scheduled for {auction_date}")
    elif decision == 'scrap':
        scrap_date = datetime.now() + timedelta(days=7)
        update_vehicle_status(call_number, 'Ready for Scrap', {
            'estimated_date': scrap_date.strftime('%Y-%m-%d')
        })
        
        # Create notification record
        cursor.execute("""
            INSERT INTO notifications 
            (vehicle_id, notification_type, due_date, status) 
            VALUES (?, ?, ?, ?)
        """, (
            call_number, 
            'Scrap_Photos', 
            scrap_date.strftime('%Y-%m-%d'),
            'pending'
        ))
        
        log_action("DECISION", current_user.username, f"Vehicle {call_number} decision: Scrap")
    else:
        conn.close()
        return jsonify({"error": "Invalid decision"}), 400
    
    conn.commit()
    conn.close()
    return jsonify({"message": "Decision recorded"}), 200

@app.route('/api/schedule-auction', methods=['POST'])
@login_required
def schedule_auction():
    try:
        data = request.json
        vehicle_ids = data.get('vehicle_ids', [])
        auction_date = data.get('auction_date')
        if not vehicle_ids or not auction_date:
            return jsonify({'status': 'error', 'message': 'Missing vehicle IDs or auction date'}), 400
        success, message = create_auction(auction_date, vehicle_ids)
        if success:
            log_action("AUCTION_SCHEDULED", current_user.username, f"Auction scheduled: {message}")
            
            # Generate newspaper ad
            try:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute(f"""
                    SELECT * FROM vehicles 
                    WHERE towbook_call_number IN ({','.join(['?' for _ in vehicle_ids])})
                """, vehicle_ids)
                vehicles = [dict(row) for row in cursor.fetchall()]
                conn.close()
                
                if vehicles:
                    ad_path = os.path.join(app.config['GENERATED_FOLDER'], f"Auction_Ad_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf")
                    success, error = pdf_gen.generate_newspaper_ad(vehicles, ad_path)
                    if success:
                        # Add document record
                        conn = get_db_connection()
                        cursor = conn.cursor()
                        cursor.execute("""
                            INSERT INTO documents 
                            (vehicle_id, type, filename, upload_date) 
                            VALUES (?, ?, ?, ?)
                        """, (
                            "BATCH", 
                            "Newspaper Ad", 
                            os.path.basename(ad_path), 
                            datetime.now().strftime('%Y-%m-%d')
                        ))
                        conn.commit()
                        conn.close()
                        message += f" Newspaper ad generated."
            except Exception as e:
                logging.error(f"Error generating newspaper ad: {e}")
                
            return jsonify({'status': 'success', 'message': message})
        return jsonify({'status': 'error', 'message': message}), 500
    except Exception as e:
        logging.error(f"Error scheduling auction: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/generate-release/<call_number>', methods=['POST'])
@login_required
def generate_release(call_number):
    try:
        data = request.json
        conn = get_db_connection()
        vehicle = conn.execute("SELECT * FROM vehicles WHERE towbook_call_number = ?", (call_number,)).fetchone()
        conn.close()
        if not vehicle:
            return jsonify({'error': 'Vehicle not found'}), 404
        vehicle_data = dict(vehicle)
        for key in vehicle_data:
            if vehicle_data[key] is None or vehicle_data[key] == '':
                vehicle_data[key] = 'N/A'
        vehicle_data.update(data)
        vehicle_data['release_date'] = data.get('release_date', datetime.now().strftime('%Y-%m-%d'))
        vehicle_data['release_time'] = data.get('release_time', datetime.now().strftime('%H:%M'))
        release_reason = data.get('release_reason', 'Not specified')
        
        compliance_text = {
            'Owner Redeemed': "Vehicle released to owner per MCL 257.252. All fees paid.",
            'Auctioned': "Vehicle sold at public auction per MCL 257.252g. Sale amount recorded.",
            'Scrapped': "Vehicle scrapped per MCL 257.252b. No value retained.",
            'Title Transfer': "Title transferred to tow company in lieu of fees per MCL 257.252."
        }.get(release_reason, "Vehicle released per MCL 257.252.")
        vehicle_data['compliance_text'] = compliance_text
        
        pdf_path = f"static/generated_pdfs/Release_{call_number}.pdf"
        os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
        success, error = pdf_gen.generate_release_notice(vehicle_data, pdf_path)
        if success:
            update_fields = {
                'release_reason': release_reason,
                'recipient': data.get('recipient', 'Not specified'),
                'release_date': vehicle_data['release_date'],
                'release_time': vehicle_data['release_time'],
                'release_notification_sent': 1
            }
            if release_reason == 'Auctioned':
                update_fields['sale_amount'] = float(data.get('sale_amount', 0))
                update_fields['fees'] = float(data.get('fees', 0))
                update_fields['net_proceeds'] = update_fields['sale_amount'] - update_fields['fees']
            status = {
                'Owner Redeemed': 'Released',
                'Auctioned': 'Auctioned',
                'Scrapped': 'Scrapped',
                'Title Transfer': 'Transferred'
            }.get(release_reason, 'Released')
            release_vehicle(call_number, release_reason, data.get('recipient', 'Not specified'),
                           vehicle_data['release_date'], vehicle_data['release_time'])
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO police_logs (vehicle_id, communication_date, communication_type, notes) VALUES (?, ?, ?, ?)",
                           (call_number, datetime.now().strftime('%Y-%m-%d'), 'Release Notification',
                            f"Vehicle released: {release_reason} to {data.get('recipient', 'Not specified')}"))
            cursor.execute("INSERT INTO documents (vehicle_id, type, filename, upload_date) VALUES (?, ?, ?, ?)",
                           (call_number, 'Release Notice', os.path.basename(pdf_path), datetime.now().strftime('%Y-%m-%d')))
            
            # Create notification record
            cursor.execute("""
                INSERT INTO notifications 
                (vehicle_id, notification_type, due_date, status, document_path) 
                VALUES (?, ?, ?, ?, ?)
            """, (
                call_number, 
                'Release_Notice', 
                datetime.now().strftime('%Y-%m-%d'),
                'pending',
                pdf_path
            ))
            
            conn.commit()
            conn.close()
            log_action("RELEASE", current_user.username, f"Vehicle {call_number} released: {release_reason}")
            return send_file(pdf_path, as_attachment=True)
        return jsonify({'error': error}), 500
    except Exception as e:
        logging.error(f"Error generating release: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/mark-released/<call_number>', methods=['POST'])
@login_required
def mark_released(call_number):
    try:
        data = request.json
        success = release_vehicle(call_number, data.get('release_reason', 'Not specified'),
                                 data.get('recipient', 'Not specified'), data.get('release_date'),
                                 data.get('release_time'))
        if success:
            log_action("RELEASE", current_user.username, f"Vehicle {call_number} marked as released: {data.get('release_reason')}")
            return jsonify({'status': 'success'})
        return jsonify({'error': 'Failed to release vehicle'}), 500
    except Exception as e:
        logging.error(f"Error marking released: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/logs')
@login_required
def get_action_logs():
    try:
        vehicle_id = request.args.get('vehicle_id')
        limit = request.args.get('limit', 100, type=int)
        logs = get_logs(vehicle_id, limit)
        return jsonify([dict(log) for log in logs])
    except Exception as e:
        logging.error(f"Error retrieving logs: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/workflow-counts')
@login_required
def workflow_counts():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        today = datetime.now().strftime('%Y-%m-%d')
        cursor.execute("""
            SELECT COUNT(*) FROM vehicles
            WHERE status = 'New' AND last_updated < DATE('now', '-2 day')
            OR (status = 'TOP Generated' AND last_updated < DATE('now', '-30 day'))
        """)
        overdue = cursor.fetchone()[0]
        cursor.execute("""
            SELECT COUNT(*) FROM vehicles
            WHERE status = 'New' AND last_updated = DATE('now', '-2 day')
            OR (status = 'TOP Generated' AND last_updated = DATE('now', '-30 day'))
        """)
        due_today = cursor.fetchone()[0]
        cursor.execute("""
            SELECT COUNT(*) FROM vehicles
            WHERE status = 'TR52 Ready' OR status = 'TR208 Ready'
        """)
        ready = cursor.fetchone()[0]
        
        # Count pending notifications
        cursor.execute("""
            SELECT COUNT(*) FROM notifications
            WHERE status = 'pending' AND due_date <= ?
        """, (today,))
        pending_notifications = cursor.fetchone()[0]
        
        conn.close()
        return jsonify({
            'overdue': overdue,
            'dueToday': due_today,
            'ready': ready,
            'pendingNotifications': pending_notifications
        })
    except Exception as e:
        logging.error(f"Error getting workflow counts: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/statistics')
@login_required
def get_statistics():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM vehicles")
        total_vehicles = cursor.fetchone()[0]
        cursor.execute("""
            SELECT status, COUNT(*) as count
            FROM vehicles
            GROUP BY status
        """)
        status_counts = {row[0] or 'N/A': row[1] for row in cursor.fetchall()}
        cursor.execute("""
            SELECT jurisdiction, COUNT(*) as count
            FROM vehicles
            WHERE jurisdiction IS NOT NULL AND jurisdiction != 'N/A'
            GROUP BY jurisdiction
            ORDER BY count DESC
            LIMIT 5
        """)
        jurisdiction_counts = {row[0]: row[1] for row in cursor.fetchall()}
        cursor.execute("""
            SELECT 
                AVG(JULIANDAY(COALESCE(release_date, DATE('now'))) - JULIANDAY(tow_date)) as avg_days
            FROM vehicles
            WHERE tow_date IS NOT NULL AND tow_date != 'N/A'
        """)
        avg_processing_days = cursor.fetchone()[0]
        cursor.execute("""
            SELECT action_type, vehicle_id, details, timestamp
            FROM logs
            ORDER BY timestamp DESC
            LIMIT 5
        """)
        recent_activity = [dict(row) for row in cursor.fetchall()]
        
        # Get compliance metrics
        cursor.execute("""
            SELECT COUNT(*) FROM vehicles 
            WHERE top_notification_sent = 1
        """)
        top_notifications = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT COUNT(*) FROM vehicles 
            WHERE tr52_available_date IS NOT NULL AND tr52_available_date != 'N/A'
            OR tr208_available_date IS NOT NULL AND tr208_available_date != 'N/A'
        """)
        tr52_ready = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT COUNT(*) FROM vehicles 
            WHERE auction_ad_sent = 1
        """)
        auction_ads = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT COUNT(*) FROM vehicles 
            WHERE release_notification_sent = 1
        """)
        release_notifications = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT SUM(sale_amount) FROM vehicles 
            WHERE sale_amount IS NOT NULL AND sale_amount > 0
        """)
        total_sales = cursor.fetchone()[0] or 0
        
        cursor.execute("""
            SELECT SUM(net_proceeds) FROM vehicles 
            WHERE net_proceeds IS NOT NULL AND net_proceeds > 0
        """)
        total_proceeds = cursor.fetchone()[0] or 0
        
        # Get TR208 metrics
        cursor.execute("""
            SELECT COUNT(*) FROM vehicles 
            WHERE tr208_eligible = 1
        """)
        tr208_eligible = cursor.fetchone()[0]
        
        conn.close()
        return jsonify({
            'totalVehicles': total_vehicles,
            'statusCounts': status_counts,
            'jurisdictionCounts': jurisdiction_counts,
            'avgProcessingDays': round(avg_processing_days, 1) if avg_processing_days else 0,
            'recentActivity': recent_activity,
            'complianceMetrics': {
                'topNotifications': top_notifications,
                'tr52Ready': tr52_ready,
                'auctionAds': auction_ads,
                'releaseNotifications': release_notifications,
                'tr208Eligible': tr208_eligible,
                'totalSales': round(float(total_sales), 2),
                'totalProceeds': round(float(total_proceeds), 2)
            }
        })
    except Exception as e:
        logging.error(f"Error getting statistics: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/contacts', methods=['GET'])
@login_required
def api_get_contacts():
    try:
        contacts = get_contacts()
        return jsonify(contacts)
    except Exception as e:
        logging.error(f"Error getting contacts: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/contacts', methods=['POST'])
@login_required
def api_save_contact():
    try:
        data = request.json
        success, message = save_contact(data)
        if success:
            return jsonify({'status': 'success', 'message': message})
        return jsonify({'status': 'error', 'message': message}), 400
    except Exception as e:
        logging.error(f"Error saving contact: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/generate-certified-mail/<call_number>', methods=['POST'])
@login_required
def generate_certified_mail(call_number):
    try:
        # Generate a certified mail tracking number
        certified_mail_number = generate_certified_mail_number()
        
        # Update vehicle record
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE vehicles 
            SET certified_mail_number = ?, 
                certified_mail_sent_date = ? 
            WHERE towbook_call_number = ?
        """, (certified_mail_number, datetime.now().strftime('%Y-%m-%d'), call_number))
        
        # Add a police log entry
        cursor.execute("""
            INSERT INTO police_logs 
            (vehicle_id, communication_date, communication_type, notes) 
            VALUES (?, ?, ?, ?)
        """, (
            call_number,
            datetime.now().strftime('%Y-%m-%d'),
            'Certified Mail',
            f"Certified mail sent, tracking #: {certified_mail_number}"
        ))
        
        conn.commit()
        conn.close()
        
        log_action("CERTIFIED_MAIL", current_user.username, f"Vehicle {call_number} certified mail generated: {certified_mail_number}")
        
        return jsonify({
            'status': 'success',
            'certified_mail_number': certified_mail_number,
            'sent_date': datetime.now().strftime('%Y-%m-%d')
        })
    except Exception as e:
        logging.error(f"Error generating certified mail: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/auto-detect-jurisdiction/<call_number>', methods=['POST'])
@login_required
def auto_detect_jurisdiction(call_number):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT location FROM vehicles WHERE towbook_call_number = ?", (call_number,))
        result = cursor.fetchone()
        conn.close()
        
        if not result or not result['location'] or result['location'] == 'N/A':
            return jsonify({'status': 'error', 'message': 'No location found for vehicle'}), 400
            
        location = result['location']
        jurisdiction = determine_jurisdiction(location)
        
        if jurisdiction == 'Unknown':
            return jsonify({
                'status': 'warning', 
                'message': 'Could not determine jurisdiction from location',
                'location': location,
                'jurisdiction': jurisdiction
            }), 200
            
        # Update vehicle record
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE vehicles 
            SET jurisdiction = ?
            WHERE towbook_call_number = ?
        """, (jurisdiction, call_number))
        conn.commit()
        conn.close()
        
        log_action("AUTO_DETECT", current_user.username, f"Vehicle {call_number} jurisdiction auto-detected: {jurisdiction} from location: {location}")
        
        return jsonify({
            'status': 'success',
            'location': location,
            'jurisdiction': jurisdiction,
            'message': f"Jurisdiction detected: {jurisdiction}"
        })
    except Exception as e:
        logging.error(f"Error auto-detecting jurisdiction: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/calculate-storage-fees/<call_number>', methods=['GET'])
@login_required
def api_calculate_storage_fees(call_number):
    try:
        daily_rate = request.args.get('rate', 25.00, type=float)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT tow_date FROM vehicles WHERE towbook_call_number = ?", (call_number,))
        result = cursor.fetchone()
        conn.close()
        
        if not result or not result['tow_date'] or result['tow_date'] == 'N/A':
            return jsonify({'status': 'error', 'message': 'No tow date found for vehicle'}), 400
            
        tow_date = result['tow_date']
        fee, days = calculate_storage_fees(tow_date, daily_rate)
        
        return jsonify({
            'status': 'success',
            'tow_date': tow_date,
            'days': days,
            'daily_rate': daily_rate,
            'total_fee': fee,
            'formatted_fee': f"${fee:.2f}"
        })
    except Exception as e:
        logging.error(f"Error calculating storage fees: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/document-download/<path:filename>', methods=['GET'])
@login_required
def download_document(filename):
    try:
        file_path = os.path.join(app.config['DOCUMENT_FOLDER'], filename)
        if not os.path.exists(file_path):
            # Try generated folder
            file_path = os.path.join(app.config['GENERATED_FOLDER'], filename)
            if not os.path.exists(file_path):
                return jsonify({'error': 'File not found'}), 404
                
        return send_file(file_path, as_attachment=True)
    except Exception as e:
        logging.error(f"Error downloading document: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/generate-scrap-certification/<call_number>', methods=['POST'])
@login_required
def generate_scrap_certification(call_number):
    try:
        data = request.json
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM vehicles WHERE towbook_call_number = ?", (call_number,))
        vehicle = cursor.fetchone()
        
        if not vehicle:
            conn.close()
            return jsonify({'error': 'Vehicle not found'}), 404
            
        vehicle_data = dict(vehicle)
        for key in vehicle_data:
            if vehicle_data[key] is None or vehicle_data[key] == '':
                vehicle_data[key] = 'N/A'
                
        # Get photo paths
        photos = []
        if vehicle_data['photo_paths'] and vehicle_data['photo_paths'] != 'N/A':
            try:
                photos = json.loads(vehicle_data['photo_paths'])
            except:
                photos = []
                
        if not photos:
            conn.close()
            return jsonify({'error': 'No photos found for scrap certification'}), 400
            
        # Update with additional data
        salvage_value = data.get('salvage_value', 0)
        vehicle_data['salvage_value'] = salvage_value
        
        # Generate PDF
        pdf_path = f"static/generated_pdfs/Scrap_{call_number}.pdf"
        success, error = pdf_gen.generate_scrap_certification(vehicle_data, photos, pdf_path)
        
        if success:
            # Update vehicle
            cursor.execute("""
                UPDATE vehicles 
                SET salvage_value = ?,
                    status = 'Scrapped',
                    archived = 1,
                    release_reason = 'Scrapped',
                    release_date = ?
                WHERE towbook_call_number = ?
            """, (salvage_value, datetime.now().strftime('%Y-%m-%d'), call_number))
            
            # Add document record
            cursor.execute("""
                INSERT INTO documents 
                (vehicle_id, type, filename, upload_date) 
                VALUES (?, ?, ?, ?)
            """, (call_number, 'Scrap Certification', os.path.basename(pdf_path), datetime.now().strftime('%Y-%m-%d')))
            
            # Add log entry
            cursor.execute("""
                INSERT INTO police_logs 
                (vehicle_id, communication_date, communication_type, notes) 
                VALUES (?, ?, ?, ?)
            """, (
                call_number,
                datetime.now().strftime('%Y-%m-%d'),
                'Scrap Certification',
                f"Vehicle scrapped with salvage value: ${float(salvage_value):.2f}"
            ))
            
            conn.commit()
            conn.close()
            
            log_action("SCRAP", current_user.username, f"Vehicle {call_number} scrapped with salvage value: ${float(salvage_value):.2f}")
            
            return jsonify({
                'status': 'success',
                'message': 'Scrap certification generated',
                'pdf_path': os.path.basename(pdf_path)
            })
        else:
            conn.close()
            return jsonify({'error': error}), 500
    except Exception as e:
        logging.error(f"Error generating scrap certification: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/scraping-progress')
@login_required
def scraping_progress():
    progress = {'percentage': 0, 'is_running': False, 'processed': 0, 'total': 0, 'status': 'Not running'}
    return jsonify({'progress': progress})

# Update utils.py log_action function to include user information
# This function already exists in your utils.py file, but now includes user info
@app.context_processor
def inject_user():
    return dict(current_user=current_user)

if __name__ == '__main__':
    port = 5000
    if is_port_in_use(port):
        logging.warning(f"Port {port} is in use. Trying port {port + 1}")
        port += 1
    status_thread = threading.Thread(target=run_status_checks, daemon=True)
    status_thread.start()
    app.run(debug=True, host='0.0.0.0', port=port)