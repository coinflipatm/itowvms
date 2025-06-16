"""
Main Application Routes
Core routes for the web interface (legacy compatibility + new features)
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from app.core.auth import role_required
from app.core.database import VehicleRepository, db_manager
import logging

main_bp = Blueprint('main', __name__)
main_logger = logging.getLogger('main')

@main_bp.route('/')
@login_required
def index():
    """Main application dashboard"""
    
    # Check if user has access to new dashboard
    if current_user.can_access_dashboard():
        return redirect(url_for('dashboard.daily_operations'))
    else:
        # Fall back to legacy interface
        return render_template('index.html')

@main_bp.route('/legacy')
@login_required
def legacy_interface():
    """Legacy interface for backward compatibility"""
    
    return render_template('index.html')

@main_bp.route('/vehicles')
@login_required
def vehicles_list():
    """Vehicle list view"""
    
    try:
        # Get filter parameters
        status_filter = request.args.get('status', 'all')
        jurisdiction_filter = request.args.get('jurisdiction', 'all')
        
        vehicle_repo = VehicleRepository(db_manager)
        
        # Build query based on filters
        if status_filter == 'all':
            vehicles = vehicle_repo.get_all_vehicles()
        else:
            vehicles = vehicle_repo.get_vehicles_by_status(status_filter)
        
        # Apply jurisdiction filter if specified
        if jurisdiction_filter != 'all':
            vehicles = [v for v in vehicles if v.get('jurisdiction') == jurisdiction_filter]
        
        return render_template('vehicles/list.html', 
                             vehicles=vehicles,
                             current_status=status_filter,
                             current_jurisdiction=jurisdiction_filter)
        
    except Exception as e:
        main_logger.error(f"Failed to load vehicles list: {e}")
        flash('Error loading vehicles list', 'error')
        return redirect(url_for('main.index'))

@main_bp.route('/vehicles/<int:vehicle_id>')
@login_required
def vehicle_details(vehicle_id):
    """Vehicle details view"""
    
    try:
        vehicle_repo = VehicleRepository(db_manager)
        vehicle = vehicle_repo.get_vehicle_by_id(vehicle_id)
        
        if not vehicle:
            flash('Vehicle not found', 'error')
            return redirect(url_for('main.vehicles_list'))
        
        return render_template('vehicles/details.html', vehicle=vehicle)
        
    except Exception as e:
        main_logger.error(f"Failed to load vehicle details {vehicle_id}: {e}")
        flash('Error loading vehicle details', 'error')
        return redirect(url_for('main.vehicles_list'))

@main_bp.route('/reports')
@login_required
@role_required(['admin', 'editor'])
def reports():
    """Reports dashboard"""
    
    return render_template('reports/dashboard.html')

@main_bp.route('/settings')
@login_required
@role_required(['admin'])
def settings():
    """System settings"""
    
    return render_template('settings/index.html')

# Error handlers
@main_bp.errorhandler(403)
def forbidden(error):
    flash('You do not have permission to access this page.', 'error')
    return redirect(url_for('main.index'))

@main_bp.errorhandler(404)
def page_not_found(error):
    return render_template('errors/404.html'), 404

@main_bp.errorhandler(500)
def internal_server_error(error):
    return render_template('errors/500.html'), 500
