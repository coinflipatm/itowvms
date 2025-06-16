"""
Enhanced Authentication Module
Consolidated authentication system with improved security
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, session, current_app
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import sqlite3
import logging
import secrets
import uuid
from functools import wraps
from flask import jsonify

# Initialize Flask-Login
login_manager = LoginManager()
auth_logger = logging.getLogger('auth')

# Create Blueprint for authentication routes
auth_bp = Blueprint('auth', __name__)

class User(UserMixin):
    """Enhanced User model with role-based permissions"""
    
    def __init__(self, id, username, email, password_hash, role, created_at, last_login=None, is_active=True):
        self.id = id
        self.username = username
        self.email = email
        self.password_hash = password_hash
        self.role = role
        self.created_at = created_at
        self.last_login = last_login
        self._is_active = is_active
    
    @property
    def is_active(self):
        return self._is_active
    
    def can_edit(self):
        """Check if user has edit permissions"""
        return self.role in ['admin', 'editor']
    
    def can_delete(self):
        """Check if user has delete permissions"""
        return self.role == 'admin'
    
    def can_manage_users(self):
        """Check if user can manage other users"""
        return self.role == 'admin'
    
    def can_access_dashboard(self):
        """Check if user can access operations dashboard"""
        return self.role in ['admin', 'editor', 'viewer']

def init_auth(app):
    """Initialize authentication with Flask app"""
    
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'
    
    # Create auth tables if they don't exist
    with app.app_context():
        init_auth_db()
    
    # Register user loader
    @login_manager.user_loader
    def load_user(user_id):
        return get_user_by_id(user_id)

def init_auth_db():
    """Initialize authentication database tables"""
    
    try:
        conn = get_auth_db_connection()
        cursor = conn.cursor()
        
        # Enhanced users table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'viewer',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP,
            is_active BOOLEAN DEFAULT 1,
            failed_login_attempts INTEGER DEFAULT 0,
            locked_until TIMESTAMP,
            password_reset_token TEXT,
            password_reset_expires TIMESTAMP
        )
        ''')
        
        # User sessions table for better session management
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_sessions (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            session_token TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP NOT NULL,
            ip_address TEXT,
            user_agent TEXT,
            is_active BOOLEAN DEFAULT 1,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
        ''')
        
        # User activity log
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_activity_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            activity_type TEXT NOT NULL,
            activity_details TEXT,
            ip_address TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
        ''')
        
        conn.commit()
        conn.close()
        
        auth_logger.info("Authentication database initialized")
        
    except Exception as e:
        auth_logger.error(f"Failed to initialize auth database: {e}")
        raise

def get_auth_db_connection():
    """Get authentication database connection"""
    
    # For now, use the same database as the main app
    # In production, consider separate auth database
    db_url = current_app.config.get('DATABASE_URL', 'sqlite:///database.db')
    if db_url.startswith('sqlite:///'):
        db_path = db_url.replace('sqlite:///', '')
        return sqlite3.connect(db_path)
    else:
        raise ValueError("Only SQLite databases supported for auth currently")

def get_user_by_id(user_id):
    """Get user by ID"""
    
    try:
        conn = get_auth_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT id, username, email, password_hash, role, created_at, last_login, is_active
        FROM users WHERE id = ? AND is_active = 1
        ''', (user_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return User(*row)
        return None
        
    except Exception as e:
        auth_logger.error(f"Failed to get user {user_id}: {e}")
        return None

def get_user_by_username(username):
    """Get user by username"""
    
    try:
        conn = get_auth_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT id, username, email, password_hash, role, created_at, last_login, is_active
        FROM users WHERE username = ? AND is_active = 1
        ''', (username,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return User(*row)
        return None
        
    except Exception as e:
        auth_logger.error(f"Failed to get user by username {username}: {e}")
        return None

def create_user(username, email, password, role='viewer'):
    """Create new user"""
    
    try:
        conn = get_auth_db_connection()
        cursor = conn.cursor()
        
        user_id = str(uuid.uuid4())
        password_hash = generate_password_hash(password)
        
        cursor.execute('''
        INSERT INTO users (id, username, email, password_hash, role, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, username, email, password_hash, role, datetime.now()))
        
        conn.commit()
        conn.close()
        
        auth_logger.info(f"User created: {username} ({role})")
        return user_id
        
    except sqlite3.IntegrityError as e:
        auth_logger.error(f"Failed to create user {username}: {e}")
        return None
    except Exception as e:
        auth_logger.error(f"Unexpected error creating user {username}: {e}")
        return None

def authenticate_user(username, password, ip_address=None):
    """Authenticate user with enhanced security"""
    
    try:
        user = get_user_by_username(username)
        
        if not user:
            log_activity(None, 'failed_login', f'Unknown username: {username}', ip_address)
            return None
        
        # Check if account is locked
        if is_account_locked(user.id):
            log_activity(user.id, 'failed_login', 'Account locked', ip_address)
            return None
        
        # Verify password
        if check_password_hash(user.password_hash, password):
            # Successful login
            reset_failed_attempts(user.id)
            update_last_login(user.id)
            log_activity(user.id, 'login', 'Successful login', ip_address)
            return user
        else:
            # Failed login
            increment_failed_attempts(user.id)
            log_activity(user.id, 'failed_login', 'Invalid password', ip_address)
            return None
            
    except Exception as e:
        auth_logger.error(f"Authentication error for {username}: {e}")
        return None

def is_account_locked(user_id):
    """Check if user account is locked"""
    
    try:
        conn = get_auth_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT failed_login_attempts, locked_until 
        FROM users WHERE id = ?
        ''', (user_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            failed_attempts, locked_until = row
            
            # Check if locked by time
            if locked_until and datetime.fromisoformat(locked_until) > datetime.now():
                return True
            
            # Check if locked by failed attempts
            if failed_attempts >= 5:  # Lock after 5 failed attempts
                return True
        
        return False
        
    except Exception as e:
        auth_logger.error(f"Failed to check account lock status: {e}")
        return False

def increment_failed_attempts(user_id):
    """Increment failed login attempts"""
    
    try:
        conn = get_auth_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        UPDATE users 
        SET failed_login_attempts = failed_login_attempts + 1,
            locked_until = CASE 
                WHEN failed_login_attempts >= 4 THEN datetime('now', '+30 minutes')
                ELSE locked_until
            END
        WHERE id = ?
        ''', (user_id,))
        
        conn.commit()
        conn.close()
        
    except Exception as e:
        auth_logger.error(f"Failed to increment failed attempts: {e}")

def reset_failed_attempts(user_id):
    """Reset failed login attempts"""
    
    try:
        conn = get_auth_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        UPDATE users 
        SET failed_login_attempts = 0, locked_until = NULL
        WHERE id = ?
        ''', (user_id,))
        
        conn.commit()
        conn.close()
        
    except Exception as e:
        auth_logger.error(f"Failed to reset failed attempts: {e}")

def update_last_login(user_id):
    """Update user's last login timestamp"""
    
    try:
        conn = get_auth_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        UPDATE users SET last_login = ? WHERE id = ?
        ''', (datetime.now(), user_id))
        
        conn.commit()
        conn.close()
        
    except Exception as e:
        auth_logger.error(f"Failed to update last login: {e}")

def log_activity(user_id, activity_type, details, ip_address=None):
    """Log user activity"""
    
    try:
        conn = get_auth_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        INSERT INTO user_activity_log (user_id, activity_type, activity_details, ip_address)
        VALUES (?, ?, ?, ?)
        ''', (user_id, activity_type, details, ip_address))
        
        conn.commit()
        conn.close()
        
    except Exception as e:
        auth_logger.error(f"Failed to log activity: {e}")

def api_login_required(f):
    """Decorator for API endpoints requiring authentication"""
    
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated_function

def role_required(required_roles):
    """Decorator for role-based access control"""
    
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                if request.is_json:
                    return jsonify({'error': 'Authentication required'}), 401
                else:
                    return redirect(url_for('auth.login'))
            
            if current_user.role not in required_roles:
                if request.is_json:
                    return jsonify({'error': 'Insufficient permissions'}), 403
                else:
                    flash('You do not have permission to access this page.', 'error')
                    return redirect(url_for('auth.login'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Authentication routes
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Enhanced login with security features"""
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        remember = bool(request.form.get('remember'))
        
        if not username or not password:
            flash('Username and password are required.', 'error')
            return render_template('auth/login.html')
        
        # Get client IP
        ip_address = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
        
        user = authenticate_user(username, password, ip_address)
        
        if user:
            login_user(user, remember=remember)
            
            # Redirect to next page or dashboard
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            
            # Check user role for default redirect
            if user.can_access_dashboard():
                return redirect(url_for('dashboard.daily_operations'))
            else:
                return redirect(url_for('main.index'))
        else:
            flash('Invalid username or password.', 'error')
    
    return render_template('auth/login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    """Enhanced logout with activity logging"""
    
    if current_user.is_authenticated:
        ip_address = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
        log_activity(current_user.id, 'logout', 'User logged out', ip_address)
    
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))

# Legacy compatibility functions
def get_user(user_id):
    """Legacy compatibility function"""
    return get_user_by_id(user_id)
