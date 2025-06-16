#!/usr/bin/env python3
"""
Create a test user with known credentials
"""
import sqlite3
import sys
from werkzeug.security import generate_password_hash
from datetime import datetime

# Add the current directory to Python path
sys.path.insert(0, '/workspaces/itowvms')

from database import get_database_path

def create_test_user():
    print("="*50)
    print("CREATING TEST USER")
    print("="*50)
    
    try:
        conn = sqlite3.connect(get_database_path())
        cursor = conn.cursor()
        
        # Create a test user with known credentials
        username = "testuser"
        email = "testuser@example.com"
        password = "password123"
        role = "admin"
        
        password_hash = generate_password_hash(password)
        created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Delete existing test user if exists
        cursor.execute("DELETE FROM users WHERE username = ? OR email = ?", (username, email))
        
        # Insert new test user
        cursor.execute("""
            INSERT INTO users (username, email, password_hash, role, created_at, is_active)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (username, email, password_hash, role, created_at, True))
        
        conn.commit()
        
        print(f"✅ Created test user:")
        print(f"   Username: {username}")
        print(f"   Email: {email}")
        print(f"   Password: {password}")
        print(f"   Role: {role}")
        
        # Show all users
        print(f"\n👥 All users in database:")
        cursor.execute("SELECT username, email, role, is_active FROM users ORDER BY username;")
        users = cursor.fetchall()
        
        for user in users:
            status = "Active" if user[3] else "Inactive"
            print(f"  {user[0]} ({user[1]}) - Role: {user[2]}, Status: {status}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error creating test user: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    create_test_user()
