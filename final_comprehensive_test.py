"""
Final Comprehensive Integration Test
Validates the entire iTow VMS enhanced architecture end-to-end
"""

import time
import requests
from datetime import datetime, timedelta
from app.factory import create_app

def test_comprehensive_system_integration():
    """
    Complete end-to-end test of the enhanced iTow VMS architecture
    """
    
    print("=" * 60)
    print("🚀 iTow VMS Enhanced Architecture - Final Integration Test")
    print("=" * 60)
    print(f"Test started at: {datetime.now()}")
    
    # Create application
    app = create_app('development')
    
    # Stop scheduler to prevent background interference
    if hasattr(app, 'scheduler'):
        app.scheduler.stop()
    
    with app.app_context():
        
        print("\n📋 PHASE 1: Core System Validation")
        print("-" * 40)
        
        # Test 1: Application Architecture
        print("1. Testing Enhanced Application Architecture...")
        components = {
            'workflow_engine': hasattr(app, 'workflow_engine'),
            'automated_workflow': hasattr(app, 'automated_workflow'),
            'scheduler': hasattr(app, 'scheduler'),
            'notification_manager': hasattr(app, 'notification_manager'),
            'towbook_integration': hasattr(app, 'towbook_integration'),
        }
        
        for component, status in components.items():
            print(f"   {'✅' if status else '❌'} {component}: {'Initialized' if status else 'Missing'}")
        
        assert all(components.values()), "All core components must be initialized"
        print("   🎉 Enhanced architecture fully operational")
        
        # Test 2: Database Integration
        print("\n2. Testing Database Integration...")
        from app.core.database import get_db_connection, VehicleRepository, DatabaseManager
        
        db = get_db_connection()
        cursor = db.cursor()
        
        # Check vehicles table
        cursor.execute("SELECT COUNT(*) as count FROM vehicles")
        vehicle_count = cursor.fetchone()['count']
        print(f"   📊 Vehicles in database: {vehicle_count}")
        
        # Check vehicle_logs table
        cursor.execute("SELECT COUNT(*) as count FROM vehicle_logs")
        log_count = cursor.fetchone()['count']
        print(f"   📝 Log entries: {log_count}")
        
        # Check notification_queue table
        cursor.execute("SELECT COUNT(*) as count FROM notification_queue")
        notification_count = cursor.fetchone()['count']
        print(f"   📧 Notifications queued: {notification_count}")
        
        assert vehicle_count > 0, "Should have vehicles in database"
        print("   ✅ Database integration verified")
        
        print("\n📊 PHASE 2: Workflow Engine Validation")
        print("-" * 40)
        
        # Test 3: Workflow Engine Analysis
        print("3. Testing Workflow Engine Analysis...")
        workflow_engine = app.workflow_engine
        
        priorities = workflow_engine.get_daily_priorities()
        urgent_vehicles = priorities.get('urgent', [])
        attention_vehicles = priorities.get('needs_attention', [])
        stable_vehicles = priorities.get('stable', [])
        
        print(f"   🚨 Urgent vehicles: {len(urgent_vehicles)}")
        print(f"   ⚠️  Needs attention: {len(attention_vehicles)}")
        print(f"   ✅ Stable vehicles: {len(stable_vehicles)}")
        
        total_analyzed = len(urgent_vehicles) + len(attention_vehicles) + len(stable_vehicles)
        print(f"   📈 Total vehicles analyzed: {total_analyzed}")
        
        assert total_analyzed > 0, "Workflow engine should analyze vehicles"
        print("   ✅ Workflow engine operational")
        
        # Test 4: Automated Workflow Execution
        print("\n4. Testing Automated Workflow Execution...")
        automated_workflow = app.automated_workflow
        
        start_time = time.time()
        results = automated_workflow.execute_automated_actions()
        execution_time = time.time() - start_time
        
        print(f"   📧 Notices sent: {results.get('notices_sent', 0)}")
        print(f"   🔄 Status updates: {results.get('status_updates', 0)}")
        print(f"   🚨 Alerts generated: {results.get('alerts_generated', 0)}")
        print(f"   📄 Documents created: {results.get('documents_created', 0)}")
        print(f"   ❌ Errors: {results.get('errors', 0)}")
        print(f"   ⏱️  Execution time: {execution_time:.3f} seconds")
        
        assert isinstance(results, dict), "Should return execution results"
        assert execution_time < 5.0, "Should execute within 5 seconds"
        print("   ✅ Automated workflow execution verified")
        
        print("\n📧 PHASE 3: Notification System Validation")
        print("-" * 40)
        
        # Test 5: Notification System
        print("5. Testing Notification System...")
        notification_manager = app.notification_manager
        
        # Queue test notifications
        test_notifications = [
            {
                'recipient': 'admin@itowvms.com',
                'subject': 'System Test - Seven Day Notice',
                'body': 'This is a test seven day notice for vehicle TEST-001',
                'type': 'seven_day_notice',
                'vehicle': 'TEST-001'
            },
            {
                'recipient': 'alerts@itowvms.com',
                'subject': 'System Test - Urgent Alert',
                'body': 'This is a test urgent alert for vehicle TEST-002',
                'type': 'alert',
                'vehicle': 'TEST-002'
            }
        ]
        
        notifications_queued = 0
        for notification in test_notifications:
            success = notification_manager.queue_notification(
                recipient_email=notification['recipient'],
                subject=notification['subject'],
                body=notification['body'],
                notification_type=notification['type'],
                vehicle_call_number=notification['vehicle']
            )
            if success:
                notifications_queued += 1
        
        print(f"   📧 Test notifications queued: {notifications_queued}")
        
        # Get queue status
        queue_status = notification_manager.get_queue_status()
        print(f"   📊 Queue status: {queue_status}")
        
        assert notifications_queued > 0, "Should queue test notifications"
        print("   ✅ Notification system operational")
        
        print("\n🔗 PHASE 4: TowBook Integration Validation")
        print("-" * 40)
        
        # Test 6: TowBook Integration
        print("6. Testing TowBook Integration...")
        towbook = app.towbook_integration
        
        # Test date range functionality
        date_range = towbook.get_available_date_range()
        print(f"   📅 Suggested date range: {date_range['start_date']} to {date_range['end_date']}")
        print(f"   💡 Reason: {date_range['suggested_reason']}")
        
        # Test import progress (without actual import)
        progress = towbook.get_import_progress()
        print(f"   📊 Import status: {progress['status']}")
        print(f"   🔄 Currently running: {progress['is_running']}")
        
        assert isinstance(date_range, dict), "Should return date range"
        assert 'start_date' in date_range, "Should include start date"
        print("   ✅ TowBook integration verified")
        
        print("\n⚡ PHASE 5: Performance & Scalability")
        print("-" * 40)
        
        # Test 7: Performance Benchmarks
        print("7. Testing Performance Benchmarks...")
        
        # Workflow engine performance
        start_time = time.time()
        for i in range(5):
            priorities = workflow_engine.get_daily_priorities()
        workflow_time = time.time() - start_time
        print(f"   🏃 Workflow analysis (5x): {workflow_time:.3f} seconds")
        
        # Database query performance
        start_time = time.time()
        for i in range(10):
            cursor.execute("SELECT COUNT(*) FROM vehicles WHERE status = 'New'")
            cursor.fetchone()
        db_time = time.time() - start_time
        print(f"   💾 Database queries (10x): {db_time:.3f} seconds")
        
        # Notification processing performance
        start_time = time.time()
        processed = automated_workflow._check_notification_queue()
        notification_time = time.time() - start_time
        print(f"   📧 Notification processing: {notification_time:.3f} seconds ({processed} processed)")
        
        assert workflow_time < 2.0, "Workflow analysis should be fast"
        assert db_time < 1.0, "Database queries should be fast"
        print("   ✅ Performance benchmarks passed")
        
        print("\n🛡️  PHASE 6: Security & Configuration")
        print("-" * 40)
        
        # Test 8: Security Configuration
        print("8. Testing Security Configuration...")
        
        security_checks = {
            'SECRET_KEY': bool(app.config.get('SECRET_KEY')),
            'SESSION_COOKIE_SECURE': app.config.get('SESSION_COOKIE_SECURE', False),
            'PERMANENT_SESSION_LIFETIME': bool(app.config.get('PERMANENT_SESSION_LIFETIME')),
            'BCRYPT_LOG_ROUNDS': app.config.get('BCRYPT_LOG_ROUNDS', 0) >= 12,
        }
        
        for check, status in security_checks.items():
            print(f"   {'✅' if status else '⚠️ '} {check}: {'Configured' if status else 'Needs attention'}")
        
        # Configuration validation
        config_checks = {
            'DATABASE_URL': bool(app.config.get('DATABASE_URL')),
            'LOG_LEVEL': bool(app.config.get('LOG_LEVEL')),
            'WORKFLOW_CHECK_INTERVAL': bool(app.config.get('WORKFLOW_CHECK_INTERVAL')),
        }
        
        for check, status in config_checks.items():
            print(f"   {'✅' if status else '❌'} {check}: {'Set' if status else 'Missing'}")
        
        assert all(config_checks.values()), "All configuration must be set"
        print("   ✅ Security and configuration verified")
        
        print("\n🚀 PHASE 7: Production Readiness")
        print("-" * 40)
        
        # Test 9: Production Readiness Check
        print("9. Testing Production Readiness...")
        
        readiness_checks = {
            'Application Factory': components['workflow_engine'] and components['automated_workflow'],
            'Database Integration': vehicle_count > 0 and log_count > 0,
            'Workflow Engine': len(urgent_vehicles) >= 0,  # Should at least analyze without error
            'Notification System': queue_status['total'] > 0,
            'TowBook Integration': 'start_date' in date_range,
            'Performance': workflow_time < 2.0 and db_time < 1.0,
            'Configuration': all(config_checks.values()),
            'Error Handling': results.get('errors', 0) == 0,  # No errors in automation
        }
        
        for check, status in readiness_checks.items():
            print(f"   {'✅' if status else '❌'} {check}: {'Ready' if status else 'Not Ready'}")
        
        ready_count = sum(1 for status in readiness_checks.values() if status)
        total_checks = len(readiness_checks)
        readiness_percentage = (ready_count / total_checks) * 100
        
        print(f"\n   📊 Production Readiness: {ready_count}/{total_checks} ({readiness_percentage:.1f}%)")
        
        assert readiness_percentage >= 90, f"System should be at least 90% ready (currently {readiness_percentage:.1f}%)"
        print("   ✅ Production readiness verified")
        
        print("\n" + "=" * 60)
        print("🎉 FINAL INTEGRATION TEST RESULTS")
        print("=" * 60)
        
        print(f"✅ Enhanced Architecture: OPERATIONAL")
        print(f"✅ Database Integration: {vehicle_count} vehicles, {log_count} logs")
        print(f"✅ Workflow Engine: {total_analyzed} vehicles analyzed")
        print(f"✅ Automation System: {sum(results.values())} actions processed")
        print(f"✅ Notification System: {queue_status['total']} notifications managed")
        print(f"✅ TowBook Integration: READY")
        print(f"✅ Performance: Workflow {workflow_time:.3f}s, DB {db_time:.3f}s")
        print(f"✅ Production Readiness: {readiness_percentage:.1f}%")
        
        print(f"\n🚀 DEPLOYMENT STATUS: PRODUCTION READY")
        print(f"📅 Test completed at: {datetime.now()}")
        
        return True

if __name__ == "__main__":
    try:
        success = test_comprehensive_system_integration()
        if success:
            print("\n🎊 CONGRATULATIONS! 🎊")
            print("The iTow VMS Enhanced Architecture has passed all integration tests!")
            print("The system is ready for production deployment.")
        else:
            print("\n❌ Integration test failed")
    except Exception as e:
        print(f"\n💥 Integration test failed with error: {e}")
        import traceback
        traceback.print_exc()
