from flask import Flask, render_template, send_file, request, jsonify
from database import (init_db, get_vehicles_by_status, update_vehicle_status, 
                      update_vehicle, insert_vehicle, get_db_connection, check_and_update_statuses, 
                      get_logs, toggle_archive_status, create_auction)
from generator import PDFGenerator
from utils import (generate_complaint_number, release_vehicle, log_action, 
                   ensure_logs_table_exists, setup_logging, get_status_filter, calculate_newspaper_ad_date)
from datetime import datetime, timedelta
import threading
import os
import logging
import time
import socket
import json
from werkzeug.utils import secure_filename
from io import StringIO
import csv

# Configure logging
setup_logging()

app = Flask(__name__)

# Initialize components
init_db()
ensure_logs_table_exists()
pdf_gen = PDFGenerator()

# Configure upload folders
UPLOAD_FOLDER = 'static/uploads/vehicle_photos'
DOCUMENT_FOLDER = 'static/uploads/documents'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['DOCUMENT_FOLDER'] = DOCUMENT_FOLDER
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
ALLOWED_DOCUMENT_EXTENSIONS = {'pdf'}

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
            time.sleep(3600)
        except Exception as e:
            logging.error(f"Status check error: {e}")
            time.sleep(60)

@app.route('/')
def index():
    status = request.args.get('status', 'New')
    return render_template('index.html', status=status)

@app.route('/api/vehicles')
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
                'readyAuction': status_breakdown.get('Ready for Auction', 0),
                'readyScrap': status_breakdown.get('Ready for Scrap', 0),
                'auction': status_breakdown.get('Auction', 0),
                'scrapped': status_breakdown.get('Scrapped', 0),
                'released': status_breakdown.get('Released', 0),
                'completed': sum([
                    status_breakdown.get('Released', 0),
                    status_breakdown.get('Scrapped', 0),
                    status_breakdown.get('Auctioned', 0)
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
            conn = get_db_connection()
            cursor = conn.cursor()
            sort_by = "tow_date DESC"
            if sort_column:
                valid_columns = [
                    'towbook_call_number', 'complaint_number', 'vin', 'make', 'model', 
                    'year', 'color', 'tow_date', 'jurisdiction', 'status', 'last_updated'
                ]
                if sort_column in valid_columns:
                    sort_dir = "ASC" if sort_direction.lower() == 'asc' else "DESC"
                    sort_by = f"{sort_column} {sort_dir}"
            cursor.execute(f"SELECT * FROM vehicles WHERE archived = 0 ORDER BY {sort_by}")
            vehicles = [dict(row) for row in cursor.fetchall()]
            conn.close()
    
        for vehicle in vehicles:
            for key in vehicle:
                vehicle[key] = vehicle[key] if vehicle[key] else 'N/A'
            if 'tow_date' in vehicle and vehicle['tow_date'] != 'N/A':
                try:
                    tow_date = datetime.strptime(vehicle['tow_date'], '%Y-%m-%d')
                    vehicle['days_since_tow'] = (datetime.now() - tow_date).days
                    if vehicle['status'] == 'TOP Generated' and vehicle.get('tr52_available_date') != 'N/A':
                        tr52_date = datetime.strptime(vehicle['tr52_available_date'], '%Y-%m-%d')
                        vehicle['days_until_next_step'] = max(0, (tr52_date - datetime.now()).days)
                        vehicle['next_step_label'] = 'days until TR52 Ready'
                    elif vehicle['status'] == 'TR52 Ready':
                        vehicle['next_step_label'] = 'days since TR52 Ready'
                        vehicle['days_until_next_step'] = vehicle.get('days_until_next_step', 0)
                    elif vehicle['status'] == 'Ready for Scrap' and vehicle.get('estimated_date') != 'N/A':
                        estimated_date = datetime.strptime(vehicle['estimated_date'], '%Y-%m-%d')
                        vehicle['days_until_next_step'] = max(0, (estimated_date - datetime.now()).days)
                        vehicle['next_step_label'] = 'days until legal scrap date'
                    elif vehicle['status'] == 'Ready for Auction' and vehicle.get('auction_date') != 'N/A':
                        auction_date = datetime.strptime(vehicle['auction_date'], '%Y-%m-%d')
                        vehicle['days_until_auction'] = max(0, (auction_date - datetime.now()).days)
                        vehicle['next_step_label'] = 'days until auction'
                except Exception as e:
                    logging.warning(f"Date processing error for {vehicle['towbook_call_number']}: {e}")
        
        return jsonify(vehicles)
    except Exception as e:
        logging.error(f"Error in api_get_vehicles: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/vehicles/<call_number>', methods=['PUT'])
def update_vehicle_api(call_number):
    try:
        data = request.json
        for key in data:
            data[key] = data[key] if data[key] else 'N/A'
        success, message = update_vehicle(call_number, data)
        if success:
            log_action("UPDATE", call_number, f"Vehicle details updated: {json.dumps(data)}")
            return jsonify({'status': 'success', 'message': message})
        return jsonify({'status': 'error', 'message': message}), 400
    except Exception as e:
        logging.error(f"Error updating vehicle {call_number}: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/vehicles/delete/<call_number>', methods=['DELETE'])
def delete_vehicle(call_number):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM vehicles WHERE towbook_call_number = ?", (call_number,))
        if cursor.fetchone()[0] == 0:
            conn.close()
            return jsonify({'status': 'error', 'message': 'Vehicle not found'}), 404
        cursor.execute("DELETE FROM logs WHERE vehicle_id = ?", (call_number,))
        cursor.execute("DELETE FROM police_logs WHERE vehicle_id = ?", (call_number,))
        cursor.execute("DELETE FROM documents WHERE vehicle_id = ?", (call_number,))
        cursor.execute("DELETE FROM vehicles WHERE towbook_call_number = ?", (call_number,))
        conn.commit()
        conn.close()
        log_action("SYSTEM", "ADMIN", f"Vehicle {call_number} permanently deleted")
        return jsonify({'status': 'success', 'message': f'Vehicle {call_number} deleted'})
    except Exception as e:
        logging.error(f"Error deleting vehicle {call_number}: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/vehicles/add', methods=['POST'])
def add_vehicle():
    try:
        data = request.json
        if not data.get('towbook_call_number'):
            data['towbook_call_number'] = f"MANUAL-{int(time.time())}"
        if not data.get('status'):
            data['status'] = 'New'
        if 'complaint_number' not in data or not data['complaint_number']:
            complaint_number, sequence, year = generate_complaint_number()
            data['complaint_number'] = complaint_number
            data['complaint_sequence'] = sequence
            data['complaint_year'] = year
        for key in data:
            data[key] = data[key] if data[key] else 'N/A'
        success, message = insert_vehicle(data)
        if success:
            log_action("INSERT", data['towbook_call_number'], f"New vehicle added: {json.dumps(data)}")
            return jsonify({'status': 'success', 'message': message})
        return jsonify({'status': 'error', 'message': message}), 400
    except Exception as e:
        logging.error(f"Error adding vehicle: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/update-status/<call_number>', methods=['POST'])
def api_update_status(call_number):
    try:
        data = request.get_json()
        new_status = data.get('status')
        if not new_status:
            return jsonify({"error": "No status provided"}), 400
        from utils import convert_frontend_status
        new_status = convert_frontend_status(new_status)
        logging.info(f"Attempting status update for {call_number} to {new_status}")
        success = update_vehicle_status(call_number, new_status, data)
        if success:
            logging.info(f"Status updated: {call_number} => {new_status}")
            log_action("USER", call_number, f"Status updated to {new_status}")
            return jsonify({"status": "success", "message": "Status updated"}), 200
        else:
            logging.error(f"Failed to update status for {call_number} to {new_status}")
            return jsonify({"error": "Status update failed"}), 500
    except Exception as e:
        logging.error(f"Error in api_update_status: {e}")
        return jsonify({"error": str(e)}), 500
    
@app.route('/api/check-statuses', methods=['POST'])
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
                log_action("STATUS_CORRECTION", call_number, f"Changed incorrect status 'Auction' to 'Ready for Auction'")
                logging.info(f"Fixed status for vehicle {call_number}")
                fixed_count += 1
        conn.commit()
        conn.close()
        return jsonify({'status': 'success', 'fixed': fixed_count})
    except Exception as e:
        logging.error(f"Error checking statuses: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/upload-photo/<call_number>', methods=['POST'])
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
        photo_paths = json.loads(result['photo_paths']) if result and result['photo_paths'] else []
        photo_paths.append(new_filename)
        cursor.execute("UPDATE vehicles SET photo_paths = ? WHERE towbook_call_number = ?",
                       (json.dumps(photo_paths), call_number))
        conn.commit()
        conn.close()
        log_action("PHOTO_UPLOAD", call_number, f"Uploaded photo: {new_filename}")
        return jsonify({'status': 'success', 'filename': new_filename})
    return jsonify({'error': 'File type not allowed'}), 400

@app.route('/api/police-logs/<call_number>', methods=['GET'])
def get_police_logs(call_number):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM police_logs WHERE vehicle_id = ? ORDER BY communication_date DESC", (call_number,))
    logs = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(logs)

@app.route('/api/police-logs/<call_number>', methods=['POST'])
def add_police_log(call_number):
    data = request.json
    communication_date = data.get('communication_date', datetime.now().strftime('%Y-%m-%d'))
    communication_type = data.get('communication_type')
    notes = data.get('notes')
    if not communication_type or not notes:
        return jsonify({'error': 'Missing required fields'}), 400
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO police_logs (vehicle_id, communication_date, communication_type, notes) VALUES (?, ?, ?, ?)",
                   (call_number, communication_date, communication_type, notes))
    conn.commit()
    conn.close()
    log_action("POLICE_LOG", call_number, f"Added police communication log: {communication_type}")
    return jsonify({'status': 'success'})

@app.route('/api/compliance-report', methods=['GET'])
def compliance_report():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT towbook_call_number, tow_date, top_form_sent_date, tr52_available_date, 
               status, auction_date, release_date, photo_paths, sale_amount, fees, net_proceeds
        FROM vehicles WHERE archived = 0
    """)
    vehicles = cursor.fetchall()
    conn.close()
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['Call Number', 'Tow Date', 'Notice Sent Date', 'Redemption End Date', 'Status', 
                     'Auction Date', 'Release Date', 'Photo Count', 'Sale Amount', 'Fees', 'Net Proceeds'])
    for vehicle in vehicles:
        photo_count = len(json.loads(vehicle['photo_paths'])) if vehicle['photo_paths'] else 0
        writer.writerow([
            vehicle['towbook_call_number'] or 'N/A', 
            vehicle['tow_date'] or 'N/A', 
            vehicle['top_form_sent_date'] or 'N/A', 
            vehicle['tr52_available_date'] or 'N/A', 
            vehicle['status'] or 'N/A', 
            vehicle['auction_date'] or 'N/A', 
            vehicle['release_date'] or 'N/A', 
            photo_count, 
            vehicle['sale_amount'] or 0, 
            vehicle['fees'] or 0, 
            vehicle['net_proceeds'] or 0
        ])
    output.seek(0)
    return send_file(output, mimetype='text/csv', as_attachment=True, download_name='compliance_report.csv')

@app.route('/api/upload-tr52/<call_number>', methods=['POST'])
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
        log_action("TR52_UPLOAD", call_number, f"Uploaded amended TR52: {new_filename}")
        return jsonify({'status': 'success', 'filename': new_filename})
    return jsonify({'error': 'File type not allowed'}), 400

@app.route('/api/documents/<call_number>', methods=['GET'])
def get_documents(call_number):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT type, filename, upload_date FROM documents WHERE vehicle_id = ? ORDER BY upload_date DESC",
                   (call_number,))
    documents = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(documents)

@app.route('/api/pending-notifications', methods=['GET'])
def pending_notifications():
    conn = get_db_connection()
    cursor = conn.cursor()
    notifications = []
    cursor.execute("SELECT towbook_call_number, tow_date, top_notification_sent, auction_ad_sent, release_notification_sent, status, ad_placement_date, release_date, jurisdiction FROM vehicles WHERE archived = 0")
    vehicles = cursor.fetchall()
    today = datetime.now().date()
    for vehicle in vehicles:
        tow_date = datetime.strptime(vehicle['tow_date'], '%Y-%m-%d').date() if vehicle['tow_date'] != 'N/A' else today
        if not vehicle['top_notification_sent'] and (today - tow_date).days <= 1:
            notifications.append({
                'vehicle_id': vehicle['towbook_call_number'],
                'action': 'Send TOP Notification',
                'due_date': tow_date.strftime('%Y-%m-%d'),
                'jurisdiction': vehicle['jurisdiction']
            })
        if vehicle['status'] == 'Ready for Auction' and not vehicle['auction_ad_sent'] and vehicle['ad_placement_date'] != 'N/A':
            ad_date = datetime.strptime(vehicle['ad_placement_date'], '%Y-%m-%d').date()
            if (today - ad_date).days >= 0:
                notifications.append({
                    'vehicle_id': vehicle['towbook_call_number'],
                    'action': 'Send Auction Ad Receipt',
                    'due_date': ad_date.strftime('%Y-%m-%d'),
                    'jurisdiction': vehicle['jurisdiction']
                })
        if vehicle['status'] in ['Released', 'Auctioned', 'Scrapped'] and not vehicle['release_notification_sent'] and vehicle['release_date'] != 'N/A':
            notifications.append({
                'vehicle_id': vehicle['towbook_call_number'],
                'action': 'Send Release Notification',
                'due_date': vehicle['release_date'],
                'jurisdiction': vehicle['jurisdiction']
            })
    conn.close()
    return jsonify(notifications)

@app.route('/api/generate-top/<call_number>', methods=['POST'])
def generate_top(call_number):
    try:
        conn = get_db_connection()
        vehicle = conn.execute("SELECT * FROM vehicles WHERE towbook_call_number = ?", (call_number,)).fetchone()
        conn.close()
        if not vehicle:
            return jsonify({'error': 'Vehicle not found'}), 404
        data = dict(vehicle)
        for key in data:
            data[key] = data[key] if data[key] else 'N/A'
        pdf_path = f"static/generated_pdfs/TOP_{call_number}.pdf"
        os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
        success, error = pdf_gen.generate_top(data, pdf_path)
        if success:
            update_fields = {
                'top_form_sent_date': datetime.now().strftime('%Y-%m-%d'),
                'top_notification_sent': 1
            }
            tr52_date = datetime.now() + timedelta(days=30)
            update_fields['tr52_available_date'] = tr52_date.strftime('%Y-%m-%d')
            update_fields['days_until_next_step'] = 30
            update_fields['redemption_end_date'] = tr52_date.strftime('%Y-%m-%d')
            update_vehicle_status(call_number, 'TOP Generated', update_fields)
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO police_logs (vehicle_id, communication_date, communication_type, notes) VALUES (?, ?, ?, ?)",
                           (call_number, datetime.now().strftime('%Y-%m-%d'), 'TOP Notification', 
                            f"TOP form sent to LEIN processor for jurisdiction: {data['jurisdiction']}"))
            conn.commit()
            conn.close()
            log_action("GENERATE_TOP", call_number, "TOP form generated and notified")
            # Placeholder for email/SMS/fax notification
            return send_file(pdf_path, as_attachment=True)
        logging.error(f"Failed to generate TOP: {error}")
        return jsonify({'error': error}), 500
    except Exception as e:
        logging.error(f"Error generating TOP: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/mark-tr52-ready/<call_number>', methods=['POST'])
def mark_tr52_ready(call_number):
    try:
        update_fields = {'tr52_received_date': datetime.now().strftime('%Y-%m-%d')}
        success = update_vehicle_status(call_number, 'TR52 Ready', update_fields)
        if success:
            log_action("TR52_READY", call_number, "TR52 form received")
            return jsonify({'status': 'success', 'message': 'Vehicle marked as TR52 Ready'})
        return jsonify({'status': 'error', 'message': 'Failed to update status'}), 500
    except Exception as e:
        logging.error(f"Error marking TR52 ready: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/paperwork-received/<call_number>', methods=['POST'])
def paperwork_received(call_number):
    try:
        update_fields = {'paperwork_received_date': datetime.now().strftime('%Y-%m-%d')}
        success = update_vehicle_status(call_number, 'Scheduled for Release', update_fields)
        if success:
            log_action("PAPERWORK_RECEIVED", call_number, "Paperwork received")
            return jsonify({'status': 'success', 'message': 'Paperwork received'})
        return jsonify({'status': 'error', 'message': 'Failed to update status'}), 500
    except Exception as e:
        logging.error(f"Error marking paperwork: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/decision/<call_number>', methods=['POST'])
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
        log_action("USER", call_number, f"Decision: Auction, scheduled for {auction_date}")
    elif decision == 'scrap':
        update_vehicle_status(call_number, 'Ready for Scrap')
        log_action("USER", call_number, "Decision: Scrap")
    else:
        conn.close()
        return jsonify({"error": "Invalid decision"}), 400
    
    conn.commit()
    conn.close()
    return jsonify({"message": "Decision recorded"}), 200

@app.route('/api/schedule-auction', methods=['POST'])
def schedule_auction():
    try:
        data = request.json
        vehicle_ids = data.get('vehicle_ids', [])
        auction_date = data.get('auction_date')
        if not vehicle_ids or not auction_date:
            return jsonify({'status': 'error', 'message': 'Missing vehicle IDs or auction date'}), 400
        success, message = create_auction(auction_date, vehicle_ids)
        if success:
            log_action("AUCTION_SCHEDULED", "BATCH", f"Auction scheduled: {message}")
            return jsonify({'status': 'success', 'message': message})
        return jsonify({'status': 'error', 'message': message}), 500
    except Exception as e:
        logging.error(f"Error scheduling auction: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/generate-release/<call_number>', methods=['POST'])
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
            vehicle_data[key] = vehicle_data[key] if vehicle_data[key] else 'N/A'
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
                'Title Transfer': 'Released'
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
            conn.commit()
            conn.close()
            log_action("RELEASE", call_number, f"Vehicle released: {release_reason}")
            return send_file(pdf_path, as_attachment=True)
        return jsonify({'error': error}), 500
    except Exception as e:
        logging.error(f"Error generating release: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/mark-released/<call_number>', methods=['POST'])
def mark_released(call_number):
    try:
        data = request.json
        success = release_vehicle(call_number, data.get('release_reason', 'Not specified'),
                                 data.get('recipient', 'Not specified'), data.get('release_date'),
                                 data.get('release_time'))
        if success:
            log_action("RELEASE", call_number, f"Marked as released: {data.get('release_reason')}")
            return jsonify({'status': 'success'})
        return jsonify({'error': 'Failed to release vehicle'}), 500
    except Exception as e:
        logging.error(f"Error marking released: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/logs')
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
            WHERE status = 'TR52 Ready'
        """)
        ready = cursor.fetchone()[0]
        conn.close()
        return jsonify({
            'overdue': overdue,
            'dueToday': due_today,
            'ready': ready
        })
    except Exception as e:
        logging.error(f"Error getting workflow counts: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/statistics')
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
            SELECT action, vehicle_id, details, timestamp
            FROM logs
            ORDER BY timestamp DESC
            LIMIT 5
        """)
        recent_activity = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return jsonify({
            'totalVehicles': total_vehicles,
            'statusCounts': status_counts,
            'jurisdictionCounts': jurisdiction_counts,
            'avgProcessingDays': round(avg_processing_days, 1) if avg_processing_days else 0,
            'recentActivity': recent_activity
        })
    except Exception as e:
        logging.error(f"Error getting statistics: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = 5000
    if is_port_in_use(port):
        logging.warning(f"Port {port} is in use. Trying port {port + 1}")
        port += 1
    status_thread = threading.Thread(target=run_status_checks, daemon=True)
    status_thread.start()
    app.run(debug=True, host='0.0.0.0', port=port)