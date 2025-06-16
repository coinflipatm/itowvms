#!/usr/bin/env python3
import sqlite3

# Database path
db_path = '/workspaces/itowvms/vehicles.db'

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get column info
    cursor.execute("PRAGMA table_info(vehicles);")
    columns = cursor.fetchall()
    
    print("All columns in vehicles table:")
    year_cols = []
    for col in columns:
        col_name = col[1]
        col_type = col[2]
        print(f"  {col_name} ({col_type})")
        if 'year' in col_name.lower():
            year_cols.append(col_name)
    
    print(f"\nYear-related columns: {year_cols}")
    
    conn.close()
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
