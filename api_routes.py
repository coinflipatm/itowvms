"""
API routes for enhanced features in iTow Impound Manager
"""
from datetime import datetime, timedelta
from collections import defaultdict
from flask import Blueprint, request, jsonify, send_file, current_app
from database import get_db_connection, get_vehicles, get_pending_notifications, get_contacts, get_contact_by_id, add_contact_explicit, update_contact_explicit, delete_contact_explicit
from utils import log_action, convert_frontend_status
from scraper import TowBookScraper # Add this import
import logging # Added import for logging
from io import BytesIO, StringIO # Added BytesIO import for exporting files
import os # Added import for os
from threading import Thread  # Added for background scraping
from genesee_jurisdictions import get_jurisdiction_list

# Create blueprint
api = Blueprint('api', __name__)

# Workflow management routes
@api.route('/api/workflow-counts')
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
            OR (status = 'TOP Generated' AND owner_known = 'Yes' AND last_updated < DATE('now', '-30 day'))
            OR (status = 'TOP Generated' AND owner_known = 'No' AND last_updated < DATE('now', '-10 day'))
        """)
        overdue = cursor.fetchone()[0]
        
        # Actions due today
        cursor.execute("""
            SELECT COUNT(*) FROM vehicles
            WHERE status = 'New' AND last_updated = DATE('now', '-2 day')
            OR (status = 'TOP Generated' AND owner_known = 'Yes' AND last_updated = DATE('now', '-30 day'))
            OR (status = 'TOP Generated' AND owner_known = 'No' AND last_updated = DATE('now', '-10 day'))
        """)
        due_today = cursor.fetchone()[0]
        
        # Ready for disposition
        cursor.execute("""
            SELECT COUNT(*) FROM vehicles
            WHERE status = 'Ready for Disposition'
        """)
        ready = cursor.fetchone()[0]
        
        conn.close()
        
        return jsonify({
            'overdue': overdue,
            'dueToday': due_today,
            'ready': ready
        })
    except Exception as e:
        print(f"Error getting workflow counts: {e}")
        return jsonify({'error': f'Error getting workflow counts: {str(e)}'}), 500

# Reporting routes
@api.route('/api/reports')
def get_reports():
    """Get report data for dashboard"""
    try:
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')
        report_type = request.args.get('type', 'summary')
        
        # Validate dates
        if not start_date_str or not end_date_str:
            return jsonify({'error': 'Start date and end date are required.'}), 400
        
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').strftime('%Y-%m-%d')
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').strftime('%Y-%m-%d')
        except ValueError:
            return jsonify({'error': 'Invalid date format. Please use YYYY-MM-DD.'}), 400
            
        # Get data from database
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Status distribution
        cursor.execute("""
            SELECT status, COUNT(*) as count
            FROM vehicles
            WHERE (date(tow_date) BETWEEN ? AND ?) OR (release_date IS NOT NULL AND date(release_date) BETWEEN ? AND ?)
            GROUP BY status
        """, (start_date, end_date, start_date, end_date))
        status_data = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Revenue data (example - adapt to your actual schema if different)
        cursor.execute("""
            SELECT 
                strftime('%Y-%m', release_date) as month_year,  -- Changed to YYYY-MM for better sorting
                COUNT(*) as count 
                -- SUM(release_fee) as total_revenue -- If you have a release_fee column
            FROM vehicles
            WHERE release_date IS NOT NULL AND date(release_date) BETWEEN ? AND ?
            GROUP BY month_year
            ORDER BY month_year
        """, (start_date, end_date))
        
        months = []
        counts = []
        for row in cursor.fetchall():
            # Convert month number to name
            month_name = datetime.strptime(row[0], '%Y-%m').strftime('%b %Y')
            months.append(month_name)
            counts.append(row[1])
            
        revenue_data = {
            'labels': months if months else ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
            'values': counts if counts else [0, 0, 0, 0, 0, 0]
        }
        
        # Processing time by status
        cursor.execute("""
            SELECT status,
                   AVG(JULIANDAY(COALESCE(date(release_date), date('now'))) - JULIANDAY(date(tow_date))) as avg_days
            FROM vehicles
            WHERE (date(tow_date) BETWEEN ? AND ?) OR (release_date IS NOT NULL AND date(release_date) BETWEEN ? AND ?)
            GROUP BY status
        """, (start_date, end_date, start_date, end_date))
        processing_time = {
            'labels': [],
            'values': []
        }
        for row in cursor.fetchall():
            processing_time['labels'].append(row[0] if row[0] else 'N/A')
            processing_time['values'].append(row[1] if row[1] is not None else 0)
        
        # Jurisdiction distribution
        cursor.execute("""
            SELECT jurisdiction, COUNT(*) as count
            FROM vehicles
            WHERE (date(tow_date) BETWEEN ? AND ?) OR (release_date IS NOT NULL AND date(release_date) BETWEEN ? AND ?)
            GROUP BY jurisdiction
        """, (start_date, end_date, start_date, end_date))
        jurisdiction_data = {row[0]: row[1] for row in cursor.fetchall()}

        conn.close()

        return jsonify({
            'statusDistribution': status_data,
            'revenueData': revenue_data,
            'processingTime': processing_time,
            'jurisdictionDistribution': jurisdiction_data,
            'reportType': report_type,
            'startDate': start_date,
            'endDate': end_date
        })

    except Exception as e:
        logging.error(f"Error getting reports: {e}", exc_info=True)
        return jsonify({'error': f'Error getting reports: {str(e)}'}), 500

# Enhanced vehicle search endpoint
@api.route('/api/vehicles/search')
def search_vehicles():
    """Search vehicles across multiple fields"""
    try:
        query = request.args.get('query', '')
        status_filter = request.args.get('status', 'all') # Example: 'all', 'active', 'completed'
        # Add more filters as needed: date ranges, jurisdiction, etc.

        if not query and status_filter == 'all':
            # Potentially return all vehicles or a subset if no specific query
            # For now, let's require a query if no other filter is strong
            # return jsonify({'error': 'Search query or specific filter required'}), 400
            pass # Allow fetching all if that's desired, or implement pagination


        conn = get_db_connection()
        # Base query
        sql_query = "SELECT * FROM vehicles WHERE 1=1"
        params = []

        if query:
            # Search across multiple relevant fields
            # Ensure to adjust field names based on your 'vehicles' table schema
            search_term = f"%{query}%"
            sql_query += """
                AND (
                    towbook_call_number LIKE ? OR
                    license_plate LIKE ? OR
                    vin LIKE ? OR
                    make LIKE ? OR
                    model LIKE ? OR
                    owner_name LIKE ? OR
                    complaint_number LIKE ?
                    -- Add other fields you want to search
                )
            """
            params.extend([search_term] * 7) # Adjust count based on number of fields

        if status_filter and status_filter != 'all':
            # Assuming convert_frontend_status can handle this or you map it directly
            # For simplicity, direct mapping or a helper might be better here
            if status_filter == 'active':
                sql_query += " AND status NOT IN (?, ?, ?, ?)"
                params.extend(['Released', 'Auctioned', 'Scrapped', 'Transferred'])
            elif status_filter == 'completed':
                sql_query += " AND status IN (?, ?, ?, ?)"
                params.extend(['Released', 'Auctioned', 'Scrapped', 'Transferred'])
            else: # Specific status
                sql_query += " AND status = ?"
                params.append(status_filter)
        
        # Add sorting and pagination here if needed
        sql_query += " ORDER BY tow_date DESC" # Example sorting

        vehicles_data = [dict(row) for row in conn.execute(sql_query, tuple(params)).fetchall()]
        conn.close()
        
        return jsonify(vehicles_data)
        
    except Exception as e:
        logging.error(f"Error searching vehicles: {e}", exc_info=True)
        return jsonify({'error': f'Error searching vehicles: {str(e)}'}), 500

# Export routes with improved error handling
@api.route('/api/vehicles/export/<export_format>') # Renamed 'format' to 'export_format'
def export_vehicles(export_format):
    """Export vehicle data"""
    try:
        # Fetch all vehicles or based on some filters (similar to search)
        conn = get_db_connection()
        vehicles_cursor = conn.execute("SELECT * FROM vehicles ORDER BY tow_date DESC")
        vehicles_list = [dict(row) for row in vehicles_cursor.fetchall()]
        conn.close()

        if not vehicles_list:
            return jsonify({"message": "No vehicles to export."}), 404

        if export_format.lower() == 'csv':
            from io import StringIO
            import csv
            si = StringIO()
            cw = csv.writer(si)
            # Write header (use keys from the first vehicle dict)
            headers = vehicles_list[0].keys()
            cw.writerow(headers)
            # Write rows
            for vehicle in vehicles_list:
                cw.writerow([vehicle.get(h, '') for h in headers]) # Use .get for safety
            
            output = si.getvalue()
            return send_file(
                BytesIO(output.encode('utf-8')),
                mimetype='text/csv',
                as_attachment=True,
                download_name='vehicles_export.csv'
            )
        elif export_format.lower() == 'json':
            return jsonify(vehicles_list)
        # Add other formats like Excel (xlsx) if needed, using libraries like openpyxl
        # elif export_format.lower() == 'xlsx':
        #     # ... implementation for Excel export ...
        #     pass
        else:
            return jsonify({'error': 'Unsupported format. Use "csv" or "json".'}), 400
        
    except Exception as e:
        logging.error(f"Error exporting vehicles: {e}", exc_info=True)
        return jsonify({'error': f'Error exporting vehicles: {str(e)}'}), 500

# Statistics endpoint for dashboard
@api.route('/api/statistics')
def get_statistics():
    """Get overall statistics for dashboard"""
    try:
        conn = get_db_connection()
        
        total_vehicles = conn.execute("SELECT COUNT(*) FROM vehicles").fetchone()[0]
        
        active_statuses = ['New', 'TOP Generated', 'TR52 Ready', 'TR208 Ready', 'Ready for Auction', 'Ready for Scrap']
        active_vehicles_query = f"SELECT COUNT(*) FROM vehicles WHERE status IN ({','.join(['?']*len(active_statuses))})"
        active_vehicles = conn.execute(active_vehicles_query, active_statuses).fetchone()[0]
        
        released_vehicles = conn.execute("SELECT COUNT(*) FROM vehicles WHERE status = 'Released'").fetchone()[0]
        
        # Average processing time for completed vehicles (Released, Auctioned, Scrapped)
        # Ensure tow_date and release_date are stored in a comparable format (e.g., YYYY-MM-DD or datetime)
        avg_processing_time_query = """
            SELECT AVG(JULIANDAY(date(release_date)) - JULIANDAY(date(tow_date))) 
            FROM vehicles 
            WHERE status IN ('Released', 'Auctioned', 'Scrapped', 'Transferred') AND release_date IS NOT NULL AND tow_date IS NOT NULL
        """
        avg_time_result = conn.execute(avg_processing_time_query).fetchone()[0]
        avg_processing_time = round(avg_time_result, 2) if avg_time_result is not None else "N/A"

        # Vehicles by jurisdiction
        jurisdiction_counts_cursor = conn.execute("SELECT jurisdiction, COUNT(*) FROM vehicles GROUP BY jurisdiction")
        jurisdiction_stats = {row[0] if row[0] else "Unknown": row[1] for row in jurisdiction_counts_cursor.fetchall()}

        conn.close()
        
        return jsonify({
            'totalVehicles': total_vehicles,
            'activeVehicles': active_vehicles,
            'releasedVehicles': released_vehicles,
            'averageProcessingTimeDays': avg_processing_time,
            'vehiclesByJurisdiction': jurisdiction_stats
        })
        
    except Exception as e:
        logging.error(f"Error getting statistics: {e}", exc_info=True)
        return jsonify({'error': f'Error getting statistics: {str(e)}'}), 500

# Scraper routes
# TODO: Implement a more robust way to manage and access scraper instances
# For example, using a global dictionary or a dedicated manager class
# that can store and retrieve scraper instances based on user sessions or task IDs.
scraper_instances = {} # Simplified: In-memory storage for scraper instances

@api.route('/api/start-scraping', methods=['POST'])
def start_scraping_route():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    start_date = data.get('start_date')
    end_date = data.get('end_date')
    test_mode = data.get('test_mode', False)  # Add test mode support

    if not all([username, password, start_date, end_date]):
        return jsonify({'error': 'Username, password, start date, and end date are required.'}), 400

    # Use a unique ID for the scraper instance, e.g., session ID or a generated UUID
    # For simplicity, using username as a key here, but this might not be suitable for concurrent use
    scraper_id = username 
    if scraper_id in scraper_instances and scraper_instances[scraper_id].is_running():
        return jsonify({'message': 'Scraping is already in progress for this user.'}), 400
        
    scraper = TowBookScraper(username, password, test_mode=test_mode)  # Pass test_mode to scraper
    scraper_instances[scraper_id] = scraper

    # Capture the current app instance before starting the background thread
    app = current_app._get_current_object()

    # Run scraper in background to immediately return control to client
    def run_scraper():
        # Use Flask application context for database operations
        with app.app_context():
            scraper.scrape_data(start_date, end_date)
    Thread(target=run_scraper, daemon=True).start()

    return jsonify({'message': 'Scraper started', 'scraper_id': scraper_id, 'status': 'started', 'test_mode': test_mode}), 202

# New route to fetch scraping progress
@api.route('/api/scraping-progress/<scraper_id>', methods=['GET'])
def scraping_progress_route(scraper_id):
    """Get current progress of an active scraper instance"""
    scraper = scraper_instances.get(scraper_id)
    if not scraper:
        return jsonify({'error': 'Scraper not found.'}), 404
    return jsonify(scraper.get_progress()), 200

@api.route('/api/pending-notifications')
def pending_notifications_route():
    try:
        notifications = get_pending_notifications() # This function is in database.py
        # Convert Row objects to dictionaries if they are not already
        notifications_list = [dict(n) for n in notifications]
        return jsonify(notifications_list)
    except Exception as e:
        logging.error(f"Error fetching pending notifications: {e}", exc_info=True)
        return jsonify({'error': f'Error fetching pending notifications: {str(e)}'}), 500

# Contacts API routes
@api.route('/api/contacts')
def get_contacts_api():
    """Get all jurisdiction contacts"""
    try:
        contacts = get_contacts()
        return jsonify(contacts)
    except Exception as e:
        logging.error(f"Error fetching contacts: {e}", exc_info=True)
        return jsonify({'error': f'Error fetching contacts: {str(e)}'}), 500

@api.route('/api/contacts/<int:contact_id>')
def get_contact_api(contact_id):
    """Get a specific contact by ID"""
    try:
        contact = get_contact_by_id(contact_id)
        if contact:
            return jsonify(contact)
        else:
            return jsonify({'error': 'Contact not found'}), 404
    except Exception as e:
        logging.error(f"Error fetching contact {contact_id}: {e}", exc_info=True)
        return jsonify({'error': f'Error fetching contact: {str(e)}'}), 500

@api.route('/api/contacts', methods=['POST'])
def add_contact_api():
    """Add a new jurisdiction contact"""
    try:
        data = request.json
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Validate required fields
        if not data.get('jurisdiction'):
            return jsonify({'error': 'Jurisdiction is required'}), 400
        
        contact_id = add_contact_explicit(data)
        return jsonify({'success': True, 'contact_id': contact_id, 'message': 'Contact added successfully'}), 201
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logging.error(f"Error adding contact: {e}", exc_info=True)
        return jsonify({'error': f'Error adding contact: {str(e)}'}), 500

@api.route('/api/contacts/<int:contact_id>', methods=['PUT'])
def update_contact_api(contact_id):
    """Update an existing jurisdiction contact"""
    try:
        data = request.json
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        success = update_contact_explicit(contact_id, data)
        if success:
            return jsonify({'success': True, 'message': 'Contact updated successfully'})
        else:
            return jsonify({'error': 'Failed to update contact'}), 500
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logging.error(f"Error updating contact {contact_id}: {e}", exc_info=True)
        return jsonify({'error': f'Error updating contact: {str(e)}'}), 500

@api.route('/api/contacts/<int:contact_id>', methods=['DELETE'])
def delete_contact_api(contact_id):
    """Delete a jurisdiction contact"""
    try:
        success = delete_contact_explicit(contact_id)
        if success:
            return jsonify({'success': True, 'message': 'Contact deleted successfully'})
        else:
            return jsonify({'error': 'Contact not found'}), 404
    except Exception as e:
        logging.error(f"Error deleting contact {contact_id}: {e}", exc_info=True)
        return jsonify({'error': f'Error deleting contact: {str(e)}'}), 500

@api.route('/api/jurisdictions')
def get_jurisdictions_api():
    """Get list of all Genesee County jurisdictions"""
    try:
        jurisdictions = get_jurisdiction_list()
        return jsonify(jurisdictions)
    except Exception as e:
        logging.error(f"Error fetching jurisdictions: {e}", exc_info=True)
        return jsonify({'error': f'Error fetching jurisdictions: {str(e)}'}), 500

# Register blueprint with the app
def register_api_routes(app):
    app.register_blueprint(api)
    
    # Add a diagnostic route
    @app.route('/api/diagnostic')
    def diagnostic():
        """Diagnostic route to check database connection and data access"""
        try:
            from database import DATABASE, get_database_path
            conn = get_db_connection()
            tables_cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [row[0] for row in tables_cursor.fetchall()]
            
            vehicles_count = conn.execute("SELECT COUNT(*) FROM vehicles").fetchone()[0]
            contacts_count = conn.execute("SELECT COUNT(*) FROM contacts").fetchone()[0] if 'contacts' in tables else 0
            notifications_count = conn.execute("SELECT COUNT(*) FROM notifications").fetchone()[0] if 'notifications' in tables else 0
            
            sample_vehicle = None
            if vehicles_count > 0:
                vehicle_cursor = conn.execute("SELECT * FROM vehicles LIMIT 1")
                sample_vehicle = dict(vehicle_cursor.fetchone())
                # Convert any non-serializable types
                for key, value in sample_vehicle.items():
                    if not isinstance(value, (str, int, float, bool, type(None))):
                        sample_vehicle[key] = str(value)
            
            conn.close()
            
            return jsonify({
                'status': 'success',
                'database_path': get_database_path(),
                'tables': tables,
                'counts': {
                    'vehicles': vehicles_count,
                    'contacts': contacts_count,
                    'notifications': notifications_count
                },
                'sample_vehicle': sample_vehicle
            })
        except Exception as e:
            logging.error(f"Diagnostic error: {e}", exc_info=True)
            return jsonify({
                'status': 'error',
                'message': str(e),
                'type': str(type(e))
            }), 500