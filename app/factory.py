"""
Application Factory
Enhanced Flask application factory with proper configuration management
"""

import os
import logging
from flask import Flask
from config import get_config

def create_app(config_name=None):
    """
    Application factory with proper environment configuration
    Replaces the scattered configuration in old app.py
    """
    
    # Get the base directory (one level up from app package)
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    template_dir = os.path.join(base_dir, 'templates')
    static_dir = os.path.join(base_dir, 'static')
    
    app = Flask(__name__, 
                template_folder=template_dir,
                static_folder=static_dir)
    
    # Load configuration
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')
    
    config_class = get_config()
    app.config.from_object(config_class)
    
    # Ensure required directories exist
    os.makedirs('logs', exist_ok=True)
    os.makedirs('static/generated_pdfs', exist_ok=True)
    
    # Initialize logging
    setup_logging(app)
    
    # Initialize database
    from app.core.database import init_db
    init_db(app)
    
    # Initialize authentication
    from app.core.auth import init_auth
    init_auth(app)
    
    # Initialize notification system
    from app.core.notifications import init_notifications
    init_notifications(app)
    
    # Register blueprints
    register_blueprints(app)
    
    # Initialize workflow engines (only if not testing)
    if not app.config.get('TESTING', False):
        from app.workflows.engine import VehicleWorkflowEngine
        from app.workflows.automated import AutomatedWorkflowEngine
        app.workflow_engine = VehicleWorkflowEngine(app)
        app.automated_workflow = AutomatedWorkflowEngine(app)
        
        # Start background task scheduler (only in production)
        from app.core.scheduler import init_scheduler
        init_scheduler(app)
    
    # Initialize TowBook integration
    from app.integrations.towbook import init_towbook_integration
    app.towbook_integration = init_towbook_integration(app)
    
    # Initialize Phase 4 Advanced Analytics (only if not testing)
    if not app.config.get('TESTING', False):
        from app.analytics.engine import AnalyticsEngine
        from app.analytics.dashboard import DashboardManager
        from app.analytics.reports import ReportGenerator
        
        app.analytics_engine = AnalyticsEngine(app)
        app.dashboard_manager = DashboardManager(app)
        app.report_generator = ReportGenerator(app)
        
        app.logger.info("Phase 4 Advanced Analytics initialized")
    
    return app

def setup_logging(app):
    """Configure centralized logging system"""
    
    logging.basicConfig(
        level=getattr(logging, app.config['LOG_LEVEL']),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(app.config['LOG_FILE']),
            logging.StreamHandler()
        ]
    )
    
    # Create specialized loggers
    app.logger.info(f"iTow VMS starting in {app.config.get('ENV', 'development')} mode")
    
    # Workflow logger
    workflow_logger = logging.getLogger('workflow')
    workflow_logger.setLevel(logging.INFO)
    
    # TowBook integration logger  
    towbook_logger = logging.getLogger('towbook')
    towbook_logger.setLevel(logging.INFO)
    
    # Authentication logger
    auth_logger = logging.getLogger('auth')
    auth_logger.setLevel(logging.INFO)

def register_blueprints(app):
    """Register all application blueprints"""
    
    # Authentication blueprint
    from app.core.auth import auth_bp
    app.register_blueprint(auth_bp)
    
    # API routes
    from app.api.routes import api_bp
    app.register_blueprint(api_bp, url_prefix='/api')
    
    # Main application routes
    from app.api.main_routes import main_bp
    app.register_blueprint(main_bp)
    
    # Workflow dashboard
    from app.workflows.dashboard import dashboard_bp
    app.register_blueprint(dashboard_bp, url_prefix='/dashboard')
    
    # Phase 4 Advanced Analytics routes
    from app.analytics.routes import analytics_bp
    app.register_blueprint(analytics_bp, url_prefix='/analytics')

if __name__ == '__main__':
    app = create_app()
    app.run(
        host='0.0.0.0',
        port=int(os.environ.get('PORT', 5000)),
        debug=app.config['DEBUG']
    )
