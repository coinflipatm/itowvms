#!/usr/bin/env python3
"""
Migrate users from database.db to vehicles.db for authentication consistency
"""
import sqlite3
import os
import sys

# Add the current directory to Python path
sys.path.insert(0, '/workspaces/itowvms')

from database import get_database_path

def migrate_users():
    print("="*50)
    print("USER MIGRATION SCRIPT")
    print("="*50)
    
    source_db = 'database.db'
    target_db = get_database_path()
    
    print(f"Source database: {source_db}")
    print(f"Target database: {target_db}")
    
    if not os.path.exists(source_db):
        print(f"❌ Source database {source_db} not found")
        return False
    
    if not os.path.exists(target_db):
        print(f"❌ Target database {target_db} not found")
        return False
    
    try:
        # Connect to source database
        source_conn = sqlite3.connect(source_db)
        source_conn.row_factory = sqlite3.Row
        source_cursor = source_conn.cursor()
        
        # Check if users table exists in source
        source_cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users';")
        if not source_cursor.fetchone():
            print("❌ No users table in source database")
            source_conn.close()
            return False
        
        # Get all users from source
        source_cursor.execute("SELECT * FROM users;")
        users = source_cursor.fetchall()
        print(f"📊 Found {len(users)} users in source database")
        
        # Connect to target database  
        target_conn = sqlite3.connect(target_db)
        target_cursor = target_conn.cursor()
        
        # Create users table in target if it doesn't exist
        target_cursor.execute('''
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
        target_cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            username TEXT NOT NULL,
            action_type TEXT NOT NULL,
            details TEXT
        )
        ''')
        
        # Check existing users in target
        target_cursor.execute("SELECT COUNT(*) FROM users;")
        existing_count = target_cursor.fetchone()[0]
        print(f"📊 Target database has {existing_count} existing users")
        
        # Copy users from source to target
        migrated_count = 0
        skipped_count = 0
        
        for user in users:
            try:
                target_cursor.execute("""
                    INSERT OR IGNORE INTO users 
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
                
                if target_cursor.rowcount > 0:
                    migrated_count += 1
                    print(f"✅ Migrated user: {user['username']} ({user['role']})")
                else:
                    skipped_count += 1
                    print(f"⚠️  Skipped existing user: {user['username']}")
                    
            except Exception as e:
                print(f"❌ Error migrating user {user['username']}: {e}")
                skipped_count += 1
        
        target_conn.commit()
        
        # Verify migration
        target_cursor.execute("SELECT COUNT(*) FROM users;")
        final_count = target_cursor.fetchone()[0]
        
        print(f"\n📊 Migration Summary:")
        print(f"  Users migrated: {migrated_count}")
        print(f"  Users skipped: {skipped_count}")
        print(f"  Total users in target: {final_count}")
        
        # Show users in target database
        target_cursor.execute("SELECT username, email, role, is_active FROM users;")
        final_users = target_cursor.fetchall()
        
        print(f"\n👥 Users in target database:")
        for user in final_users:
            status = "Active" if user[3] else "Inactive"
            print(f"  {user[0]} ({user[1]}) - Role: {user[2]}, Status: {status}")
        
        source_conn.close()
        target_conn.close()
        
        print(f"\n✅ Migration completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    migrate_users()
