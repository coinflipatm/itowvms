#!/usr/bin/env python3
"""
Isolated test for daily morning status check functionality.
"""

import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_daily_check_isolated():
    """Test daily check in isolation"""
    print("=" * 60)
    print("ISOLATED DAILY CHECK TEST")
    print("=" * 60)
    
    try:
        # Import Flask app and create context
        from app import app
        with app.app_context():
            print("✅ Flask app context created")
            
            # Test database connection first
            from database import get_db_connection
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM vehicles WHERE archived = 0")
            active_count = cursor.fetchone()[0]
            print(f"✅ Database connection successful - {active_count} active vehicles")
            
            # Don't close the connection yet - keep it open
            
            # Import scheduler but don't start it (to avoid conflicts)
            from scheduler import AutomatedStatusScheduler
            scheduler = AutomatedStatusScheduler()
            print("✅ Scheduler created (not started)")
            
            # Test the specific daily check method
            print("\n--- Testing Daily Morning Status Check Method ---")
            
            # Manual implementation of the daily check to debug the issue
            from datetime import datetime
            from utils import log_action
            
            print("Running manual daily morning status check...")
            
            # Use the same connection
            cursor.execute("SELECT * FROM vehicles WHERE archived = 0 LIMIT 5")  # Limit to 5 for testing
            vehicles = cursor.fetchall()
            
            today = datetime.now().date()
            checked_count = 0
            
            print(f"Checking {len(vehicles)} vehicles (limited sample)")
            
            for vehicle in vehicles:
                try:
                    call_number = vehicle['towbook_call_number']
                    current_status = vehicle['status']
                    last_updated = vehicle['last_updated']
                    
                    checked_count += 1
                    print(f"  Processing vehicle {call_number} - Status: {current_status}")
                    
                    # Parse last updated date
                    if last_updated:
                        try:
                            if ' ' in last_updated:
                                last_updated_date = datetime.strptime(last_updated, '%Y-%m-%d %H:%M:%S').date()
                            else:
                                last_updated_date = datetime.strptime(last_updated, '%Y-%m-%d').date()
                        except ValueError:
                            print(f"    Skipping {call_number} - invalid date format")
                            continue
                    else:
                        print(f"    Skipping {call_number} - no last_updated date")
                        continue
                    
                    days_in_status = (today - last_updated_date).days
                    print(f"    Days in status: {days_in_status}")
                    
                    # Test notification threshold checking without creating notifications
                    notifications_needed = scheduler._check_status_thresholds(vehicle, days_in_status, conn)
                    print(f"    Notifications needed: {len(notifications_needed)}")
                    
                except Exception as e:
                    print(f"    Error processing vehicle {call_number}: {e}")
                    continue
            
            conn.close()
            print(f"✅ Manual daily check completed - processed {checked_count} vehicles")
            
            # Now test the actual scheduler method
            print("\n--- Testing Scheduler Daily Check Method ---")
            try:
                scheduler._daily_morning_status_check()
                print("✅ Scheduler daily check completed successfully")
            except Exception as e:
                print(f"❌ Scheduler daily check failed: {e}")
                import traceback
                traceback.print_exc()
            
            print("\n" + "=" * 60)
            print("✅ ISOLATED TEST COMPLETED")
            print("=" * 60)
            
            return True
            
    except Exception as e:
        print(f"❌ Isolated test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_daily_check_isolated()
    sys.exit(0 if success else 1)
