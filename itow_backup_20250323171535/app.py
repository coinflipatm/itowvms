from flask import Flask, render_template, send_file, request, jsonify
from database import init_db, get_vehicles, update_status, insert_vehicle, get_db_connection, check_and_update_statuses, get_logs
from generator import PDFGenerator
from scraper import TowBookScraper
from utils import get_progress_mock, update_vehicle_status, generate_invoice_number, release_vehicle, log_action, ensure_logs_table_exists
from datetime import datetime, timedelta
import threading
import os
import csv
import time
import logging
import sqlite3

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)

# Initialize key components
init_db()
ensure_logs_table_exists()  # Make sure logs table exists
pdf_gen = PDFGenerator()
scraper = None  # Will be initialized on first scrape

@app.route('/')
def index():
    tab = request.args.get('tab', 'active')
    return render_template('batch_review.html', tab=tab)

@app.route('/api/vehicles')
def api_vehicles():
    tab = request.args.get('tab', 'active')
    call_number = request.args.get('call_number')
    
    if call_number:
        conn = get_db_connection()
        vehicle = conn.execute("SELECT * FROM vehicles WHERE towbook_call_number = ?", (call_number,)).fetchone()
        conn.close()
        vehicle_data = dict(vehicle) if vehicle else {}
        logging.info(f"Retrieved vehicle for call_number {call_number}: {vehicle_data}")
        return jsonify([vehicle_data] if vehicle else [])
    
    vehicles = get_vehicles(tab if tab in ['active', 'completed'] else None)
    vehicle_list = [dict(v) for v in vehicles]
    logging.info(f"Retrieved {len(vehicle_list)} vehicles for tab {tab}: {vehicle_list}")
    return jsonify(vehicle_list)

@app.route('/api/vehicles/<call_number>', methods=['PUT'])
def update_vehicle(call_number):
    try:
        data = request.json
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if vehicle exists
        cursor.execute("SELECT * FROM vehicles WHERE towbook_call_number = ?", (call_number,))
        if not cursor.fetchone():
            conn.close()
            return jsonify({'status': 'error', 'message': 'Vehicle not found'}), 404
        
        # Build update statement
        fields = []
        values = []
        for key, value in data.items():
            if key != 'towbook_call_number':
                fields.append(f"{key} = ?")
                values.append(value)
        
        if fields:
            sql = f"UPDATE vehicles SET {', '.join(fields)}, last_updated = ? WHERE towbook_call_number = ?"
            values.append(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            values.append(call_number)
            cursor.execute(sql, values)
            conn.commit()
            logging.info(f"Updated vehicle {call_number} with fields: {', '.join(data.keys())}")
            
            try:
                log_action("UPDATE", call_number, f"Updated fields: {', '.join(data.keys())}")
            except Exception as e:
                logging.error(f"Failed to log update: {e}")
        
        conn.close()
        return jsonify({'status': 'success'})
    except Exception as e:
        logging.error(f"Error updating vehicle {call_number}: {e}")
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
            update_vehicle_status(call_number, 'TOP Sent', update_fields)
            
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
            if not vehicle_data.get('release_time'):
                vehicle_data['release_time'] = datetime.now().strftime('%H:%M')
            
            pdf_path = f"static/generated_pdfs/Release_{call_number}.pdf"
            os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
            
            success, error = pdf_gen.generate_release_notice(vehicle_data, pdf_path)
            
            if success:
                # Update vehicle with release info
                release_vehicle(
                    call_number, 
                    data.get('release_reason', 'Not specified'),
                    data.get('recipient', 'Not specified')
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
        success = release_vehicle(
            call_number, 
            data.get('release_reason', 'Not specified'),
            data.get('recipient', 'Not specified'),
            data.get('release_date')
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
                'reference_number': row.get('id', ''),
                'status': row.get('current_status', 'New') or 'New',
                'owner_known': 'Yes' if row.get('vin') or row.get('plate') else 'No'
            }
            
            # Add any TR-52 specific fields if present
            if row.get('tr52_status'):
                vehicle_data['tr52_status'] = row.get('tr52_status')
            
            if row.get('our_custody'):
                vehicle_data['our_custody'] = row.get('our_custody')
            
            # Insert vehicle into database
            insert_vehicle(vehicle_data)
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
            reference_number = row.get('reference_number', '')
            call_refs.append({
                'towbook_call_number': str(call_number).strip(),
                'reference_number': reference_number.strip() if reference_number else ''
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