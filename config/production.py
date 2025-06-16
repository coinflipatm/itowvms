"""
Production Configuration
Secure configuration for production deployment with enhanced features
"""

import os
from datetime import timedelta

class ProductionConfig:
    """Production environment configuration"""
    
    # Flask Settings
    DEBUG = False
    TESTING = False
    SECRET_KEY = os.environ.get('SECRET_KEY')  # Must be set in production
    
    # Database Settings
    DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///database.db')
    DATABASE_BACKUP_URL = os.environ.get('DATABASE_BACKUP_URL', 'sqlite:///database_backup.db')
    DATABASE_POOL_SIZE = int(os.environ.get('DATABASE_POOL_SIZE', 10))
    DATABASE_POOL_TIMEOUT = int(os.environ.get('DATABASE_POOL_TIMEOUT', 30))
    
    # Security configuration
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)  # 8-hour sessions
    BCRYPT_LOG_ROUNDS = 13  # Higher rounds for production
    
    # TowBook Integration
    TOWBOOK_TEST_MODE = False
    TOWBOOK_SYNC_INTERVAL = timedelta(hours=2)  # Less frequent in production
    TOWBOOK_BATCH_SIZE = 50
    TOWBOOK_USERNAME = os.environ.get('TOWBOOK_USERNAME')
    TOWBOOK_PASSWORD = os.environ.get('TOWBOOK_PASSWORD')
    
    # Logging
    LOG_LEVEL = 'INFO'
    LOG_FILE = 'logs/itow_prod.log'
    LOG_MAX_BYTES = 52428800  # 50MB
    LOG_BACKUP_COUNT = 10
    
    # Workflow Settings
    SEVEN_DAY_NOTICE_ENABLED = True
    AUTO_DOCUMENTATION_ENABLED = True
    BATCH_PROCESSING_ENABLED = True
    
    # Chrome WebDriver
    CHROME_HEADLESS = True
    CHROME_DEBUG_PORT = None
    
    # Session Management
    PERMANENT_SESSION_LIFETIME = timedelta(hours=12)
    SESSION_COOKIE_SECURE = True  # HTTPS in production
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # Security
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600  # 1 hour
