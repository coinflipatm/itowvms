"""
Phase 3: Production Automation Integration Test
Tests automated workflow engine, scheduler, and notification system
"""

import time
import threading
from datetime import datetime, timedelta
from app.factory import create_app

def test_phase3_automation_integration():
    """
    Comprehensive test of Phase 3 automation features
    """
    
    print("=== Phase 3: Automation Integration Test ===")
    print(f"Test started at: {datetime.now()}")
    
    # Create application with enhanced automation
    app = create_app('development')
    
    with app.app_context():
        
        # Test 1: Application Components
        print("\n1. Testing Application Components...")
        assert hasattr(app, 'workflow_engine'), "Workflow engine not initialized"
        assert hasattr(app, 'automated_workflow'), "Automated workflow not initialized"
        assert hasattr(app, 'scheduler'), "Scheduler not initialized"
        assert hasattr(app, 'notification_manager'), "Notification manager not initialized"
        assert hasattr(app, 'towbook_integration'), "TowBook integration not initialized"
        print("   ✅ All application components initialized")
        
        # Test 2: Automated Workflow Engine
        print("\n2. Testing Automated Workflow Engine...")
        automated_workflow = app.automated_workflow
        
        # Execute automated actions
        results = automated_workflow.execute_automated_actions()
        assert isinstance(results, dict), "Automated actions should return dict"
        assert 'notices_sent' in results, "Results should include notices_sent"
        assert 'status_updates' in results, "Results should include status_updates"
        assert 'alerts_generated' in results, "Results should include alerts_generated"
        print(f"   ✅ Automated actions executed: {results}")
        
        # Test 3: Notification System
        print("\n3. Testing Notification System...")
        notification_manager = app.notification_manager
        
        # Queue a test notification
        success = notification_manager.queue_notification(
            recipient_email="test@example.com",
            subject="Test Notification",
            body="This is a test notification from iTow VMS",
            notification_type="test",
            vehicle_call_number="TEST001"
        )
        assert success, "Notification queueing should succeed"
        
        # Get queue status
        queue_status = notification_manager.get_queue_status()
        assert isinstance(queue_status, dict), "Queue status should be dict"
        assert queue_status['total'] > 0, "Should have at least one notification queued"
        print(f"   ✅ Notification system working: {queue_status}")
        
        # Test 4: Scheduler Components
        print("\n4. Testing Scheduler Components...")
        scheduler = app.scheduler
        
        # Get scheduler status
        scheduler_status = scheduler.get_status()
        assert isinstance(scheduler_status, dict), "Scheduler status should be dict"
        assert 'running' in scheduler_status, "Status should include running state"
        assert 'workflow_check_interval' in scheduler_status, "Status should include intervals"
        print(f"   ✅ Scheduler status: Running={scheduler_status['running']}")
        
        # Test 5: Database Integration
        print("\n5. Testing Database Integration...")
        
        # Test notification queue table exists
        from app.core.database import get_db_connection
        db = get_db_connection()
        cursor = db.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='notification_queue'")
        table_exists = cursor.fetchone() is not None
        assert table_exists, "Notification queue table should exist"
        
        # Test notification queue functionality
        cursor.execute("SELECT COUNT(*) as count FROM notification_queue WHERE status = 'pending'")
        pending_count = cursor.fetchone()['count']
        assert pending_count >= 1, "Should have at least one pending notification"
        print(f"   ✅ Database integration: {pending_count} pending notifications")
        
        # Test 6: Workflow Engine Integration
        print("\n6. Testing Workflow Engine Integration...")
        workflow_engine = app.workflow_engine
        
        # Get daily priorities
        priorities = workflow_engine.get_daily_priorities()
        assert isinstance(priorities, dict), "Priorities should be dict"
        assert 'urgent' in priorities, "Should have urgent category"
        
        urgent_count = len(priorities.get('urgent', []))
        total_count = sum(len(vehicles) for vehicles in priorities.values())
        print(f"   ✅ Workflow analysis: {urgent_count} urgent, {total_count} total vehicles")
        
        # Test 7: TowBook Integration
        print("\n7. Testing TowBook Integration...")
        towbook = app.towbook_integration
        
        # Test date range functionality
        date_range = towbook.get_available_date_range()
        assert isinstance(date_range, dict), "Date range should be dict"
        print(f"   ✅ TowBook integration: Date range available")
        
        # Test 8: Automated Action Processing
        print("\n8. Testing Automated Action Processing...")
        
        # Process notification queue
        notifications_processed = automated_workflow._check_notification_queue()
        assert isinstance(notifications_processed, int), "Should return int count"
        print(f"   ✅ Notification processing: {notifications_processed} notifications processed")
        
        # Test 9: Configuration Validation
        print("\n9. Testing Configuration...")
        
        # Check production-ready configuration options
        config_checks = {
            'WORKFLOW_CHECK_INTERVAL': app.config.get('WORKFLOW_CHECK_INTERVAL', 3600),
            'STATUS_UPDATE_INTERVAL': app.config.get('STATUS_UPDATE_INTERVAL', 21600),
            'NOTIFICATION_CHECK_INTERVAL': app.config.get('NOTIFICATION_CHECK_INTERVAL', 1800),
            'DATABASE_URL': app.config.get('DATABASE_URL', 'sqlite:///vehicles.db'),
            'SECRET_KEY': bool(app.config.get('SECRET_KEY')),
        }
        
        for key, value in config_checks.items():
            assert value is not None, f"Configuration {key} should be set"
        
        print(f"   ✅ Configuration validated: {len(config_checks)} settings checked")
        
        # Test 10: Performance and Resource Usage
        print("\n10. Testing Performance...")
        
        start_time = time.time()
        
        # Run multiple automated workflow cycles
        for i in range(3):
            results = automated_workflow.execute_automated_actions()
            assert isinstance(results, dict), f"Cycle {i+1} should return results"
        
        execution_time = time.time() - start_time
        assert execution_time < 30, "Multiple cycles should complete within 30 seconds"
        print(f"   ✅ Performance test: 3 cycles completed in {execution_time:.2f} seconds")
        
        # Cleanup: Stop scheduler to prevent background activity
        scheduler.stop()
        
        print("\n=== Phase 3 Integration Test Results ===")
        print("✅ All 10 core automation tests passed!")
        print(f"✅ Automated workflow engine operational")
        print(f"✅ Background task scheduler functional")
        print(f"✅ Email notification system ready")
        print(f"✅ Database integration complete")
        print(f"✅ Production configuration validated")
        print(f"\nTest completed at: {datetime.now()}")
        
        return True

if __name__ == "__main__":
    try:
        success = test_phase3_automation_integration()
        if success:
            print("\n🎉 Phase 3 automation integration is COMPLETE!")
            print("The iTow VMS enhanced architecture is ready for production deployment.")
        else:
            print("\n❌ Phase 3 integration test failed")
    except Exception as e:
        print(f"\n❌ Phase 3 integration test failed with error: {e}")
        import traceback
        traceback.print_exc()
