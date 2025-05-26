#!/usr/bin/env python3
"""
Test script to verify that vehicles are now correctly accessible after fixing archived field.
"""

import sqlite3
import json

def test_vehicle_visibility():
    """Test that vehicles are now properly visible in the correct tabs"""
    try:
        print("Testing vehicle visibility after archived field fix...")
        
        conn = sqlite3.connect('vehicles.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Test 1: Count active vehicles (should appear in active tab)
        active_statuses = ['New', 'TOP Generated', 'TR52 Ready', 'TR208 Ready', 'Ready for Auction', 'Ready for Scrap']
        active_statuses_str = "', '".join(active_statuses)
        
        cursor.execute(f"""
            SELECT COUNT(*) as count 
            FROM vehicles 
            WHERE status IN ('{active_statuses_str}') AND archived = 0
        """)
        active_count = cursor.fetchone()['count']
        print(f"✓ Active vehicles (should appear in frontend active tab): {active_count}")
        
        # Test 2: Count completed vehicles (should appear in completed tab)
        completed_statuses = ['Released', 'Auctioned', 'Scrapped', 'Transferred']
        completed_statuses_str = "', '".join(completed_statuses)
        
        cursor.execute(f"""
            SELECT COUNT(*) as count 
            FROM vehicles 
            WHERE status IN ('{completed_statuses_str}') AND archived = 1
        """)
        completed_count = cursor.fetchone()['count']
        print(f"✓ Completed vehicles (should appear in frontend completed tab): {completed_count}")
        
        # Test 3: Show breakdown by status
        print("\nDetailed breakdown:")
        cursor.execute("""
            SELECT status, archived, COUNT(*) as count
            FROM vehicles 
            GROUP BY status, archived
            ORDER BY status, archived
        """)
        
        for row in cursor.fetchall():
            tab = "ACTIVE" if row['status'] in active_statuses and row['archived'] == 0 else \
                  "COMPLETED" if row['status'] in completed_statuses and row['archived'] == 1 else \
                  "HIDDEN"
            print(f"  Status: {row['status']:<15} Archived: {row['archived']} Count: {row['count']:<3} → {tab} tab")
        
        # Test 4: Check for any problematic vehicles
        cursor.execute(f"""
            SELECT COUNT(*) as count
            FROM vehicles 
            WHERE (status IN ('{active_statuses_str}') AND archived = 1) 
               OR (status IN ('{completed_statuses_str}') AND archived = 0)
        """)
        problematic_count = cursor.fetchone()['count']
        
        if problematic_count > 0:
            print(f"\n⚠️  WARNING: {problematic_count} vehicles have inconsistent archived status!")
        else:
            print(f"\n✓ All vehicles have correct archived status!")
        
        # Test 5: Simulate API query for active vehicles
        cursor.execute(f"""
            SELECT towbook_call_number, status, archived, tow_date
            FROM vehicles 
            WHERE status IN ('{active_statuses_str}') AND archived = 0
            ORDER BY last_updated DESC
            LIMIT 5
        """)
        
        print(f"\nSample active vehicles that should appear in frontend:")
        for row in cursor.fetchall():
            print(f"  Call#: {row['towbook_call_number']} | Status: {row['status']} | Tow Date: {row['tow_date']}")
        
        conn.close()
        
        # Summary
        print(f"\n" + "="*60)
        print(f"SUMMARY:")
        print(f"✓ Active vehicles ready for frontend: {active_count}")
        print(f"✓ Completed vehicles ready for frontend: {completed_count}")
        print(f"✓ Archived field fix: {'SUCCESS' if problematic_count == 0 else 'PARTIAL'}")
        print(f"="*60)
        
        return active_count > 0
        
    except Exception as e:
        print(f"Error testing vehicle visibility: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_vehicle_visibility()
    if success:
        print("\n🎉 Vehicles should now appear correctly in the iTow VMS frontend!")
    else:
        print("\n❌ Issues detected - vehicles may not appear correctly in frontend")
