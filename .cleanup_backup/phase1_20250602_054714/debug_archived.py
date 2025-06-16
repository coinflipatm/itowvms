import sqlite3

try:
    print("Checking archived field impact...")
    
    conn = sqlite3.connect('vehicles.db')
    cursor = conn.cursor()
    
    # Check active vehicles that are not archived
    cursor.execute("SELECT status, archived, COUNT(*) FROM vehicles WHERE status IN ('New', 'TOP Generated', 'TR52 Ready') GROUP BY status, archived ORDER BY status, archived")
    results = cursor.fetchall()
    print('Active vehicles by status and archived flag:')
    for row in results:
        print(f'  Status: {row[0]}, Archived: {row[1]}, Count: {row[2]}')
    
    # Check what the frontend should see (non-archived active vehicles)
    cursor.execute("SELECT COUNT(*) FROM vehicles WHERE status IN ('New', 'TOP Generated', 'TR52 Ready') AND archived = 0")
    non_archived_active = cursor.fetchone()[0]
    print(f'Non-archived active vehicles: {non_archived_active}')
    
    conn.close()
    print("Check complete")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
