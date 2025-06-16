#!/usr/bin/env python3
"""
iTow Vehicle Management System - Main Application Entry Point
Enhanced architecture with application factory pattern

This replaces the old app.py with a cleaner, more maintainable structure.
The original app.py is preserved for reference and migration purposes.
"""

import os
import sys
import logging
from app.factory import create_app

def main():
    """Main application entry point"""
    
    # Create application using factory pattern
    app = create_app()
    
    # Log startup information
    app.logger.info("="*60)
    app.logger.info("iTow Vehicle Management System - Enhanced Architecture")
    app.logger.info(f"Environment: {app.config.get('ENV', 'development')}")
    app.logger.info(f"Debug Mode: {app.config.get('DEBUG', False)}")
    app.logger.info(f"Database: {app.config.get('DATABASE_PATH', 'Not configured')}")
    app.logger.info("="*60)
    
    # Run application
    try:
        app.run(
            host=app.config.get('HOST', '0.0.0.0'),
            port=app.config.get('PORT', 5000),
            debug=app.config.get('DEBUG', False)
        )
    except KeyboardInterrupt:
        app.logger.info("Application shutdown requested by user")
    except Exception as e:
        app.logger.error(f"Application startup failed: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
