"""
Development Configuration
Settings for development environment
"""

import os
from datetime import timedelta

class DevelopmentConfig:
    """Development environment configuration"""
    
    # Flask Settings
    DEBUG = True
    TESTING = False
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    
    # Database Settings
    DATABASE_URL = 'sqlite:///vehicles.db'
    DATABASE_BACKUP_URL = 'sqlite:///vehicles_backup.db'
    
    # TowBook Integration
    TOWBOOK_TEST_MODE = True
    TOWBOOK_SYNC_INTERVAL = timedelta(minutes=5)  # Frequent sync for testing
    TOWBOOK_BATCH_SIZE = 10
    
    # Logging
    LOG_LEVEL = 'DEBUG'
    LOG_FILE = 'logs/itow_dev.log'
    LOG_MAX_BYTES = 10485760  # 10MB
    LOG_BACKUP_COUNT = 5
    
    # Workflow Settings
    SEVEN_DAY_NOTICE_ENABLED = True
    AUTO_DOCUMENTATION_ENABLED = True
    BATCH_PROCESSING_ENABLED = False  # Manual control in dev
    
    # Chrome WebDriver
    CHROME_HEADLESS = False  # Show browser in development
    CHROME_DEBUG_PORT = 9222
    
    # Session Management
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)
    SESSION_COOKIE_SECURE = False  # HTTP in development
    SESSION_COOKIE_HTTPONLY = True
