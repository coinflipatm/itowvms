#!/usr/bin/env python3
"""
Comprehensive Integration Test
Tests the complete enhanced iTow VMS application architecture
"""

import requests
import json
import sys
import os
import sqlite3
import time
from datetime import datetime

def test_web_interface():
    """Test the web interface"""
    base_url = "http://127.0.0.1:5000"
    
    print("="*60)
    print("iTow VMS Enhanced Architecture - Comprehensive Integration Test")
    print("="*60)
    
    # Test 1: Application responding  
    print("\n1. Testing Application Response...")
    try:
        response = requests.get(f"{base_url}/", timeout=10)
        if response.status_code in [200, 302]:
            print("✅ Application responding properly")
        else:
            print(f"❌ Unexpected response: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Application not responding: {e}")
        return False
    
    # Test 2: Login page loads
    print("\n2. Testing Login Page...")
    try:
        response = requests.get(f"{base_url}/login", timeout=10)
        if response.status_code == 200 and "iTow Impound Manager" in response.text:
            print("✅ Login page loads correctly")
        else:
            print(f"❌ Login page issue: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Login page error: {e}")
        return False
    
    # Test 3: API endpoints protection
    print("\n3. Testing API Authentication...")
    try:
        response = requests.get(f"{base_url}/api/vehicles", timeout=10)
        if response.status_code == 401:
            print("✅ API properly protected (401 Unauthorized)")
        else:
            print(f"❌ API authentication issue: {response.status_code}")
    except Exception as e:
        print(f"❌ API test error: {e}")
    
    return True

def test_database_integration():
    """Test database integration"""
    print("\n4. Testing Database Integration...")
    
    try:
        # Test main database
        conn = sqlite3.connect('/workspaces/itowvms/vehicles.db')
        cursor = conn.cursor()
        
        # Check vehicles table
        cursor.execute("SELECT COUNT(*) FROM vehicles")
        vehicle_count = cursor.fetchone()[0]
        print(f"✅ Found {vehicle_count} vehicles in database")
        
        # Check a sample vehicle
        cursor.execute("SELECT towbook_call_number, vin, tow_date FROM vehicles LIMIT 1")
        sample_vehicle = cursor.fetchone()
        if sample_vehicle:
            print(f"✅ Sample vehicle: Call #{sample_vehicle[0]}, VIN: {sample_vehicle[1]}")
        
        # Test logs table
        cursor.execute("SELECT COUNT(*) FROM logs")
        log_count = cursor.fetchone()[0]
        print(f"✅ Found {log_count} log entries")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Database integration error: {e}")
        return False

def test_enhanced_components():
    """Test enhanced architecture components directly"""
    print("\n5. Testing Enhanced Architecture Components...")
    
    try:
        # Import and test the factory
        sys.path.append('/workspaces/itowvms')
        from app.factory import create_app
        from app.core.database import DatabaseManager, VehicleRepository
        
        # Create test app
        app = create_app()
        
        with app.app_context():
            print("✅ Application factory working")
            
            # Test database manager and repository
            db_manager = DatabaseManager(app)
            repo = VehicleRepository(db_manager)
            vehicles = repo.get_vehicles_by_status('New')
            print(f"✅ Vehicle Repository: Found {len(vehicles)} new vehicles")
            
            # Test workflow engine
            if hasattr(app, 'workflow_engine'):
                print("✅ Workflow engine initialized")
            else:
                print("❌ Workflow engine not found")
            
        return True
        
    except Exception as e:
        print(f"❌ Enhanced components error: {e}")
        return False

def test_workflow_functionality():
    """Test workflow engine functionality"""
    print("\n6. Testing Workflow Engine...")
    
    try:
        sys.path.append('/workspaces/itowvms')
        from app.factory import create_app
        
        app = create_app()
        with app.app_context():
            if hasattr(app, 'workflow_engine'):
                engine = app.workflow_engine
                
                # Test daily priorities
                priorities = engine.get_daily_priorities()
                print(f"✅ Daily priorities: {len(priorities)} vehicles need attention")
                
                # Test action evaluation for a real vehicle
                active_vehicles = engine._get_active_vehicles()
                if active_vehicles:
                    test_vehicle = active_vehicles[0]
                    actions = engine.get_next_actions(test_vehicle['towbook_call_number'])
                    print(f"✅ Action engine: {len(actions)} actions needed for test vehicle")
                else:
                    print(f"✅ Action engine: No active vehicles to test")
                
                return True
            else:
                print("❌ Workflow engine not available")
                return False
                
    except Exception as e:
        print(f"❌ Workflow functionality error: {e}")
        return False

def run_comprehensive_test():
    """Run all integration tests"""
    print("Starting comprehensive integration test...")
    print(f"Timestamp: {datetime.now()}")
    
    # Give the application time to start if needed
    time.sleep(2)
    
    results = []
    
    # Run all tests
    results.append(test_web_interface())
    results.append(test_database_integration())
    results.append(test_enhanced_components())
    results.append(test_workflow_functionality())
    
    # Summary
    print("\n" + "="*60)
    print("INTEGRATION TEST SUMMARY")
    print("="*60)
    
    passed = sum(results)
    total = len(results)
    
    print(f"Tests Passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED - Enhanced architecture is ready!")
        print("\nNext Steps:")
        print("- Phase 1 Integration: COMPLETE ✅")
        print("- Phase 2: TowBook Integration")
        print("- Phase 3: Production Deployment")
    else:
        print("❌ Some tests failed - see details above")
    
    return passed == total

if __name__ == '__main__':
    success = run_comprehensive_test()
    sys.exit(0 if success else 1)
