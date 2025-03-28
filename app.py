from flask import Flask, render_template, send_file, request, jsonify
from database import (init_db, get_vehicles, get_vehicles_by_status, update_vehicle_status, 
                      update_vehicle, insert_vehicle, get_db_connection, check_and_update_statuses, 
                      get_logs, toggle_archive_status, create_auction, batch_update_status)
from generator import PDFGenerator
from scraper import TowBookScraper
from utils import (get_progress_mock, generate_invoice_number, release_vehicle, log_action, 
                   ensure_logs_table_exists, setup_logging, ensure_directories, get_status_filter)
from datetime import datetime, timedelta
import threading
import os
import csv
import time
import logging
import sqlite3
from api_routes import register_api_routes
import json

# Configure logging
setup_logging()

app = Flask(__name__)

# Initialize key components
init_db()
ensure_logs_table_exists()  # Make sure logs table exists
register_api_routes(app)
pdf_gen = PDFGenerator()
scraper = None  # Will be initialized on first scrape

@app.route('/')
def index():
    status = request.args.get('status', 'New')
    return render_template('batch_review.html', status=status)

@app.route('/api/vehicles')
def api_vehicles():
    status_type = request.args.get('status_type')
    count_by_status = request.args.get('count_by_status') == 'true'
    auction_only = request.args.get('auction_only') == 'true'
    call_number = request.args.get('call_number')
    sort_column = request.args.get('sort')
    sort_direction = request.args.get('direction', 'asc')
    
    if count_by_status:
        # Get counts for each status type
        conn = get_db_connection()
        cursor = conn.cursor()
        counts = {
            'new': cursor.execute("SELECT COUNT(*) FROM vehicles WHERE status = 'New' AND archived = 0").fetchone()[0],
            'topSent': cursor.execute("SELECT COUNT(*) FROM vehicles WHERE status = 'TOP Generated' AND archived = 0").fetchone()[0],
            'ready': cursor.execute("SELECT COUNT(*) FROM vehicles WHERE status = 'Ready for Disposition' AND archived = 0").fetchone()[0],
            'paperwork': cursor.execute("SELECT COUNT(*) FROM vehicles WHERE status = 'Paperwork Received' AND archived = 0").fetchone()[0],
            'action': cursor.execute("SELECT COUNT(*) FROM vehicles WHERE status IN ('Ready for Auction', 'Ready for Scrap') AND archived = 0").fetchone()[0],
            'inAuction': cursor.execute("SELECT COUNT(*) FROM vehicles WHERE status = 'In Auction' AND archived = 0").fetchone()[0],
            'completed': cursor.execute("SELECT COUNT(*) FROM vehicles WHERE status IN ('Released', 'Auctioned', 'Scrapped') OR archived = 1").fetchone()[0],
            'active': cursor.execute("SELECT COUNT(*) FROM vehicles WHERE archived = 0").fetchone()[0],
            'total': cursor.execute("SELECT COUNT(*) FROM vehicles").fetchone()[0]
        }
        conn.close()
        return jsonify({'status': 'success', 'counts': counts})
    
    if call_number:
        conn = get_db_connection()
        vehicle = conn.execute("SELECT * FROM vehicles WHERE towbook_call_number = ?", (call_number,)).fetchone()
        conn.close()
        vehicle_data = dict(vehicle) if vehicle else {}
        logging.info(f"Retrieved vehicle for call_number {call_number}: {vehicle_data}")
        return jsonify([vehicle_data] if vehicle else [])
    
    # For auction-ready vehicles only
    if auction_only:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM vehicles 
            WHERE status = 'Ready for Auction'
            ORDER BY tow_date ASC
        ''')
        vehicles = cursor.fetchall()
        conn.close()
        vehicle_list = [dict(v) for v in vehicles]
        return jsonify(vehicle_list)
    
    # Map status_type to actual database statuses
    status_filter = get_status_filter(status_type)
    
    vehicles = get_vehicles_by_status(status_filter, sort_column, sort_direction)
    
    # Add countdown information to each vehicle
    for vehicle in vehicles:
        if 'tow_date' in vehicle and vehicle['tow_date']:
            try:
                tow_date = datetime.strptime(vehicle['tow_date'], '%Y-%m-%d')
                days_since_tow = (datetime.now() - tow_date).days
                vehicle['days_since_tow'] = days_since_tow
                
                # Calculate countdown based on status
                if vehicle['status'] == 'TOP Generated' and vehicle['tr52_available_date']:
                    # Days until Ready for Disposition
                    tr52_date = datetime.strptime(vehicle['tr52_available_date'], '%Y-%m-%d')
                    days_until_ready = max(0, (tr52_date - datetime.now()).days)
                    vehicle['days_until_next_step'] = days_until_ready
                    vehicle['next_step_label'] = 'days until Ready for Disposition'
                    
                elif vehicle['status'] == 'In Auction' and vehicle['auction_date']:
                    # Days until auction
                    auction_date = datetime.strptime(vehicle['auction_date'], '%Y-%m-%d')
                    days_until_auction = max(0, (auction_date - datetime.now()).days)
                    vehicle['days_until_auction'] = days_until_auction
            except Exception as e:
                # If we can't parse the date, just continue
                logging.warning(f"Error processing dates for vehicle {vehicle['towbook_call_number']}: {e}")
                pass
    
    vehicle_list = [dict(v) for v in vehicles]
    logging.info(f"Retrieved {len(vehicle_list)} vehicles for status type {status_type}")
    return jsonify(vehicle_list)

@app.route('/api/vehicles/<call_number>', methods=['PUT'])
def update_vehicle_api(call_number):
    try:
        data = request.json
        success, message = update_vehicle(call_number, data)
        
        if success:
            return jsonify({'status': 'success', 'message': message})
        else:
            return jsonify({'status': 'error', 'message': message}), 400
            
    except Exception as e:
        logging.error(f"Error updating vehicle {call_number}: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/vehicles/add', methods=['POST'])
def add_vehicle():
    try:
        data = request.json
        required_fields = ['towbook_call_number', 'tow_date']
        
        # Validate required fields
        for field in required_fields:
            if not data.get(field):
                return jsonify({'status': 'error', 'message': f'Missing required field: {field}'}), 400
        
        # Default values
        if 'status' not in data:
            data['status'] = 'New'
        if 'archived' not in data:
            data['archived'] = 0
            
        # Insert the vehicle
        success, message = insert_vehicle(data)
        
        if success:
            return jsonify({'status': 'success', 'message': message})
        else:
            return jsonify({'status': 'error', 'message': message}), 400
            
    except Exception as e:
        logging.error(f"Error adding vehicle: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/vehicles/toggle-status/<call_number>', methods=['POST'])
def toggle_vehicle_status(call_number):
    try:
        success, message = toggle_archive_status(call_number)
        
        if success:
            return jsonify({'status': 'success', 'message': message})
        else:
            return jsonify({'status': 'error', 'message': message}), 400
    except Exception as e:
        logging.error(f"Error toggling vehicle status: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/update-status/<call_number>', methods=['POST'])
def update_status_api(call_number):
    try:
        data = request.json
        new_status = data.get('status')
        update_fields = data.get('fields', {})
        
        if not new_status:
            return jsonify({'status': 'error', 'message': 'Status not provided'}), 400
            
        success = update_vehicle_status(call_number, new_status, update_fields)
        
        if success:
            return jsonify({'status': 'success', 'message': f'Status updated to {new_status}'})
        return jsonify({'status': 'error', 'message': 'Failed to update status'}), 500
    except Exception as e:
        logging.error(f"Error updating status: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/generate-top/<call_number>', methods=['POST'])
def generate_top(call_number):
    try:
        conn = get_db_connection()
        vehicle = conn.execute("SELECT * FROM vehicles WHERE towbook_call_number = ?", (call_number,)).fetchone()
        conn.close()
        
        if not vehicle:
            return jsonify({'error': 'Vehicle not found'}), 404
        
        data = dict(vehicle)
        pdf_path = f"static/generated_pdfs/TOP_{call_number}.pdf"
        os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
        success, error = pdf_gen.generate_top(data, pdf_path)
        
        if success:
            update_fields = {'top_form_sent_date': datetime.now().strftime('%Y-%m-%d')}
            update_vehicle_status(call_number, 'TOP Generated', update_fields)
            
            try:
                log_action("GENERATE_TOP", call_number, "TOP form generated and status updated")
            except Exception as e:
                logging.error(f"Failed to log TOP generation: {e}")
                
            return send_file(pdf_path, as_attachment=True)
        else:
            logging.error(f"Failed to generate TOP form: {error}")
            return jsonify({'error': error}), 500
    except Exception as e:
        logging.error(f"Error generating TOP for {call_number}: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/paperwork-received/<call_number>', methods=['POST'])
def paperwork_received(call_number):
    try:
        # Update status to Paperwork Received
        update_fields = {
            'paperwork_received_date': datetime.now().strftime('%Y-%m-%d')
        }
        
        success = update_vehicle_status(call_number, 'Paperwork Received', update_fields)
        
        if success:
            return jsonify({'status': 'success', 'message': 'Paperwork received and status updated'})
        return jsonify({'status': 'error', 'message': 'Failed to update status'}), 500
    except Exception as e:
        logging.error(f"Error marking paperwork received: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/decision/<call_number>', methods=['POST'])
def make_decision(call_number):
    try:
        data = request.json
        decision = data.get('decision')
        
        if decision not in ['auction', 'scrap']:
            return jsonify({'status': 'error', 'message': 'Invalid decision'}), 400
            
        # Update status based on decision
        new_status = 'Ready for Auction' if decision == 'auction' else 'Ready for Scrap'
        update_fields = {
            'decision': decision.capitalize(),
            'decision_date': datetime.now().strftime('%Y-%m-%d')
        }
        
        success = update_vehicle_status(call_number, new_status, update_fields)
        
        if success:
            return jsonify({'status': 'success', 'message': f'Decision set to {decision}'})
        return jsonify({'status': 'error', 'message': 'Failed to update decision'}), 500
    except Exception as e:
        logging.error(f"Error setting decision: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/schedule-auction', methods=['POST'])
def schedule_auction():
    try:
        data = request.json
        vehicle_ids = data.get('vehicle_ids', [])
        auction_date = data.get('auction_date')
        
        if not vehicle_ids:
            return jsonify({'status': 'error', 'message': 'No vehicles specified'}), 400
            
        if not auction_date:
            return jsonify({'status': 'error', 'message': 'No auction date specified'}), 400
        
        # Create auction and add vehicles
        success, message = create_auction(auction_date, vehicle_ids)
        
        if success:
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
        
        if vehicle:
            # Combine vehicle data with release info
            vehicle_data = dict(vehicle)
            vehicle_data.update(data)
            
            # Use provided release date or default to today
            if data.get('release_date'):
                vehicle_data['release_date'] = data.get('release_date')
            elif not vehicle_data.get('release_date'):
                vehicle_data['release_date'] = datetime.now().strftime('%Y-%m-%d')
                
            # Use provided release time or default to current time
            if data.get('release_time'):
                vehicle_data['release_time'] = data.get('release_time')
            elif not vehicle_data.get('release_time'):
                vehicle_data['release_time'] = datetime.now().strftime('%H:%M')
            
            pdf_path = f"static/generated_pdfs/Release_{call_number}.pdf"
            os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
            
            success, error = pdf_gen.generate_release_notice(vehicle_data, pdf_path)
            
            if success:
                # Update vehicle with release info
                release_vehicle(
                    call_number, 
                    data.get('release_reason', 'Not specified'),
                    data.get('recipient', 'Not specified'),
                    data.get('release_date'),
                    data.get('release_time')
                )
                return send_file(pdf_path, as_attachment=True)
            return jsonify({'error': error}), 500
        return jsonify({'error': 'Vehicle not found'}), 404
    except Exception as e:
        logging.error(f"Error generating release notice: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/mark-released/<call_number>', methods=['POST'])
def mark_released(call_number):
    try:
        data = request.json
        
        if not data.get('release_reason'):
            return jsonify({'error': 'Release reason is required'}), 400
            
        success = release_vehicle(
            call_number, 
            data.get('release_reason', 'Not specified'),
            data.get('recipient', 'Not specified'),
            data.get('release_date'),
            data.get('release_time')
        )
        
        if success:
            return jsonify({'status': 'success'})
        return jsonify({'error': 'Failed to release vehicle'}), 500
    except Exception as e:
        logging.error(f"Error marking vehicle as released: {e}")
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

@app.route('/api/clear-database', methods=['POST'])
def clear_database():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM vehicles")
        conn.commit()
        conn.close()
        
        try:
            log_action("SYSTEM", "ALL", "Database cleared")
        except Exception as e:
            logging.error(f"Failed to log database clear: {e}")
            
        return jsonify({'status': 'success'})
    except Exception as e:
        logging.error(f"Error clearing database: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/import-csv', methods=['POST'])
def import_csv():
    if 'file' not in request.files:
        return jsonify({'status': 'error', 'message': 'No file provided'}), 400
        
    file = request.files['file']
    if not file.filename.endswith('.csv'):
        return jsonify({'status': 'error', 'message': 'File must be a CSV'}), 400
        
    try:
        csv_data = file.read().decode('utf-8').splitlines()
        reader = csv.DictReader(csv_data)
        
        vehicles_added = 0
        for row in reader:
            # Skip empty rows
            if not row.get('towbook_call_number'):
                continue
                
            vehicle_data = {
                'towbook_call_number': row.get('towbook_call_number', ''),
                'jurisdiction': row.get('jurisdiction', ''),
                'tow_date': row.get('tow_date', ''),
                'tow_time': row.get('tow_time', ''),
                'location': row.get('pickup_location', ''),  # Using pickup_location
                'requestor': 'PROPERTY OWNER',  # Default value
                'vin': row.get('vin', ''),
                'year': row.get('year', ''),
                'make': row.get('make', ''),
                'model': row.get('model', ''),
                'color': row.get('color', ''),
                'plate': row.get('plate', ''),
                'state': '',  # Not specified in CSV
                'case_number': '',  # Not specified in CSV
                'officer_name': row.get('officer', ''),
                'complaint_number': row.get('id', ''),
                'status': row.get('current_status', 'New') or 'New',
                'owner_known': 'Yes' if row.get('vin') or row.get('plate') else 'No'
            }
            
            # Add any TR-52 specific fields if present
            if row.get('tr52_status'):
                vehicle_data['tr52_status'] = row.get('tr52_status')
            
            if row.get('our_custody'):
                vehicle_data['our_custody'] = row.get('our_custody')
            
            # Insert vehicle into database
            success, _ = insert_vehicle(vehicle_data)
            if success:
                vehicles_added += 1
            
        # Log the import action
        try:
            log_action("IMPORT_CSV", "BATCH", f"Imported {vehicles_added} vehicles from CSV")
        except Exception as e:
            logging.error(f"Failed to log CSV import: {e}")
            
        return jsonify({'status': 'success', 'message': f'Successfully imported {vehicles_added} vehicles'})
    except Exception as e:
        logging.error(f"Error importing CSV: {e}")
        return jsonify({'status': 'error', 'message': f'Failed to import CSV: {str(e)}'}), 500

@app.route('/api/start-scraping', methods=['POST'])
def start_scraping():
    global scraper
    try:
        data = request.json
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        
        if not start_date or not end_date:
            return jsonify({'status': 'error', 'message': 'Both start and end dates are required'}), 400
            
        # Validate date format
        try:
            start_date_obj = datetime.strptime(start_date, '%Y-%m-%d')
            end_date_obj = datetime.strptime(end_date, '%Y-%m-%d')
            
            if start_date_obj > end_date_obj:
                return jsonify({'status': 'error', 'message': 'Start date cannot be after end date'}), 400
                
        except ValueError:
            return jsonify({'status': 'error', 'message': 'Invalid date format. Use YYYY-MM-DD format'}), 400
            
        if not hasattr(app, 'scraping_thread') or not app.scraping_thread.is_alive():
            if scraper is None:
                scraper = TowBookScraper("iTow05", "iTow2023", database='vehicles.db')
            
            app.scraping_thread = threading.Thread(
                target=lambda: scraper.start_scraping_with_date_range(start_date, end_date)
            )
            
            app.scraping_thread.daemon = True
            app.scraping_thread.start()
            return jsonify({'status': 'started'})
        return jsonify({'status': 'running'})
    except Exception as e:
        logging.error(f"Error starting scraping: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500
    
@app.route('/api/import-call-numbers', methods=['POST'])
def import_call_numbers():
    if 'file' not in request.files:
        return jsonify({'status': 'error', 'message': 'No file provided'}), 400
        
    file = request.files['file']
    if not file.filename.endswith('.csv'):
        return jsonify({'status': 'error', 'message': 'File must be a CSV'}), 400
        
    try:
        csv_data = file.read().decode('utf-8').splitlines()
        reader = csv.DictReader(csv_data)
        
        call_refs = []
        for row in reader:
            call_number = row.get('towbook_call_number')
            complaint_number = row.get('complaint_number', '')
            call_refs.append({
                'towbook_call_number': str(call_number).strip(),
                'complaint_number': complaint_number.strip() if complaint_number else ''
            })
        
        # Start scraping
        global scraper
        if not hasattr(app, 'scraping_thread') or not app.scraping_thread.is_alive():
            if scraper is None:
                scraper = TowBookScraper("iTow05", "iTow2023", database='vehicles.db')
            
            app.scraping_thread = threading.Thread(
                target=lambda: scraper.scrape_specific_call_numbers(call_refs)
            )
            app.scraping_thread.daemon = True
            app.scraping_thread.start()
            
            return jsonify({'status': 'started', 'message': f'Started scraping {len(call_refs)} call numbers'})
        else:
            return jsonify({'status': 'running', 'message': 'Scraping is already running'})
            
    except Exception as e:
        logging.error(f"Error importing call numbers: {e}")
        return jsonify({'status': 'error', 'message': f'Failed to import call numbers: {str(e)}'}), 500  

@app.route('/scraping-progress')
def scraping_progress():
    global scraper
    try:
        if scraper:
            progress = scraper.get_progress()
            return jsonify({
                'status': 'success',
                'progress': progress
            })
        return jsonify({
            'status': 'success',
            'progress': {'percentage': 0, 'is_running': False, 'processed': 0, 'total': 0}
        })
    except Exception as e:
        logging.error(f"Error getting scraping progress: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e),
            'progress': {'percentage': 0, 'is_running': False, 'processed': 0, 'total': 0}
        })
        
@app.route('/api/batch-update-status', methods=['POST'])
def batch_update_status_api():
    try:
        data = request.json
        vehicle_ids = data.get('vehicle_ids', [])
        new_status = data.get('status')
        
        if not vehicle_ids or not new_status:
            return jsonify({'status': 'error', 'message': 'Missing vehicle IDs or status'}), 400
            
        # Update the vehicles
        success, updated_count, message = batch_update_status(vehicle_ids, new_status)
        
        if success:
            return jsonify({
                'status': 'success', 
                'message': message
            })
        else:
            return jsonify({'status': 'error', 'message': message}), 500
    except Exception as e:
        logging.error(f"Error in batch update: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500
            
@app.route('/api/vehicles/<call_number>', methods=['DELETE'])
def delete_vehicle(call_number):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Handle null call_number
        if call_number == 'null':
            # Try to find the record using another field, e.g., VIN
            cursor.execute("SELECT vin FROM vehicles WHERE towbook_call_number IS NULL")
            record = cursor.fetchone()
            if not record:
                conn.close()
                return jsonify({'status': 'error', 'message': 'Vehicle not found'}), 404
            
            vin = record['vin']
            cursor.execute("DELETE FROM vehicles WHERE vin = ?", (vin,))
        else:
            # Normal deletion using call_number
            cursor.execute("SELECT * FROM vehicles WHERE towbook_call_number = ?", (call_number,))
            if not cursor.fetchone():
                conn.close()
                return jsonify({'status': 'error', 'message': 'Vehicle not found'}), 404
            
            cursor.execute("DELETE FROM vehicles WHERE towbook_call_number = ?", (call_number,))
        
        conn.commit()
        conn.close()
        
        # Log the deletion
        try:
            log_action("DELETE", call_number, f"Vehicle deleted: {call_number}")
        except Exception as e:
            logging.error(f"Failed to log deletion: {e}")
            
        return jsonify({'status': 'success'})
    
    except Exception as e:
        logging.error(f"Error deleting vehicle {call_number}: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500      

def run_status_checks():
    """Background thread to check for vehicles that should have status updates"""
    while True:
        try:
            check_and_update_statuses()
            
            try:
                log_action("SYSTEM", "AUTO", "Ran automated status checks")
            except Exception as e:
                logging.error(f"Failed to log status check: {e}")
                
        except Exception as e:
            logging.error(f"Error in status check: {e}")
            
        time.sleep(86400)  # Check daily
        
        
if __name__ == '__main__':
    # Ensure database structure is set up correctly
    from migrate_db import initialize_database
    initialize_database()
    
    # Run status checks in background thread
    threading.Thread(target=run_status_checks, daemon=True).start()
    
    # Start the Flask app
    app.run(debug=True, host='0.0.0.0')