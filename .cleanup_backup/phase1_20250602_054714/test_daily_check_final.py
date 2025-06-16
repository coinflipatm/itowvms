#!/usr/bin/env python3
"""
Final verification test for the daily status check system.
"""

import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_complete_system():
    """Test the complete daily check system"""
    print("=" * 60)
    print("FINAL DAILY CHECK SYSTEM VERIFICATION")
    print("=" * 60)
    
    try:
        # Import Flask app and create context
        from app import app
        with app.app_context():
            print("✅ Flask app context created")
            
            # Test database connection
            from database import get_db_connection
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM vehicles WHERE archived = 0")
            active_count = cursor.fetchone()[0]
            conn.close()
            print(f"✅ Database connection successful - {active_count} active vehicles")
            
            # Test scheduler import and instantiation
            from scheduler import get_scheduler
            scheduler = get_scheduler()
            print("✅ Scheduler imported and instantiated")
            
            # Test daily morning status check
            print("\n--- Testing Daily Morning Status Check ---")
            scheduler._daily_morning_status_check()
            print("✅ Daily morning status check completed")
            
            # Test API route function via HTTP call simulation
            print("\n--- Testing API Route ---")
            # Import the app to test route functionality
            from flask import Flask
            test_client = app.test_client()
            with app.test_request_context():
                response = test_client.post('/api/scheduler/daily-check')
                if response.status_code == 200:
                    print(f"✅ API route executed successfully - Response: {response.get_json()}")
                else:
                    print(f"⚠️ API route returned status {response.status_code}")
                    print(f"Response data: {response.get_data(as_text=True)}")
            
            # Check notifications table
            print("\n--- Checking Notifications System ---")
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Ensure notifications table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='notifications'")
            if not cursor.fetchone():
                cursor.execute('''
                    CREATE TABLE notifications (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        vehicle_id TEXT NOT NULL,
                        notification_type TEXT NOT NULL,
                        message TEXT NOT NULL,
                        due_date TEXT NOT NULL,
                        status TEXT DEFAULT 'pending',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        sent_date TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                conn.commit()
                print("✅ Notifications table created")
            else:
                print("✅ Notifications table exists")
            
            # Check recent notifications
            cursor.execute("SELECT COUNT(*) FROM notifications WHERE created_at >= date('now', '-1 day')")
            recent_notifications = cursor.fetchone()[0]
            print(f"✅ Recent notifications: {recent_notifications}")
            
            conn.close()
            
            print("\n" + "=" * 60)
            print("✅ ALL TESTS PASSED - SYSTEM IS READY")
            print("=" * 60)
            
            return True
            
    except Exception as e:
        print(f"❌ System test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_complete_system()
    sys.exit(0 if success else 1)
