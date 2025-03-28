# fix_status_values.py
import sqlite3

def fix_status_values():
    """Fix incorrect status values in the database"""
    conn = sqlite3.connect('vehicles.db')
    cursor = conn.cursor()
    
    # Status mapping (current -> correct)
    status_fixes = {
        'Paperwork': 'Paperwork Received',
        'TOP Sent': 'TOP Generated',
        'TOP_Sent': 'TOP Generated'
    }
    
    # Apply each status fix
    for old_status, new_status in status_fixes.items():
        count_before = cursor.execute("SELECT COUNT(*) FROM vehicles WHERE status = ?", 
                                    (old_status,)).fetchone()[0]
        
        if count_before > 0:
            cursor.execute("UPDATE vehicles SET status = ? WHERE status = ?", 
                         (new_status, old_status))
            print(f"Updated {count_before} vehicles: '{old_status}' → '{new_status}'")
    
    # Commit changes
    conn.commit()
    
    # Verify results
    cursor.execute("SELECT status, COUNT(*) FROM vehicles GROUP BY status")
    print("\nStatus counts after fix:")
    for status, count in cursor.fetchall():
        print(f"  {status}: {count}")
    
    conn.close()

if __name__ == "__main__":
    fix_status_values()