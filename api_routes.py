"""
API routes for enhanced features in iTow Impound Manager
"""
import csv
import io
import json
import math
from datetime import datetime, timedelta
from collections import defaultdict
from flask import Blueprint, request, jsonify, send_file
from database import get_db_connection, get_vehicles, get_logs
from utils import log_action, convert_frontend_status

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
        return jsonify({'error': str(e)}), 500

# Reporting routes
@api.route('/api/reports')
def get_reports():
    """Get report data for dashboard"""
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        report_type = request.args.get('type', 'summary')
        
        # Validate dates
        if not start_date or not end_date:
            return jsonify({'error': 'Start and end dates are required'}), 400
            
        # Get data from database
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Status distribution
        cursor.execute("""
            SELECT status, COUNT(*) as count
            FROM vehicles
            WHERE (tow_date BETWEEN ? AND ?) OR release_date BETWEEN ? AND ?
            GROUP BY status
        """, (start_date, end_date, start_date, end_date))
        status_data = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Revenue data
        # In real implementation, you'd query from a revenue table
        # This is modified to get actual data from the database
        cursor.execute("""
            SELECT 
                strftime('%m', release_date) as month,
                COUNT(*) as count
            FROM vehicles
            WHERE release_date BETWEEN ? AND ?
            GROUP BY month
            ORDER BY month
        """, (start_date, end_date))
        
        months = []
        counts = []
        for row in cursor.fetchall():
            # Convert month number to name
            month_name = datetime.strptime(row[0], '%m').strftime('%b')
            months.append(month_name)
            counts.append(row[1])
            
        revenue_data = {
            'labels': months if months else ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
            'values': counts if counts else [0, 0, 0, 0, 0, 0]
        }
        
        # Processing time by status
        cursor.execute("""
            SELECT status,
                   AVG(JULIANDAY(COALESCE(release_date, DATE('now'))) - JULIANDAY(tow_date)) as avg_days
            FROM vehicles
            WHERE (tow_date BETWEEN ? AND ?) OR release_date BETWEEN ? AND ?
            GROUP BY status
        """, (start_date, end_date, start_date, end_date))
        processing_time = {
            'labels': [],
            'values': []
        }
        for row in cursor.fetchall():
            processing_time['labels'].append(row[0])
            processing_time['values'].append(round(row[1], 1) if row[1] else 0)
        
        # Jurisdiction distribution
        cursor.execute("""
            SELECT jurisdiction, COUNT(*) as count
            FROM vehicles
            WHERE (tow_date BETWEEN ? AND ?) OR release_date BETWEEN ? AND ?
            GROUP BY jurisdiction
        """, (start_date, end_date, start_date, end_date))
        jurisdiction_data = {row[0] if row[0] else 'Unknown': row[1] for row in cursor.fetchall()}
        
        # Metrics
        cursor.execute("""
            SELECT 
                COUNT(*) as total_vehicles,
                AVG(JULIANDAY(COALESCE(release_date, DATE('now'))) - JULIANDAY(tow_date)) as avg_processing_time,
                SUM(CASE WHEN status IN ('Released', 'Auctioned', 'Scrapped') THEN 1 ELSE 0 END) * 100.0 / 
                    CASE WHEN COUNT(*) > 0 THEN COUNT(*) ELSE 1 END as completion_rate
            FROM vehicles
            WHERE (tow_date BETWEEN ? AND ?) OR release_date BETWEEN ? AND ?
        """, (start_date, end_date, start_date, end_date))
        metrics_row = cursor.fetchone()
        
        # Calculate total revenue (mock data - replace with actual calculation)
        cursor.execute("""
            SELECT COUNT(*) FROM vehicles 
            WHERE status IN ('Released', 'Auctioned', 'Scrapped')
            AND (tow_date BETWEEN ? AND ?) OR release_date BETWEEN ? AND ?
        """, (start_date, end_date, start_date, end_date))
        completed_count = cursor.fetchone()[0]
        # Assume average revenue of $150 per vehicle
        total_revenue = completed_count * 150
        
        metrics = {
            'totalVehicles': metrics_row[0],
            'avgProcessingTime': f"{round(metrics_row[1], 1) if metrics_row[1] else 0} days",
            'totalRevenue': f"${total_revenue:,}",
            'completionRate': f"{round(metrics_row[2], 1) if metrics_row[2] else 0}%"
        }
        
        conn.close()
        
        return jsonify({
            'status': status_data,
            'revenue': revenue_data,
            'processingTime': processing_time,
            'jurisdiction': jurisdiction_data,
            'metrics': metrics
        })
    except Exception as e:
        print(f"Error getting report data: {e}")
        return jsonify({'error': str(e)}), 500

# Enhanced vehicle search endpoint
@api.route('/api/vehicles/search')
def search_vehicles():
    """Search vehicles across multiple fields"""
    try:
        query = request.args.get('q', '').strip()
        if not query or len(query) < 2:
            return jsonify([])
            
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Search across multiple fields with LIKE queries
        search_term = f"%{query}%"
        cursor.execute("""
            SELECT * FROM vehicles
            WHERE towbook_call_number LIKE ? 
            OR complaint_number LIKE ?
            OR vin LIKE ?
            OR make LIKE ?
            OR model LIKE ?
            OR plate LIKE ?
            LIMIT 50
        """, (search_term, search_term, search_term, search_term, search_term, search_term))
        
        vehicles = cursor.fetchall()
        conn.close()
        
        # Convert to list of dicts
        return jsonify([dict(v) for v in vehicles])
        
    except Exception as e:
        print(f"Error searching vehicles: {e}")
        return jsonify({'error': str(e)}), 500

# Export routes with improved error handling
@api.route('/api/vehicles/export/<format>')
def export_vehicles(format):
    """Export vehicle data"""
    try:
        tab = request.args.get('tab', 'active')
        sort_column = request.args.get('sort')
        sort_direction = request.args.get('direction', 'asc')
        
        # Get vehicles data
        vehicles = get_vehicles(tab, sort_column, sort_direction)
        
        if format == 'csv':
            # Create CSV
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Get column names from first row
            if vehicles:
                columns = vehicles[0].keys()
                writer.writerow(columns)
                
                # Write data rows
                for vehicle in vehicles:
                    writer.writerow(vehicle.values())
            
            # Create response
            output.seek(0)
            filename = f"vehicles_{tab}_{datetime.now().strftime('%Y%m%d%H%M%S')}.csv"
            
            return send_file(
                io.BytesIO(output.getvalue().encode('utf-8')),
                as_attachment=True,
                download_name=filename,  # Updated parameter name
                mimetype='text/csv'
            )
        elif format == 'json':
            # Export as JSON
            vehicle_list = [dict(v) for v in vehicles]
            output = json.dumps(vehicle_list, indent=2, default=str)
            filename = f"vehicles_{tab}_{datetime.now().strftime('%Y%m%d%H%M%S')}.json"
            
            return send_file(
                io.BytesIO(output.encode('utf-8')),
                as_attachment=True,
                download_name=filename,  # Updated parameter name
                mimetype='application/json'
            )
        elif format == 'pdf':
            # For PDF, we'd need a PDF generation library
            # This is a placeholder - in real implementation you'd use reportlab or similar
            return jsonify({'error': 'PDF export not implemented yet'}), 501
        else:
            return jsonify({'error': 'Invalid export format'}), 400
    except Exception as e:
        print(f"Error exporting vehicles: {e}")
        return jsonify({'error': str(e)}), 500

# Statistics endpoint for dashboard
@api.route('/api/statistics')
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
        print(f"Error getting statistics: {e}")
        return jsonify({'error': str(e)}), 500

# Register blueprint with the app
def register_api_routes(app):
    app.register_blueprint(api)