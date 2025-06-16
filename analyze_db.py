#!/usr/bin/env python3
"""
Database Analysis Script
Analyze the existing database structure for migration
"""

import sqlite3
import sys

def analyze_database(db_path):
    """Analyze database structure"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        
        print(f"Database: {db_path}")
        print(f"Tables found: {len(tables)}")
        print("-" * 50)
        
        for table_name, in tables:
            print(f"\nTable: {table_name}")
            
            # Get column info
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            
            print("Columns:")
            for col in columns:
                cid, name, col_type, notnull, default, pk = col
                print(f"  {name} ({col_type}) {'PRIMARY KEY' if pk else ''}")
            
            # Get row count
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            print(f"Row count: {count}")
            
            # If it's the vehicles table, show a sample
            if table_name == 'vehicles' and count > 0:
                print("\nSample data:")
                cursor.execute(f"SELECT * FROM {table_name} LIMIT 3")
                rows = cursor.fetchall()
                for row in rows:
                    print(f"  {row[:5]}...")  # First 5 columns
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"Error analyzing database {db_path}: {e}")
        return False

if __name__ == "__main__":
    # Analyze both databases
    for db_file in ['vehicles.db', 'database.db']:
        analyze_database(db_file)
        print("\n" + "="*60 + "\n")
