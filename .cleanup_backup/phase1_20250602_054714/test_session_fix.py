#!/usr/bin/env python3
"""
Test session creation and authentication directly
"""

import os
import sys
import sqlite3
from flask import Flask, session
from werkzeug.security import check_password_hash

# Add current directory to path
sys.path.append('/workspaces/itowvms')

def test_database_connection():
    """Test if we can connect to the auth database"""
    print("=== Testing Database Connection ===")
    try:
        conn = sqlite3.connect('/workspaces/itowvms/database.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Check if users table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
        if cursor.fetchone():
            print("✅ Users table exists")
        else:
            print("❌ Users table does not exist")
            return False
            
        # Check if admin user exists
        cursor.execute("SELECT * FROM users WHERE username = ?", ('test_admin',))
        user = cursor.fetchone()
        if user:
            print(f"✅ Found admin user: {user['username']}, role: {user['role']}, active: {user['is_active']}")
            return user
        else:
            print("❌ No admin user found")
            return False
            
    except Exception as e:
        print(f"❌ Database connection error: {e}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()

def test_password_verification(user):
    """Test password verification"""
    print("\n=== Testing Password Verification ===")
    try:
        test_password = 'test123'
        if check_password_hash(user['password_hash'], test_password):
            print("✅ Password verification successful")
            return True
        else:
            print("❌ Password verification failed")
            return False
    except Exception as e:
        print(f"❌ Password verification error: {e}")
        return False

def test_flask_session():
    """Test Flask session creation"""
    print("\n=== Testing Flask Session ===")
    try:
        app = Flask(__name__)
        app.config['SECRET_KEY'] = 'test-secret-key'
        app.config['SESSION_COOKIE_SECURE'] = False
        app.config['SESSION_COOKIE_HTTPONLY'] = True
        app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
        
        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess['user_id'] = 1
                sess['username'] = 'test_admin'
                print("✅ Session variables set successfully")
                
            # Test if session persists
            with client.session_transaction() as sess:
                if 'user_id' in sess and sess['user_id'] == 1:
                    print("✅ Session persistence confirmed")
                    return True
                else:
                    print("❌ Session persistence failed")
                    return False
                    
    except Exception as e:
        print(f"❌ Flask session test error: {e}")
        return False

def main():
    print("Starting authentication diagnostics...\n")
    
    # Test 1: Database connection
    user = test_database_connection()
    if not user:
        print("\n❌ Database test failed - cannot proceed")
        return
    
    # Test 2: Password verification
    if not test_password_verification(user):
        print("\n❌ Password verification failed - cannot proceed")
        return
    
    # Test 3: Flask session
    if not test_flask_session():
        print("\n❌ Flask session test failed")
        return
    
    print("\n✅ All authentication components are working correctly!")
    print("\nIf the web application is still having session issues, the problem")
    print("might be in the Flask-Login integration or session configuration.")

if __name__ == "__main__":
    main()
