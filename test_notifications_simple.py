"""
Simple notification test
"""

import os
import sys
import time
from app.factory import create_app

def test_notifications():
    print("Creating app...")
    app = create_app('development')
    
    # Stop scheduler immediately
    if hasattr(app, 'scheduler'):
        app.scheduler.stop()
    
    with app.app_context():
        print("Testing notification manager...")
        nm = app.notification_manager
        print(f"Notification manager type: {type(nm)}")
        
        # Test table creation
        print("Creating notification table...")
        nm._create_notification_table()
        
        # Test queueing
        print("Queueing notification...")
        try:
            success = nm.queue_notification(
                recipient_email='test@example.com',
                subject='Test Subject',
                body='Test Body',
                notification_type='test'
            )
            print(f"Queue success: {success}")
        except Exception as e:
            print(f"Queue error: {e}")
            import traceback
            traceback.print_exc()
            success = False
        
        if success:
            status = nm.get_queue_status()
            print(f"Queue status: {status}")
        
        return success

if __name__ == "__main__":
    success = test_notifications()
    print(f"Test result: {success}")
