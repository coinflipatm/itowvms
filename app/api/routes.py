"""
Enhanced API Routes
Organized and consolidated API endpoints for the iTow system
"""

from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from datetime import datetime, timedelta
import logging
from app.core.auth import api_login_required, role_required
from app.core.database import VehicleRepository, db_manager

# Create API blueprint
api_bp = Blueprint('api', __name__)
api_logger = logging.getLogger('api')

# Vehicle Management API
@api_bp.route('/vehicles')
@api_login_required
def get_vehicles():
    """Get vehicles with filtering and pagination"""
    
    try:
        # Get query parameters
        status = request.args.get('status')
        jurisdiction = request.args.get('jurisdiction')
        page = int(request.args.get('page', 1))
        per_page = min(int(request.args.get('per_page', 50)), 100)
        
        vehicle_repo = VehicleRepository(db_manager)
        
        # Build query based on filters
        where_conditions = []
        params = []
        
        if status:
            where_conditions.append("status = ?")
            params.append(status)
        
        if jurisdiction:
            where_conditions.append("jurisdiction = ?")
            params.append(jurisdiction)
        
        where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"
        
        # Get total count
        count_query = f"SELECT COUNT(*) FROM vehicles WHERE {where_clause}"
        total_count = db_manager.fetch_one(count_query, tuple(params))[0]
        
        # Get paginated results
        offset = (page - 1) * per_page
        vehicles_query = f"""
        SELECT * FROM vehicles 
        WHERE {where_clause}
        ORDER BY date_received DESC
        LIMIT ? OFFSET ?
        """
        params.extend([per_page, offset])
        
        vehicles = db_manager.fetch_all(vehicles_query, tuple(params))
        
        return jsonify({
            'success': True,
            'vehicles': [dict(vehicle) for vehicle in vehicles],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total_count,
                'pages': (total_count + per_page - 1) // per_page
            }
        })
        
    except Exception as e:
        api_logger.error(f"Failed to get vehicles: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@api_bp.route('/vehicles/<int:vehicle_id>')
@api_login_required
def get_vehicle_details(vehicle_id):
    """Get detailed vehicle information"""
    
    try:
        vehicle_repo = VehicleRepository(db_manager)
        vehicle = vehicle_repo.get_vehicle_by_id(vehicle_id)
        
        if not vehicle:
            return jsonify({'success': False, 'error': 'Vehicle not found'}), 404
        
        # Get vehicle lifecycle stages
        stages_query = """
        SELECT stage, entered_date, exited_date, duration_days, stage_notes
        FROM vehicle_lifecycle_stages 
        WHERE vehicle_id = ?
        ORDER BY entered_date ASC
        """
        stages = db_manager.fetch_all(stages_query, (vehicle_id,))
        
        # Get notification history
        notifications_query = """
        SELECT notification_type, recipient, sent_date, delivery_confirmed
        FROM notification_log
        WHERE vehicle_id = ?
        ORDER BY sent_date DESC
        """
        notifications = db_manager.fetch_all(notifications_query, (vehicle_id,))
        
        # Get audit trail
        audit_query = """
        SELECT action_type, action_details, user_id, timestamp, system_generated
        FROM vehicle_audit_trail
        WHERE vehicle_id = ?
        ORDER BY timestamp DESC
        LIMIT 20
        """
        audit_trail = db_manager.fetch_all(audit_query, (vehicle_id,))
        
        return jsonify({
            'success': True,
            'vehicle': vehicle,
            'lifecycle_stages': [dict(stage) for stage in stages],
            'notifications': [dict(notification) for notification in notifications],
            'audit_trail': [dict(audit) for audit in audit_trail]
        })
        
    except Exception as e:
        api_logger.error(f"Failed to get vehicle details {vehicle_id}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@api_bp.route('/vehicles/<int:vehicle_id>/status', methods=['PUT'])
@api_login_required
@role_required(['admin', 'editor'])
def update_vehicle_status(vehicle_id):
    """Update vehicle status with workflow validation"""
    
    try:
        data = request.get_json()
        new_status = data.get('status')
        notes = data.get('notes', '')
        
        if not new_status:
            return jsonify({'success': False, 'error': 'Status is required'}), 400
        
        vehicle_repo = VehicleRepository(db_manager)
        success = vehicle_repo.update_vehicle_status(vehicle_id, new_status, notes)
        
        if success:
            # Log the action
            from app.workflows.engine import VehicleWorkflowEngine
            workflow_engine = current_app.workflow_engine
            workflow_engine.workflow_logger.info(
                f"Vehicle {vehicle_id} status updated to {new_status} by {current_user.username}"
            )
            
            return jsonify({
                'success': True,
                'message': f'Vehicle status updated to {new_status}'
            })
        else:
            return jsonify({'success': False, 'error': 'Failed to update status'}), 500
            
    except Exception as e:
        api_logger.error(f"Failed to update vehicle status: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# Workflow API endpoints
@api_bp.route('/workflow/summary')
@api_login_required
def get_workflow_summary():
    """Get workflow summary statistics"""
    
    try:
        summary_query = """
        SELECT 
            status,
            COUNT(*) as count,
            AVG(JULIANDAY('now') - JULIANDAY(date_received)) as avg_days_held
        FROM vehicles 
        WHERE status NOT IN ('disposed', 'released', 'closed')
        GROUP BY status
        """
        
        status_summary = db_manager.fetch_all(summary_query)
        
        # Get vehicles needing immediate attention
        urgent_query = """
        SELECT COUNT(*) FROM vehicles 
        WHERE status = 'INITIAL_HOLD' 
        AND JULIANDAY('now') - JULIANDAY(date_received) >= 7
        AND seven_day_notice_sent IS NULL
        """
        urgent_count = db_manager.fetch_one(urgent_query)[0]
        
        # Get vehicles with pickups scheduled today
        today = datetime.now().strftime('%Y-%m-%d')
        pickups_today_query = """
        SELECT COUNT(*) FROM vehicle_disposition_tracking
        WHERE scheduled_pickup_date = ? AND pickup_confirmed_date IS NULL
        """
        pickups_today = db_manager.fetch_one(pickups_today_query, (today,))[0]
        
        return jsonify({
            'success': True,
            'summary': {
                'status_breakdown': [dict(row) for row in status_summary],
                'urgent_actions': urgent_count,
                'pickups_scheduled_today': pickups_today,
                'generated_at': datetime.now().isoformat()
            }
        })
        
    except Exception as e:
        api_logger.error(f"Failed to get workflow summary: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@api_bp.route('/workflow/actions')
@api_login_required
def get_workflow_actions():
    """Get pending workflow actions"""
    
    try:
        workflow_engine = current_app.workflow_engine
        priorities = workflow_engine.get_daily_priorities()
        
        return jsonify({
            'success': True,
            'actions': priorities
        })
        
    except Exception as e:
        api_logger.error(f"Failed to get workflow actions: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# TowBook Integration API
@api_bp.route('/towbook/sync', methods=['POST'])
@api_login_required
@role_required(['admin', 'editor'])
def sync_towbook():
    """Manually trigger TowBook synchronization"""
    
    try:
        # This would integrate with the TowBook scraper
        # For now, return a placeholder response
        
        return jsonify({
            'success': True,
            'message': 'TowBook sync initiated',
            'sync_id': f'sync_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
        })
        
    except Exception as e:
        api_logger.error(f"TowBook sync failed: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@api_bp.route('/towbook/status')
@api_login_required
def get_towbook_status():
    """Get TowBook integration status"""
    
    try:
        # Check last sync time and status
        last_sync_query = """
        SELECT MAX(timestamp) FROM vehicle_audit_trail 
        WHERE action_type = 'towbook_sync'
        """
        last_sync = db_manager.fetch_one(last_sync_query)[0]
        
        return jsonify({
            'success': True,
            'status': {
                'last_sync': last_sync,
                'sync_enabled': current_app.config.get('TOWBOOK_TEST_MODE', True),
                'next_scheduled_sync': 'Manual trigger only'  # For now
            }
        })
        
    except Exception as e:
        api_logger.error(f"Failed to get TowBook status: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@api_bp.route('/towbook/import', methods=['POST'])
@api_login_required
@role_required('admin')
def import_towbook_data():
    """Import vehicles from TowBook"""
    
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['username', 'password', 'start_date', 'end_date']
        for field in required_fields:
            if field not in data:
                return jsonify({'success': False, 'error': f'Missing required field: {field}'}), 400
        
        # Get TowBook integration instance
        towbook_integration = current_app.towbook_integration
        
        # Execute import
        result = towbook_integration.import_vehicles(
            username=data['username'],
            password=data['password'],
            start_date=data['start_date'],
            end_date=data['end_date'],
            test_mode=data.get('test_mode', False)
        )
        
        api_logger.info(f"TowBook import completed by {current_user.username}: {result}")
        
        return jsonify({
            'success': result.success,
            'data': {
                'vehicles_imported': result.vehicles_imported,
                'vehicles_updated': result.vehicles_updated,
                'vehicles_skipped': result.vehicles_skipped,
                'duration_seconds': result.duration_seconds,
                'error_message': result.error_message
            }
        })
        
    except Exception as e:
        api_logger.error(f"TowBook import failed: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@api_bp.route('/towbook/validate-credentials', methods=['POST'])
@api_login_required
@role_required('admin')
def validate_towbook_credentials():
    """Validate TowBook credentials without importing"""
    
    try:
        data = request.get_json()
        
        if 'username' not in data or 'password' not in data:
            return jsonify({'success': False, 'error': 'Username and password required'}), 400
        
        towbook_integration = current_app.towbook_integration
        
        valid, message = towbook_integration.validate_credentials(
            username=data['username'],
            password=data['password']
        )
        
        return jsonify({
            'success': True,
            'data': {
                'credentials_valid': valid,
                'message': message
            }
        })
        
    except Exception as e:
        api_logger.error(f"Credential validation failed: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@api_bp.route('/towbook/date-range')
@api_login_required
def get_towbook_date_range():
    """Get recommended date range for TowBook import"""
    
    try:
        towbook_integration = current_app.towbook_integration
        date_range = towbook_integration.get_available_date_range()
        
        return jsonify({
            'success': True,
            'data': date_range
        })
        
    except Exception as e:
        api_logger.error(f"Failed to get date range: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@api_bp.route('/towbook/import-progress')
@api_login_required
def get_towbook_import_progress():
    """Get current TowBook import progress"""
    
    try:
        towbook_integration = current_app.towbook_integration
        progress = towbook_integration.get_import_progress()
        
        return jsonify({
            'success': True,
            'data': progress
        })
        
    except Exception as e:
        api_logger.error(f"Failed to get import progress: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# Reporting API
@api_bp.route('/reports/daily')
@api_login_required
def get_daily_report():
    """Generate daily operations report"""
    
    try:
        today = datetime.now().strftime('%Y-%m-%d')
        
        # Vehicles received today
        received_today_query = """
        SELECT COUNT(*) FROM vehicles 
        WHERE DATE(date_received) = ?
        """
        received_today = db_manager.fetch_one(received_today_query, (today,))[0]
        
        # Vehicles disposed today
        disposed_today_query = """
        SELECT COUNT(*) FROM vehicle_disposition_tracking
        WHERE DATE(physical_removal_date) = ?
        """
        disposed_today = db_manager.fetch_one(disposed_today_query, (today,))[0]
        
        # Notices sent today
        notices_today_query = """
        SELECT COUNT(*) FROM notification_log
        WHERE DATE(sent_date) = ? AND notification_type = '7_day_notice'
        """
        notices_today = db_manager.fetch_one(notices_today_query, (today,))[0]
        
        # Current inventory by status
        inventory_query = """
        SELECT status, COUNT(*) as count
        FROM vehicles 
        WHERE status NOT IN ('disposed', 'released', 'closed')
        GROUP BY status
        """
        inventory = db_manager.fetch_all(inventory_query)
        
        return jsonify({
            'success': True,
            'report': {
                'date': today,
                'vehicles_received': received_today,
                'vehicles_disposed': disposed_today,
                'notices_sent': notices_today,
                'current_inventory': [dict(row) for row in inventory],
                'generated_at': datetime.now().isoformat()
            }
        })
        
    except Exception as e:
        api_logger.error(f"Failed to generate daily report: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# System Health API
@api_bp.route('/system/health')
@api_login_required
def get_system_health():
    """Get system health status"""
    
    try:
        # Database connectivity check
        db_health = True
        try:
            db_manager.fetch_one("SELECT 1")
        except:
            db_health = False
        
        # Check for recent errors
        error_query = """
        SELECT COUNT(*) FROM vehicle_audit_trail
        WHERE action_type = 'error' 
        AND timestamp > datetime('now', '-1 hour')
        """
        recent_errors = db_manager.fetch_one(error_query)[0]
        
        # Check workflow engine status
        workflow_status = hasattr(current_app, 'workflow_engine') and current_app.workflow_engine is not None
        
        return jsonify({
            'success': True,
            'health': {
                'database': db_health,
                'workflow_engine': workflow_status,
                'recent_errors': recent_errors,
                'timestamp': datetime.now().isoformat(),
                'status': 'healthy' if db_health and workflow_status and recent_errors == 0 else 'degraded'
            }
        })
        
    except Exception as e:
        api_logger.error(f"Failed to get system health: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# Error handler for API routes
@api_bp.errorhandler(404)
def api_not_found(error):
    return jsonify({'success': False, 'error': 'Endpoint not found'}), 404

@api_bp.errorhandler(500)
def api_server_error(error):
    return jsonify({'success': False, 'error': 'Internal server error'}), 500
