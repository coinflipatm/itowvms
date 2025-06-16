"""
Analytics routes for iTow VMS
Provides web endpoints for advanced analytics and business intelligence
"""
from flask import Blueprint, render_template, jsonify, request, current_app, send_file
from flask_login import login_required
import json
from datetime import datetime
import logging

# Create analytics blueprint
analytics_bp = Blueprint('analytics', __name__, url_prefix='/analytics')
logger = logging.getLogger(__name__)

@analytics_bp.route('/dashboard')
@login_required
def analytics_dashboard():
    """Main analytics dashboard page"""
    try:
        timeframe = request.args.get('timeframe', '30d')
        return render_template('analytics/dashboard.html', timeframe=timeframe)
    except Exception as e:
        logger.error(f"Error loading analytics dashboard: {e}")
        return render_template('error.html', message="Unable to load analytics dashboard"), 500

@analytics_bp.route('/api/executive-dashboard')
@login_required
def api_executive_dashboard():
    """API endpoint for executive dashboard data"""
    try:
        timeframe = request.args.get('timeframe', '30d')
        
        dashboard_manager = getattr(current_app, 'dashboard_manager', None)
        if not dashboard_manager:
            return jsonify({'error': 'Dashboard manager not available'}), 500
        
        dashboard_data = dashboard_manager.get_executive_dashboard_data(timeframe)
        return jsonify(dashboard_data)
        
    except Exception as e:
        logger.error(f"Error getting executive dashboard data: {e}")
        return jsonify({'error': str(e)}), 500

@analytics_bp.route('/api/operational-dashboard')
@login_required  
def api_operational_dashboard():
    """API endpoint for operational dashboard data"""
    try:
        timeframe = request.args.get('timeframe', '7d')
        
        dashboard_manager = getattr(current_app, 'dashboard_manager', None)
        if not dashboard_manager:
            return jsonify({'error': 'Dashboard manager not available'}), 500
        
        dashboard_data = dashboard_manager.get_operational_dashboard_data(timeframe)
        return jsonify(dashboard_data)
        
    except Exception as e:
        logger.error(f"Error getting operational dashboard data: {e}")
        return jsonify({'error': str(e)}), 500

@analytics_bp.route('/api/real-time-kpis')
@login_required
def api_real_time_kpis():
    """API endpoint for real-time KPIs"""
    try:
        analytics_engine = getattr(current_app, 'analytics_engine', None)
        if not analytics_engine:
            return jsonify({'error': 'Analytics engine not available'}), 500
        
        kpis = analytics_engine.get_real_time_kpis()
        return jsonify(kpis)
        
    except Exception as e:
        logger.error(f"Error getting real-time KPIs: {e}")
        return jsonify({'error': str(e)}), 500

@analytics_bp.route('/api/vehicle-metrics')
@login_required
def api_vehicle_metrics():
    """API endpoint for vehicle metrics"""
    try:
        timeframe = request.args.get('timeframe', '30d')
        
        analytics_engine = getattr(current_app, 'analytics_engine', None)
        if not analytics_engine:
            return jsonify({'error': 'Analytics engine not available'}), 500
        
        metrics = analytics_engine.get_vehicle_metrics(timeframe)
        
        # Convert dataclass to dict for JSON serialization
        metrics_dict = {
            'total_vehicles': metrics.total_vehicles,
            'active_vehicles': metrics.active_vehicles,
            'completed_vehicles': metrics.completed_vehicles,
            'urgent_vehicles': metrics.urgent_vehicles,
            'average_processing_time': metrics.average_processing_time,
            'total_revenue': metrics.total_revenue,
            'processing_efficiency': metrics.processing_efficiency
        }
        
        return jsonify(metrics_dict)
        
    except Exception as e:
        logger.error(f"Error getting vehicle metrics: {e}")
        return jsonify({'error': str(e)}), 500

@analytics_bp.route('/api/operational-metrics')
@login_required
def api_operational_metrics():
    """API endpoint for operational metrics"""
    try:
        timeframe = request.args.get('timeframe', '30d')
        
        analytics_engine = getattr(current_app, 'analytics_engine', None)
        if not analytics_engine:
            return jsonify({'error': 'Analytics engine not available'}), 500
        
        metrics = analytics_engine.get_operational_metrics(timeframe)
        
        # Convert dataclass to dict for JSON serialization
        metrics_dict = {
            'workflow_completion_rate': metrics.workflow_completion_rate,
            'average_stage_duration': metrics.average_stage_duration,
            'bottleneck_stages': metrics.bottleneck_stages,
            'resource_utilization': metrics.resource_utilization,
            'automation_success_rate': metrics.automation_success_rate
        }
        
        return jsonify(metrics_dict)
        
    except Exception as e:
        logger.error(f"Error getting operational metrics: {e}")
        return jsonify({'error': str(e)}), 500

@analytics_bp.route('/api/financial-metrics')
@login_required
def api_financial_metrics():
    """API endpoint for financial metrics"""
    try:
        timeframe = request.args.get('timeframe', '30d')
        
        analytics_engine = getattr(current_app, 'analytics_engine', None)
        if not analytics_engine:
            return jsonify({'error': 'Analytics engine not available'}), 500
        
        metrics = analytics_engine.get_financial_metrics(timeframe)
        
        # Convert dataclass to dict for JSON serialization
        metrics_dict = {
            'total_revenue': metrics.total_revenue,
            'total_costs': metrics.total_costs,
            'average_vehicle_value': metrics.average_vehicle_value,
            'profit_margin': metrics.profit_margin,
            'cost_per_vehicle': metrics.cost_per_vehicle,
            'revenue_trend': [(t.isoformat(), v) for t, v in (metrics.revenue_trend or [])]
        }
        
        return jsonify(metrics_dict)
        
    except Exception as e:
        logger.error(f"Error getting financial metrics: {e}")
        return jsonify({'error': str(e)}), 500

@analytics_bp.route('/api/trend-analysis/<metric>')
@login_required
def api_trend_analysis(metric):
    """API endpoint for trend analysis"""
    try:
        timeframe = request.args.get('timeframe', '30d')
        
        analytics_engine = getattr(current_app, 'analytics_engine', None)
        if not analytics_engine:
            return jsonify({'error': 'Analytics engine not available'}), 500
        
        trend_data = analytics_engine.get_trend_analysis(metric, timeframe)
        return jsonify(trend_data)
        
    except Exception as e:
        logger.error(f"Error getting trend analysis for {metric}: {e}")
        return jsonify({'error': str(e)}), 500

@analytics_bp.route('/api/analytics-summary')
@login_required
def api_analytics_summary():
    """API endpoint for comprehensive analytics summary"""
    try:
        timeframe = request.args.get('timeframe', '30d')
        
        analytics_engine = getattr(current_app, 'analytics_engine', None)
        if not analytics_engine:
            return jsonify({'error': 'Analytics engine not available'}), 500
        
        summary = analytics_engine.generate_analytics_summary(timeframe)
        return jsonify(summary)
        
    except Exception as e:
        logger.error(f"Error getting analytics summary: {e}")
        return jsonify({'error': str(e)}), 500

@analytics_bp.route('/reports')
@login_required
def reports_dashboard():
    """Reports dashboard page"""
    try:
        return render_template('analytics/reports.html')
    except Exception as e:
        logger.error(f"Error loading reports dashboard: {e}")
        return render_template('error.html', message="Unable to load reports dashboard"), 500

@analytics_bp.route('/api/reports/executive-summary')
@login_required
def api_executive_summary_report():
    """API endpoint for executive summary report"""
    try:
        timeframe = request.args.get('timeframe', '30d')
        format = request.args.get('format', 'json')
        
        report_generator = getattr(current_app, 'report_generator', None)
        if not report_generator:
            return jsonify({'error': 'Report generator not available'}), 500
        
        report = report_generator.generate_executive_summary_report(timeframe, format)
        
        if format == 'json':
            return jsonify(report)
        else:
            # For non-JSON formats, return as text
            return report, 200, {'Content-Type': 'text/plain'}
        
    except Exception as e:
        logger.error(f"Error generating executive summary report: {e}")
        return jsonify({'error': str(e)}), 500

@analytics_bp.route('/api/reports/operational')
@login_required
def api_operational_report():
    """API endpoint for operational report"""
    try:
        timeframe = request.args.get('timeframe', '7d')
        format = request.args.get('format', 'json')
        
        report_generator = getattr(current_app, 'report_generator', None)
        if not report_generator:
            return jsonify({'error': 'Report generator not available'}), 500
        
        report = report_generator.generate_operational_report(timeframe, format)
        
        if format == 'json':
            return jsonify(report)
        else:
            return report, 200, {'Content-Type': 'text/plain'}
        
    except Exception as e:
        logger.error(f"Error generating operational report: {e}")
        return jsonify({'error': str(e)}), 500

@analytics_bp.route('/api/reports/financial')
@login_required
def api_financial_report():
    """API endpoint for financial report"""
    try:
        timeframe = request.args.get('timeframe', '30d')
        format = request.args.get('format', 'json')
        
        report_generator = getattr(current_app, 'report_generator', None)
        if not report_generator:
            return jsonify({'error': 'Report generator not available'}), 500
        
        report = report_generator.generate_financial_report(timeframe, format)
        
        if format == 'json':
            return jsonify(report)
        else:
            return report, 200, {'Content-Type': 'text/plain'}
        
    except Exception as e:
        logger.error(f"Error generating financial report: {e}")
        return jsonify({'error': str(e)}), 500

@analytics_bp.route('/api/reports/compliance')
@login_required
def api_compliance_report():
    """API endpoint for compliance report"""
    try:
        timeframe = request.args.get('timeframe', '30d')
        format = request.args.get('format', 'json')
        
        report_generator = getattr(current_app, 'report_generator', None)
        if not report_generator:
            return jsonify({'error': 'Report generator not available'}), 500
        
        report = report_generator.generate_compliance_report(timeframe, format)
        
        if format == 'json':
            return jsonify(report)
        else:
            return report, 200, {'Content-Type': 'text/plain'}
        
    except Exception as e:
        logger.error(f"Error generating compliance report: {e}")
        return jsonify({'error': str(e)}), 500

@analytics_bp.route('/api/reports/custom', methods=['POST'])
@login_required
def api_custom_report():
    """API endpoint for custom reports"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        metrics = data.get('metrics', [])
        timeframe = data.get('timeframe', '30d')
        filters = data.get('filters', {})
        format = data.get('format', 'json')
        
        report_generator = getattr(current_app, 'report_generator', None)
        if not report_generator:
            return jsonify({'error': 'Report generator not available'}), 500
        
        report = report_generator.generate_custom_report(metrics, timeframe, filters, format)
        
        if format == 'json':
            return jsonify(report)
        else:
            return report, 200, {'Content-Type': 'text/plain'}
        
    except Exception as e:
        logger.error(f"Error generating custom report: {e}")
        return jsonify({'error': str(e)}), 500

@analytics_bp.route('/api/reports/save', methods=['POST'])
@login_required
def api_save_report():
    """API endpoint to save reports to file"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        report_data = data.get('report_data')
        filename = data.get('filename', 'report')
        format = data.get('format', 'json')
        
        report_generator = getattr(current_app, 'report_generator', None)
        if not report_generator:
            return jsonify({'error': 'Report generator not available'}), 500
        
        file_path = report_generator.save_report_to_file(report_data, filename, format)
        
        return jsonify({
            'success': True,
            'file_path': file_path,
            'message': f'Report saved as {file_path}'
        })
        
    except Exception as e:
        logger.error(f"Error saving report: {e}")
        return jsonify({'error': str(e)}), 500

@analytics_bp.route('/operational')
@login_required
def operational_dashboard():
    """Operational analytics dashboard page"""
    try:
        timeframe = request.args.get('timeframe', '7d')
        return render_template('analytics/operational.html', timeframe=timeframe)
    except Exception as e:
        logger.error(f"Error loading operational dashboard: {e}")
        return render_template('error.html', message="Unable to load operational dashboard"), 500

@analytics_bp.route('/financial')
@login_required
def financial_dashboard():
    """Financial analytics dashboard page"""
    try:
        timeframe = request.args.get('timeframe', '30d')
        return render_template('analytics/financial.html', timeframe=timeframe)
    except Exception as e:
        logger.error(f"Error loading financial dashboard: {e}")
        return render_template('error.html', message="Unable to load financial dashboard"), 500

# Error handlers for analytics blueprint
@analytics_bp.errorhandler(404)
def analytics_not_found(error):
    return render_template('error.html', message="Analytics page not found"), 404

@analytics_bp.errorhandler(500)
def analytics_server_error(error):
    return render_template('error.html', message="Analytics server error"), 500
