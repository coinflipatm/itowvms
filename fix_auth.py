#!/usr/bin/env python3
"""
Direct authentication fix - creates admin user and tests login flow
"""

import sqlite3
import os
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

def create_admin_user():
    """Create admin user in the database"""
    db_path = '/workspaces/itowvms/database.db'
    
    print(f"Working with database: {db_path}")
    print(f"Database exists: {os.path.exists(db_path)}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Ensure the users table exists
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
    
    # Check if admin user exists
    cursor.execute("SELECT username FROM users WHERE username = ?", ('admin',))
    if cursor.fetchone():
        print("Admin user already exists")
    else:
        # Create admin user
        username = 'admin'
        password = 'admin123'
        email = 'admin@example.com'
        password_hash = generate_password_hash(password)
        created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        cursor.execute('''
            INSERT INTO users (username, email, password_hash, role, created_at, is_active)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (username, email, password_hash, 'admin', created_at, 1))
        
        print(f"Created admin user: {username}/{password}")
    
    conn.commit()
    
    # Verify users exist
    cursor.execute("SELECT username, role, is_active FROM users")
    users = cursor.fetchall()
    print(f"Users in database: {users}")
    
    conn.close()
    return True

def test_authentication():
    """Test the authentication process"""
    print("\n=== Testing Authentication ===")
    
    db_path = '/workspaces/itowvms/database.db'
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Get admin user
    cursor.execute("SELECT * FROM users WHERE username = ?", ('admin',))
    user = cursor.fetchone()
    
    if not user:
        print("❌ No admin user found")
        return False
    
    # Test password
    if check_password_hash(user['password_hash'], 'admin123'):
        print("✅ Password verification successful")
    else:
        print("❌ Password verification failed")
        return False
    
    conn.close()
    return True

if __name__ == "__main__":
    print("=== Authentication Fix Script ===")
    
    # Step 1: Create admin user
    create_admin_user()
    
    # Step 2: Test authentication
    test_authentication()
    
    print("\n✅ Authentication setup complete!")
    print("Admin credentials: admin/admin123")
