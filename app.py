from flask import Flask, render_template, send_file, request, jsonify
from database import (init_db, get_vehicles_by_status, update_vehicle_status, 
                      update_vehicle, insert_vehicle, get_db_connection, check_and_update_statuses, 
                      get_logs, toggle_archive_status, create_auction, batch_update_status)
from generator import PDFGenerator
from scraper import TowBookScraper
from utils import (generate_complaint_number, release_vehicle, log_action, 
                   ensure_logs_table_exists, setup_logging, get_status_filter)
from datetime import datetime, timedelta
import threading
import os
import logging
import time
import socket
import json

# Configure logging
setup_logging()

app = Flask(__name__)

# Initialize components
init_db()
ensure_logs_table_exists()
pdf_gen = PDFGenerator()
scraper = None  # Initialized on first scrape

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
            time.sleep(3600)  # Hourly check (1 hour)
        except Exception as e:
            logging.error(f"Status check error: {e}")
            time.sleep(60)  # Brief sleep on error

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
        sort_direction = request.args.get('direction', 'desc')  # Default to newest first
        
        logging.info(f"API request: status_type={status_type}, sort={sort_column}, direction={sort_direction}")
        
        if count_by_status:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Get exact counts for each status
            cursor.execute("SELECT status, COUNT(*) as count FROM vehicles GROUP BY status")
            status_breakdown = {row[0] or 'undefined': row[1] for row in cursor.fetchall()}
            
            # Calculate counts for UI categories
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
            return jsonify([vehicle_data] if vehicle else [])
        
        if auction_only:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM vehicles WHERE status = 'Auction' AND archived = 0 ORDER BY tow_date DESC")
            vehicles = [dict(v) for v in cursor.fetchall()]
            conn.close()
            return jsonify(vehicles)
        
        if status_type:
            vehicles = get_vehicles_by_status(status_type, sort_column, sort_direction)
            logging.info(f"Found {len(vehicles)} vehicles for status type {status_type}")
        else:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Add sorting if specified
            sort_by = "tow_date DESC"  # Default sort
            if sort_column:
                # Sanitize sort column
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
            if 'tow_date' in vehicle and vehicle['tow_date']:
                try:
                    tow_date = datetime.strptime(vehicle['tow_date'], '%Y-%m-%d')
                    vehicle['days_since_tow'] = (datetime.now() - tow_date).days
                    
                    if vehicle['status'] == 'TOP Generated' and vehicle.get('tr52_available_date'):
                        tr52_date = datetime.strptime(vehicle['tr52_available_date'], '%Y-%m-%d')
                        vehicle['days_until_next_step'] = max(0, (tr52_date - datetime.now()).days)
                        vehicle['next_step_label'] = 'days until TR52 Ready'
                    
                    elif vehicle['status'] == 'TR52 Ready':
                        vehicle['next_step_label'] = 'days since TR52 Ready'
                        vehicle['days_until_next_step'] = vehicle.get('days_until_next_step', 0)
                    
                    elif vehicle['status'] == 'Ready for Scrap' and vehicle.get('estimated_date'):
                        estimated_date = datetime.strptime(vehicle['estimated_date'], '%Y-%m-%d')
                        vehicle['days_until_next_step'] = max(0, (estimated_date - datetime.now()).days)
                        vehicle['next_step_label'] = 'days until legal scrap date'
                        
                    elif vehicle['status'] == 'Ready for Auction' and vehicle.get('auction_date'):
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
    """Delete a vehicle completely from the database"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if vehicle exists
        cursor.execute("SELECT COUNT(*) FROM vehicles WHERE towbook_call_number = ?", (call_number,))
        if cursor.fetchone()[0] == 0:
            conn.close()
            return jsonify({'status': 'error', 'message': 'Vehicle not found'}), 404
        
        # Delete logs first (foreign key constraint)
        cursor.execute("DELETE FROM logs WHERE vehicle_id = ?", (call_number,))
        
        # Then delete the vehicle
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
            
        # Use the update_vehicle_status function from utils
        from utils import update_vehicle_status, convert_frontend_status
        
        # Convert status if needed (frontend to database format)
        if new_status:
            new_status = convert_frontend_status(new_status)
            
        # Log the status change attempt
        logging.info(f"Attempting status update for {call_number} to {new_status}")
        
        # Update the status
        success = update_vehicle_status(call_number, new_status)
        
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
            # Update the status to TOP Generated
            update_fields = {'top_form_sent_date': datetime.now().strftime('%Y-%m-%d')}
            
            # Calculate the TR52 available date (20 days from now)
            tr52_date = datetime.now() + timedelta(days=20)
            update_fields['tr52_available_date'] = tr52_date.strftime('%Y-%m-%d')
            update_fields['days_until_next_step'] = 20
            
            # Update the status
            update_vehicle_status(call_number, 'TOP Generated', update_fields)
            log_action("GENERATE_TOP", call_number, "TOP form generated")
            return send_file(pdf_path, as_attachment=True)
        logging.error(f"Failed to generate TOP: {error}")
        return jsonify({'error': error}), 500
    except Exception as e:
        logging.error(f"Error generating TOP: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/mark-tr52-ready/<call_number>', methods=['POST'])
def mark_tr52_ready(call_number):
    """Mark a vehicle as TR52 Ready, indicating the TR52 form has been received"""
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
    ad_placement_date = result['ad_placement_date'] if result and result['ad_placement_date'] else None

    if decision == 'auction':
        auction_date = calculate_next_auction_date(ad_placement_date)
        update_vehicle_status(call_number, 'Ready for Auction', {'auction_date': auction_date.strftime('%Y-%m-%d')})
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
        vehicle_data.update(data)
        vehicle_data['release_date'] = data.get('release_date', datetime.now().strftime('%Y-%m-%d'))
        vehicle_data['release_time'] = data.get('release_time', datetime.now().strftime('%H:%M'))
        pdf_path = f"static/generated_pdfs/Release_{call_number}.pdf"
        os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
        success, error = pdf_gen.generate_release_notice(vehicle_data, pdf_path)
        if success:
            release_vehicle(call_number, data.get('release_reason', 'Not specified'),
                           data.get('recipient', 'Not specified'), vehicle_data['release_date'],
                           vehicle_data['release_time'])
            log_action("RELEASE", call_number, f"Vehicle released: {data.get('release_reason')}")
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

@app.route('/api/start-scraping', methods=['POST'])
def start_scraping():
    global scraper
    try:
        data = request.json
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        headless = data.get('headless', True)  # Default to headless mode
        
        if not start_date or not end_date:
            return jsonify({'status': 'error', 'message': 'Dates required'}), 400
        
        if scraper is None:
            scraper = TowBookScraper("iTow05", "iTow2023", database='vehicles.db')
        
        app.scraping_thread = threading.Thread(
            target=lambda: scraper.start_scraping_with_date_range(start_date, end_date, headless)
        )
        app.scraping_thread.daemon = True
        app.scraping_thread.start()
        
        return jsonify({'status': 'started'})
    except Exception as e:
        logging.error(f"Error starting scraping: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/scraping-progress')
def scraping_progress():
    global scraper
    try:
        if scraper:
            return jsonify({'status': 'success', 'progress': scraper.get_progress()})
        return jsonify({'status': 'success', 'progress': {'percentage': 0, 'is_running': False, 'processed': 0, 'total': 0}})
    except Exception as e:
        logging.error(f"Error getting progress: {e}")
        return jsonify({'status': 'error', 'message': str(e), 'progress': {'percentage': 0, 'is_running': False}})

@app.route('/api/workflow-counts')
def workflow_counts():
    """Get workflow counts for dashboard"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        today = datetime.now().strftime('%Y-%m-%d')
        
        # Overdue actions
        cursor.execute("""
            SELECT COUNT(*) FROM vehicles
            WHERE status = 'New' AND last_updated < DATE('now', '-2 day')
            OR (status = 'TOP Generated' AND last_updated < DATE('now', '-20 day'))
        """)
        overdue = cursor.fetchone()[0]
        
        # Actions due today
        cursor.execute("""
            SELECT COUNT(*) FROM vehicles
            WHERE status = 'New' AND last_updated = DATE('now', '-2 day')
            OR (status = 'TOP Generated' AND last_updated = DATE('now', '-20 day'))
        """)
        due_today = cursor.fetchone()[0]
        
        # Ready for disposition
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
    """Get overall statistics for dashboard"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Total vehicles
        cursor.execute("SELECT COUNT(*) FROM vehicles")
        total_vehicles = cursor.fetchone()[0]
        
        # Vehicles by status
        cursor.execute("""
            SELECT status, COUNT(*) as count
            FROM vehicles
            GROUP BY status
        """)
        status_counts = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Vehicles by jurisdiction
        cursor.execute("""
            SELECT jurisdiction, COUNT(*) as count
            FROM vehicles
            WHERE jurisdiction IS NOT NULL AND jurisdiction != ''
            GROUP BY jurisdiction
            ORDER BY count DESC
            LIMIT 5
        """)
        jurisdiction_counts = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Vehicle processing time
        cursor.execute("""
            SELECT 
                AVG(JULIANDAY(COALESCE(release_date, DATE('now'))) - JULIANDAY(tow_date)) as avg_days
            FROM vehicles
            WHERE tow_date IS NOT NULL
        """)
        avg_processing_days = cursor.fetchone()[0]
        
        # Recent activity
        cursor.execute("""
            SELECT action_type, vehicle_id, details, timestamp
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