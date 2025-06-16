#!/usr/bin/env python3
"""
Check authentication setup and user status
"""
import sqlite3
import os

# Check if user database exists and has users
def check_auth_setup():
    print("="*50)
    print("AUTHENTICATION DEBUG")
    print("="*50)
    
    # Check if database files exist
    db_files = ['database.db', 'vehicles.db']
    for db_file in db_files:
        if os.path.exists(db_file):
            print(f"✅ {db_file} exists ({os.path.getsize(db_file)} bytes)")
        else:
            print(f"❌ {db_file} not found")
    
    # Check users in database.db
    try:
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        
        # Check if users table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users';")
        if cursor.fetchone():
            print("\n✅ Users table exists")
            
            # Count users
            cursor.execute("SELECT COUNT(*) FROM users;")
            user_count = cursor.fetchone()[0]
            print(f"📊 Total users: {user_count}")
            
            if user_count > 0:
                # Show users (without passwords)
                cursor.execute("SELECT id, username, email, role, is_active, created_at, last_login FROM users;")
                users = cursor.fetchall()
                print("\n👥 Users in system:")
                for user in users:
                    status = "Active" if user[4] else "Inactive"
                    print(f"  ID: {user[0]}, Username: {user[1]}, Email: {user[2]}")
                    print(f"      Role: {user[3]}, Status: {status}")
                    print(f"      Created: {user[5]}, Last Login: {user[6] or 'Never'}")
                    print()
            else:
                print("⚠️  No users found - you need to create an admin user")
                
        else:
            print("❌ Users table does not exist")
            
        conn.close()
        
    except Exception as e:
        print(f"❌ Error checking users database: {e}")
    
    # Check vehicles.db for users table (in case it's there)
    try:
        conn = sqlite3.connect('vehicles.db')
        cursor = conn.cursor()
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users';")
        if cursor.fetchone():
            print("\n✅ Users table also found in vehicles.db")
            cursor.execute("SELECT COUNT(*) FROM users;")
            user_count = cursor.fetchone()[0]
            print(f"📊 Users in vehicles.db: {user_count}")
        else:
            print("\n❌ No users table in vehicles.db")
            
        conn.close()
        
    except Exception as e:
        print(f"❌ Error checking vehicles.db: {e}")

if __name__ == "__main__":
    check_auth_setup()
