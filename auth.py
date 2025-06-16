from flask import Blueprint, render_template, redirect, url_for, flash, request, session, abort
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import sqlite3
import logging
import secrets
import uuid
from functools import wraps
from flask import jsonify

# Import the database path function for consistency
from database import get_database_path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask-Login
login_manager = LoginManager()

# Create a Blueprint for authentication routes
auth_bp = Blueprint('auth', __name__)

# User model
class User(UserMixin):
    def __init__(self, id, username, email, password_hash, role, created_at, last_login=None, is_active=True):
        self.id = id
        self.username = username
        self.email = email
        self.password_hash = password_hash
        self.role = role
        self.created_at = created_at
        self.last_login = last_login
        self._is_active = is_active  # Use a simple attribute, not a property
    
    # Define property for is_active to work with Flask-Login
    @property
    def is_active(self):
        return self._is_active
        
    # Access control methods
    def can_edit(self):
        """Check if user has edit permissions"""
        return self.role in ['admin', 'editor']
    
    def can_delete(self):
        """Check if user has delete permissions"""
        return self.role == 'admin'
    
    def can_manage_users(self):
        """Check if user can manage other users"""
        return self.role == 'admin'
    
    @staticmethod
    def get_by_id(user_id):
        conn = sqlite3.connect(get_database_path())
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        user_data = cursor.fetchone()
        conn.close()
        
        if user_data:
            return User(
                id=user_data['id'],
                username=user_data['username'],
                email=user_data['email'],
                password_hash=user_data['password_hash'],
                role=user_data['role'],
                created_at=user_data['created_at'],
                last_login=user_data['last_login'],
                is_active=bool(user_data['is_active'])
            )
        return None
    
    @staticmethod
    def get_by_username(username):
        conn = sqlite3.connect(get_database_path())
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        user_data = cursor.fetchone()
        conn.close()
        
        if user_data:
            return User(
                id=user_data['id'],
                username=user_data['username'],
                email=user_data['email'],
                password_hash=user_data['password_hash'],
                role=user_data['role'],
                created_at=user_data['created_at'],
                last_login=user_data['last_login'],
                is_active=bool(user_data['is_active'])
            )
        return None
    
    @staticmethod
    def get_by_email(email):
        conn = sqlite3.connect(get_database_path())
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
        user_data = cursor.fetchone()
        conn.close()
        
        if user_data:
            return User(
                id=user_data['id'],
                username=user_data['username'],
                email=user_data['email'],
                password_hash=user_data['password_hash'],
                role=user_data['role'],
                created_at=user_data['created_at'],
                last_login=user_data['last_login'],
                is_active=bool(user_data['is_active'])
            )
        return None
    
    @staticmethod
    def create_user(username, email, password, role='readonly'):
        """Create a new user (default role is readonly)"""
        conn = sqlite3.connect(get_database_path())
        cursor = conn.cursor()
        created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        password_hash = generate_password_hash(password)
        
        try:
            cursor.execute(
                "INSERT INTO users (username, email, password_hash, role, created_at, is_active) VALUES (?, ?, ?, ?, ?, ?)",
                (username, email, password_hash, role, created_at, True)
            )
            conn.commit()
            user_id = cursor.lastrowid
            conn.close()
            return User.get_by_id(user_id)
        except sqlite3.IntegrityError as e:
            conn.close()
            logger.error(f"Error creating user: {e}")
            return None
    
    @staticmethod
    def update_last_login(user_id):
        conn = sqlite3.connect(get_database_path())
        cursor = conn.cursor()
        last_login = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute("UPDATE users SET last_login = ? WHERE id = ?", (last_login, user_id))
        conn.commit()
        conn.close()
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# User loader for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    return User.get_by_id(user_id)

# Login route
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = request.form.get('remember') == 'on'
        
        logger.info(f"Login attempt for username: {username}")
        
        user = User.get_by_username(username)
        
        if user and user.check_password(password):
            if not user.is_active:
                logger.warning(f"Login denied for inactive user: {username}")
                flash('This account has been deactivated. Please contact an administrator.', 'danger')
                return redirect(url_for('auth.login'))
            
            logger.info(f"Successful login for user: {username}, attempting to set session")
            login_user(user, remember=remember)
            logger.info(f"Flask-Login login_user called, current_user.is_authenticated: {current_user.is_authenticated}")
            User.update_last_login(user.id)
            
            from utils import log_action
            log_action("LOGIN", user.username, f"User logged in: {user.username}")
            
            next_page = request.args.get('next')
            if not next_page or not next_page.startswith('/'):
                next_page = url_for('index')
            logger.info(f"Redirecting to: {next_page}")
            return redirect(next_page)
        
        logger.warning(f"Failed login attempt for username: {username}")
        flash('Invalid username or password', 'danger')
    
    return render_template('login.html')

# Register route
@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    # Check if any users exist - first user becomes admin
    conn = sqlite3.connect(get_database_path())
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    user_count = cursor.fetchone()[0]
    conn.close()
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if password != confirm_password:
            flash('Passwords do not match', 'danger')
            return redirect(url_for('auth.register'))
        
        # Check if username or email already exists
        if User.get_by_username(username):
            flash('Username already exists', 'danger')
            return redirect(url_for('auth.register'))
        
        if User.get_by_email(email):
            flash('Email already registered', 'danger')
            return redirect(url_for('auth.register'))
        
        # First user is admin, others are regular users
        role = 'admin' if user_count == 0 else 'readonly'
        
        user = User.create_user(username, email, password, role)
        if user:
            from utils import log_action
            log_action("REGISTER", username, f"New user registered: {username} with role: {role}")
            
            flash('Registration successful! You can now log in.', 'success')
            return redirect(url_for('auth.login'))
        else:
            flash('Registration failed. Please try again.', 'danger')
    
    return render_template('register.html')

# Logout route
@auth_bp.route('/logout')
@login_required
def logout():
    from utils import log_action
    log_action("LOGOUT", current_user.username, f"User logged out: {current_user.username}")
    
    logout_user()
    return redirect(url_for('auth.login'))

# Profile route
@auth_bp.route('/profile')
@login_required
def profile():
    return render_template('profile.html')

# Admin-only route for user management
@auth_bp.route('/admin/users')
@login_required
def admin_users():
    if current_user.role != 'admin':
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('index'))
    
    conn = sqlite3.connect(get_database_path())
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users ORDER BY id")
    users = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return render_template('admin_users.html', users=users)

# Admin route to toggle user active status
@auth_bp.route('/admin/users/<int:user_id>/toggle_active', methods=['POST'])
@login_required
def toggle_user_active(user_id):
    if current_user.role != 'admin':
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('index'))
    
    if current_user.id == user_id:
        flash('You cannot deactivate your own account', 'danger')
        return redirect(url_for('auth.admin_users'))
    
    conn = sqlite3.connect(get_database_path())
    cursor = conn.cursor()
    
    # Get current status
    cursor.execute("SELECT is_active FROM users WHERE id = ?", (user_id,))
    result = cursor.fetchone()
    if not result:
        conn.close()
        flash('User not found', 'danger')
        return redirect(url_for('auth.admin_users'))
    
    is_active = not bool(result[0])
    cursor.execute("UPDATE users SET is_active = ? WHERE id = ?", (is_active, user_id))
    conn.commit()
    
    # Get username for logging
    cursor.execute("SELECT username FROM users WHERE id = ?", (user_id,))
    username = cursor.fetchone()[0]
    conn.close()
    
    status_text = "activated" if is_active else "deactivated"
    
    from utils import log_action
    log_action("USER_ADMIN", current_user.username, f"User {username} {status_text} by {current_user.username}")
    
    flash(f'User {status_text} successfully', 'success')
    return redirect(url_for('auth.admin_users'))

# Admin route to change user role
@auth_bp.route('/admin/users/<int:user_id>/change_role', methods=['POST'])
@login_required
def change_user_role(user_id):
    if current_user.role != 'admin':
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('index'))
    
    new_role = request.form.get('role')
    valid_roles = ['readonly', 'editor', 'admin']
    if new_role not in valid_roles:
        flash('Invalid role', 'danger')
        return redirect(url_for('auth.admin_users'))
    
    conn = sqlite3.connect(get_database_path())
    cursor = conn.cursor()
    
    # Get username for logging
    cursor.execute("SELECT username FROM users WHERE id = ?", (user_id,))
    result = cursor.fetchone()
    if not result:
        conn.close()
        flash('User not found', 'danger')
        return redirect(url_for('auth.admin_users'))
    
    username = result[0]
    
    cursor.execute("UPDATE users SET role = ? WHERE id = ?", (new_role, user_id))
    conn.commit()
    conn.close()
    
    from utils import log_action
    log_action("USER_ADMIN", current_user.username, f"User {username} role changed to {new_role} by {current_user.username}")
    
    flash(f'User role changed to {new_role} successfully', 'success')
    return redirect(url_for('auth.admin_users'))

# Custom permission decorator for edit operations
def editor_required(f):
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.can_edit():
            flash('You do not have permission to edit content. Contact an administrator.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return login_required(decorated_function)

# Custom permission decorator for delete operations
def admin_required(f):
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.can_delete():
            flash('Administrator privileges required for this action.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return login_required(decorated_function)

# Custom login_required decorator for API endpoints
def api_login_required(f):
    """
    Custom login decorator for API endpoints that returns JSON instead of redirecting to login page
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            # For API requests, return JSON error instead of redirecting
            return jsonify({"error": "Authentication required", "code": "UNAUTHORIZED"}), 401
        return f(*args, **kwargs)
    return decorated_function

# Initialize auth database tables
def init_auth_db():
    conn = sqlite3.connect(get_database_path())
    cursor = conn.cursor()
    
    # Create users table if it doesn't exist
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL,
        created_at TEXT NOT NULL,
        last_login TEXT,
        is_active BOOLEAN NOT NULL DEFAULT 1
    )
    ''')
    
    # Create user activity logs table if it doesn't exist
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS user_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        username TEXT NOT NULL,
        action_type TEXT NOT NULL,
        details TEXT
    )
    ''')
    
    conn.commit()
    conn.close()
    
    logger.info("Auth database tables initialized")