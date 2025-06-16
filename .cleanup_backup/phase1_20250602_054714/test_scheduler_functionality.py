#!/usr/bin/env python3
"""
Test script to verify scheduler functionality and database connection handling.
"""

import sys
import os
import logging
import traceback

# Import Flask app for context
from app import app 

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_scheduler_import():
    """Test that the scheduler can be imported."""
    try:
        from scheduler import AutomatedStatusScheduler
        print("✅ Scheduler imported successfully")
        return AutomatedStatusScheduler
    except Exception as e:
        print(f"❌ Failed to import scheduler: {e}")
        traceback.print_exc()
        return None

def test_scheduler_instantiation(scheduler_class):
    """Test that the scheduler can be instantiated."""
    try:
        scheduler = scheduler_class()
        print("✅ Scheduler instantiated successfully")
        return scheduler
    except Exception as e:
        print(f"❌ Failed to instantiate scheduler: {e}")
        traceback.print_exc()
        return None

def test_database_connection():
    """Test basic database connectivity."""
    try:
        from database import get_db_connection
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM vehicles WHERE archived = 0")
        active_count = cursor.fetchone()[0]
        conn.close()
        print(f"✅ Database connection successful - {active_count} active vehicles")
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        traceback.print_exc()
        return False

def test_daily_morning_check(scheduler):
    """Test the daily morning status check."""
    try:
        print("🔍 Testing daily morning status check...")
        scheduler._daily_morning_status_check()
        print("✅ Daily morning status check completed successfully")
        return True
    except Exception as e:
        print(f"❌ Daily morning status check failed: {e}")
        traceback.print_exc()
        return False

def test_notification_methods(scheduler):
    """Test notification-related methods."""
    try:
        # Test with sample vehicle data
        test_vehicle = {
            'towbook_call_number': 'TEST123',
            'status': 'New',
            'last_updated': '2025-05-26',
            'owner_known': 'No',
            'id': 999  # Fake ID for testing
        }
        
        print("🔍 Testing notification threshold checking...")
        notifications = scheduler._check_status_thresholds(test_vehicle, 7)
        print(f"✅ Notification threshold check completed - {len(notifications)} notifications needed")
        
        # Test notification existence check
        print("🔍 Testing notification existence check...")
        exists = scheduler._notification_exists('TEST123', 'status_threshold')
        print(f"✅ Notification existence check completed - exists: {exists}")
        
        return True
    except Exception as e:
        print(f"❌ Notification methods test failed: {e}")
        traceback.print_exc()
        return False

def main():
    """Run all tests."""
    print("=" * 60)
    print("SCHEDULER FUNCTIONALITY TEST")
    print("=" * 60)

    # Create an application context
    with app.app_context():
        scheduler_class = test_scheduler_import()
        if not scheduler_class:
            print("❌ Prerequisite failed: Scheduler import. Aborting further tests.")
            return

        scheduler_instance = test_scheduler_instantiation(scheduler_class)
        # Some tests can run even if instantiation fails but others require an instance.

        print("\\n--- Database Connection Test ---")
        db_ok = test_database_connection()
        if not db_ok:
            print("⚠️  Database connection failed. Some scheduler functions might not work as expected.")

        if scheduler_instance:
            print("\\n--- Daily Morning Check Test ---")
            test_daily_morning_check(scheduler_instance)

            print("\\n--- Notification Methods Test ---")
            test_notification_methods(scheduler_instance)
        else:
            print("❌ Prerequisite failed: Scheduler instantiation. Skipping instance-dependent tests.")

    print("\\n" + "=" * 60)
    print("ALL TESTS COMPLETED")
    print("=" * 60)

if __name__ == "__main__":
    main()
