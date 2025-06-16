#!/usr/bin/env python3
"""
Fix the users table structure and migrate users
"""
import sqlite3
import os
import sys

# Add the current directory to Python path
sys.path.insert(0, '/workspaces/itowvms')

from database import get_database_path

def fix_users_table():
    print("="*50)
    print("FIXING USERS TABLE STRUCTURE")
    print("="*50)
    
    target_db = get_database_path()
    print(f"Working with database: {target_db}")
    
    try:
        conn = sqlite3.connect(target_db)
        cursor = conn.cursor()
        
        # Check if users table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users';")
        table_exists = cursor.fetchone()
        
        if table_exists:
            # Get current table structure
            cursor.execute("PRAGMA table_info(users);")
            columns = cursor.fetchall()
            print(f"Current users table structure:")
            for col in columns:
                print(f"  {col[1]} ({col[2]})")
            
            # Drop and recreate the table with correct structure
            print(f"\n🔄 Dropping and recreating users table...")
            cursor.execute("DROP TABLE users;")
        
        # Create the users table with the correct structure
        cursor.execute('''
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'readonly',
            created_at TEXT NOT NULL,
            last_login TEXT,
            is_active BOOLEAN NOT NULL DEFAULT 1
        )
        ''')
        
        # Create user logs table
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
        print(f"✅ Users table created successfully")
        
        # Now migrate users from database.db
        source_db = 'database.db'
        if os.path.exists(source_db):
            print(f"\n🔄 Migrating users from {source_db}...")
            
            source_conn = sqlite3.connect(source_db)
            source_conn.row_factory = sqlite3.Row
            source_cursor = source_conn.cursor()
            
            source_cursor.execute("SELECT * FROM users;")
            users = source_cursor.fetchall()
            
            migrated_count = 0
            for user in users:
                try:
                    cursor.execute("""
                        INSERT INTO users 
                        (username, email, password_hash, role, created_at, last_login, is_active)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        user['username'],
                        user['email'], 
                        user['password_hash'],
                        user['role'],
                        user['created_at'],
                        user['last_login'],
                        user['is_active']
                    ))
                    migrated_count += 1
                    print(f"✅ Migrated user: {user['username']} ({user['role']})")
                    
                except Exception as e:
                    print(f"❌ Error migrating user {user['username']}: {e}")
            
            conn.commit()
            source_conn.close()
            
            print(f"\n📊 Migrated {migrated_count} users successfully")
        
        # Verify final state
        cursor.execute("SELECT username, email, role, is_active FROM users;")
        final_users = cursor.fetchall()
        
        print(f"\n👥 Final users in database:")
        for user in final_users:
            status = "Active" if user[3] else "Inactive"
            print(f"  {user[0]} ({user[1]}) - Role: {user[2]}, Status: {status}")
        
        conn.close()
        print(f"\n✅ Users table fix completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error fixing users table: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    fix_users_table()
