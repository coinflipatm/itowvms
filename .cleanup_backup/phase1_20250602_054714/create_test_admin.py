#!/usr/bin/env python3
"""
Create a test admin user for authentication testing
"""

import sqlite3
from werkzeug.security import generate_password_hash

def create_test_admin():
    """Create a test admin user with known credentials"""
    conn = sqlite3.connect('/workspaces/itowvms/database.db')
    cursor = conn.cursor()
    
    # Check if test_admin already exists
    cursor.execute("SELECT username FROM users WHERE username = ?", ('test_admin',))
    if cursor.fetchone():
        print("Test admin user already exists")
        conn.close()
        return
    
    # Create test admin user
    username = 'test_admin'
    password = 'test123'
    email = 'test@example.com'
    password_hash = generate_password_hash(password)
    
    cursor.execute("""
        INSERT INTO users (username, email, password_hash, role, created_at, is_active)
        VALUES (?, ?, ?, ?, datetime('now'), 1)
    """, (username, email, password_hash, 'admin'))
    
    conn.commit()
    conn.close()
    
    print(f"✅ Created test admin user:")
    print(f"   Username: {username}")
    print(f"   Password: {password}")
    print(f"   Email: {email}")

if __name__ == "__main__":
    create_test_admin()
