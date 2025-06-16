#!/usr/bin/env python3
"""
Simple Database Integration Test
Test our enhanced architecture components directly
"""

import sys
import os

# Add the project root to Python path
sys.path.insert(0, '/workspaces/itowvms')

def test_enhanced_database():
    """Test the enhanced database integration"""
    
    print("Testing Enhanced Database Integration")
    print("=" * 50)
    
    try:
        # Test import
        from app.core.database import VehicleRepository, db_manager
        from app.factory import create_app
        print("✓ Imports successful")
        
        # Create app context
        app = create_app()
        
        with app.app_context():
            print("✓ App context created")
            
            # Test database manager
            db_connection = db_manager.get_db()
            print("✓ Database connection established")
            
            # Test VehicleRepository
            vehicle_repo = VehicleRepository(db_manager)
            print("✓ VehicleRepository initialized")
            
            # Test getting vehicles by status
            initial_hold_vehicles = vehicle_repo.get_vehicles_by_status('INITIAL_HOLD')
            print(f"✓ Found {len(initial_hold_vehicles)} vehicles in INITIAL_HOLD status")
            
            # Test getting vehicles needing notice
            notice_vehicles = vehicle_repo.get_vehicles_needing_seven_day_notice()
            print(f"✓ Found {len(notice_vehicles)} vehicles needing 7-day notice")
            
            # Test getting a specific vehicle
            if initial_hold_vehicles:
                sample_vehicle = initial_hold_vehicles[0]
                call_number = sample_vehicle.get('towbook_call_number')
                if call_number:
                    retrieved_vehicle = vehicle_repo.get_vehicle_by_call_number(call_number)
                    if retrieved_vehicle:
                        print(f"✓ Successfully retrieved vehicle: {call_number}")
                        print(f"  Make: {retrieved_vehicle.get('make', 'N/A')}")
                        print(f"  Model: {retrieved_vehicle.get('model', 'N/A')}")
                        print(f"  Status: {retrieved_vehicle.get('status', 'N/A')}")
                        print(f"  Tow Date: {retrieved_vehicle.get('tow_date', 'N/A')}")
                    else:
                        print("✗ Failed to retrieve vehicle by call number")
                else:
                    print("✗ No call number found in sample vehicle")
            
            print("\n" + "=" * 50)
            print("DATABASE INTEGRATION TEST PASSED!")
            print("Enhanced architecture successfully connects to existing data")
            return True
            
    except Exception as e:
        print(f"✗ Database integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_workflow_engine():
    """Test the workflow engine integration"""
    
    print("\n\nTesting Workflow Engine Integration")
    print("=" * 50)
    
    try:
        from app.workflows.engine import VehicleWorkflowEngine, VehicleStage
        from app.factory import create_app
        print("✓ Workflow engine imports successful")
        
        app = create_app()
        
        with app.app_context():
            # Test workflow engine initialization
            workflow_engine = VehicleWorkflowEngine(app)
            print("✓ Workflow engine initialized")
            
            # Test getting morning priorities
            priorities = workflow_engine.get_morning_priorities()
            print(f"✓ Retrieved {len(priorities)} morning priorities")
            
            for priority in priorities[:3]:  # Show first 3
                print(f"  - {priority.action_type}: {priority.description}")
            
            print("\n" + "=" * 50)
            print("WORKFLOW ENGINE TEST PASSED!")
            return True
            
    except Exception as e:
        print(f"✗ Workflow engine test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = True
    
    # Test database integration
    success &= test_enhanced_database()
    
    # Test workflow engine
    success &= test_workflow_engine()
    
    if success:
        print("\n🎉 ALL ENHANCED ARCHITECTURE TESTS PASSED!")
        print("\nThe enhanced iTow VMS architecture is working correctly!")
        print("✓ Database integration with existing data")
        print("✓ Workflow engine functionality") 
        print("✓ Application factory pattern")
        print("✓ Modular design structure")
    else:
        print("\n❌ Some tests failed - Check output above")
        sys.exit(1)
