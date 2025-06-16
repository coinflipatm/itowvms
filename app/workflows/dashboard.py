"""
Daily Operations Dashboard
Centralized morning workflow management system
"""

from flask import Blueprint, render_template, request, jsonify, current_app
from flask_login import login_required
from datetime import datetime, timedelta
import logging
from app.workflows.engine import VehicleWorkflowEngine

dashboard_bp = Blueprint('dashboard', __name__)
dashboard_logger = logging.getLogger('dashboard')

@dashboard_bp.route('/')
@login_required
def daily_operations():
    """
    Main daily operations dashboard
    Replaces scattered status checking with focused workflow
    """
    return render_template('dashboard/daily_operations.html')

@dashboard_bp.route('/api/morning-priorities')
@login_required
def get_morning_priorities():
    """
    API endpoint for morning priority data
    What you check first thing each morning
    """
    
    try:
        workflow_engine = current_app.workflow_engine
        priorities = workflow_engine.get_daily_priorities()
        
        # Add summary statistics
        summary = {
            'total_urgent': len(priorities['urgent']),
            'total_today': len(priorities['today']),
            'total_upcoming': len(priorities['upcoming']),
            'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        return jsonify({
            'success': True,
            'priorities': priorities,
            'summary': summary
        })
        
    except Exception as e:
        dashboard_logger.error(f"Failed to get morning priorities: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@dashboard_bp.route('/api/vehicle-pipeline')
@login_required  
def get_vehicle_pipeline():
    """
    Get vehicle pipeline status for visual display
    """
    
    try:
        workflow_engine = current_app.workflow_engine
        
        # Get counts for each stage
        pipeline_data = {
            'initial_hold': 0,
            'pending_notification': 0,
            'notice_sent': 0,
            'approved_auction': 0,
            'approved_scrap': 0,
            'scheduled_pickup': 0,
            'disposed_today': 0
        }
        
        # This would query the database for actual counts
        # For now, returning structure
        
        return jsonify({
            'success': True,
            'pipeline': pipeline_data
        })
        
    except Exception as e:
        dashboard_logger.error(f"Failed to get vehicle pipeline: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@dashboard_bp.route('/api/process-automated-actions', methods=['POST'])
@login_required
def process_automated_actions():
    """
    Process automated workflow actions (7-day notices, etc.)
    """
    
    try:
        workflow_engine = current_app.workflow_engine
        
        # Process 7-day notices
        notice_results = workflow_engine.process_automated_seven_day_notices()
        
        # Could add other automated processes here
        
        return jsonify({
            'success': True,
            'results': {
                'seven_day_notices': notice_results,
                'processed_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
        })
        
    except Exception as e:
        dashboard_logger.error(f"Failed to process automated actions: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@dashboard_bp.route('/api/advance-vehicle-stage', methods=['POST'])
@login_required
def advance_vehicle_stage():
    """
    Manually advance a vehicle to the next workflow stage
    """
    
    try:
        data = request.get_json()
        vehicle_id = data.get('vehicle_id')
        new_stage = data.get('new_stage')
        notes = data.get('notes', '')
        
        if not vehicle_id or not new_stage:
            return jsonify({
                'success': False,
                'error': 'vehicle_id and new_stage are required'
            }), 400
        
        workflow_engine = current_app.workflow_engine
        from app.workflows.engine import VehicleStage
        
        # Convert string to enum
        try:
            stage_enum = VehicleStage(new_stage)
        except ValueError:
            return jsonify({
                'success': False,
                'error': f'Invalid stage: {new_stage}'
            }), 400
        
        success = workflow_engine.advance_stage(
            vehicle_id, stage_enum, notes, user_id='current_user'
        )
        
        if success:
            return jsonify({
                'success': True,
                'message': f'Vehicle {vehicle_id} advanced to {new_stage}'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to advance vehicle stage'
            }), 500
            
    except Exception as e:
        dashboard_logger.error(f"Failed to advance vehicle stage: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@dashboard_bp.route('/towbook')
@login_required
def towbook_management():
    """TowBook import management dashboard"""
    return render_template('dashboard/towbook_management.html')

@dashboard_bp.route('/api/towbook-status')
@login_required
def get_towbook_status():
    """
    Get TowBook integration status and statistics
    """
    
    try:
        towbook_integration = current_app.towbook_integration
        
        # Get recommended date range
        date_range = towbook_integration.get_available_date_range()
        
        # Get import progress
        progress = towbook_integration.get_import_progress()
        
        # Get recent import statistics from database
        from app.core.database import VehicleRepository, db_manager
        vehicle_repo = VehicleRepository(db_manager)
        
        # Count vehicles imported today
        today = datetime.now().strftime('%Y-%m-%d')
        today_vehicles = vehicle_repo.get_vehicles_updated_since(f"{today} 00:00:00")
        
        # Count new vehicles needing attention
        new_vehicles = vehicle_repo.get_vehicles_by_status('New')
        
        return jsonify({
            'success': True,
            'data': {
                'recommended_date_range': date_range,
                'import_progress': progress,
                'today_imported': len(today_vehicles),
                'new_vehicles_pending': len(new_vehicles),
                'last_check': datetime.now().isoformat()
            }
        })
        
    except Exception as e:
        dashboard_logger.error(f"Failed to get TowBook status: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@dashboard_bp.route('/api/towbook-import-summary')
@login_required
def get_towbook_import_summary():
    """
    Get summary of recent TowBook imports and their workflow impact
    """
    
    try:
        from app.core.database import VehicleRepository, db_manager
        vehicle_repo = VehicleRepository(db_manager)
        
        # Get vehicles imported in last 7 days
        week_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d %H:%M:%S')
        recent_vehicles = vehicle_repo.get_vehicles_updated_since(week_ago)
        
        # Analyze workflow impact
        workflow_engine = current_app.workflow_engine
        priorities = workflow_engine.get_daily_priorities()
        
        # Calculate statistics
        import_summary = {
            'vehicles_imported_7_days': len(recent_vehicles),
            'vehicles_needing_urgent_attention': len(priorities['urgent']),
            'vehicles_due_today': len(priorities['today']),
            'workflow_efficiency': {
                'automated_actions_available': sum(1 for v in priorities['urgent'] if v.get('actions')),
                'manual_review_required': sum(1 for v in priorities['urgent'] if not v.get('actions'))
            },
            'last_updated': datetime.now().isoformat()
        }
        
        return jsonify({
            'success': True,
            'data': import_summary
        })
        
    except Exception as e:
        dashboard_logger.error(f"Failed to get import summary: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
