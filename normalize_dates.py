#!/usr/bin/env python3
"""
Database Date Normalization Script

This script normalizes all tow dates in the vehicles.db database to YYYY-MM-DD format.
It handles the mixed formats found in the database (YYYY-MM-DD and MM/DD/YYYY).
"""

import sqlite3
import logging
from datetime import datetime
import re

def setup_logging():
    """Setup logging for the normalization process"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('date_normalization.log'),
            logging.StreamHandler()
        ]
    )

def parse_date_flexible(date_str):
    """
    Parse date string with flexible format handling
    
    Args:
        date_str (str): Date string in various formats
        
    Returns:
        str: Date in YYYY-MM-DD format or None if invalid
    """
    if not date_str or date_str.strip() == '' or date_str == 'N/A':
        return None
    
    date_str = date_str.strip()
    
    # Try YYYY-MM-DD format first (already correct)
    if re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
        try:
            datetime.strptime(date_str, '%Y-%m-%d')
            return date_str  # Already in correct format
        except ValueError:
            pass
    
    # Try MM/DD/YYYY format
    if re.match(r'^\d{1,2}/\d{1,2}/\d{4}$', date_str):
        try:
            parsed_date = datetime.strptime(date_str, '%m/%d/%Y')
            return parsed_date.strftime('%Y-%m-%d')
        except ValueError:
            pass
    
    # Try M/D/YYYY format (single digits)
    if re.match(r'^\d{1,2}/\d{1,2}/\d{4}$', date_str):
        try:
            # Handle cases like 1/5/2024
            parts = date_str.split('/')
            if len(parts) == 3:
                month, day, year = parts
                parsed_date = datetime(int(year), int(month), int(day))
                return parsed_date.strftime('%Y-%m-%d')
        except (ValueError, IndexError):
            pass
    
    # Try MM-DD-YYYY format (with hyphens)
    if re.match(r'^\d{1,2}-\d{1,2}-\d{4}$', date_str):
        try:
            parsed_date = datetime.strptime(date_str, '%m-%d-%Y')
            return parsed_date.strftime('%Y-%m-%d')
        except ValueError:
            pass
    
    logging.warning(f"Could not parse date: '{date_str}'")
    return None

def normalize_database_dates():
    """Normalize all dates in the vehicles database"""
    try:
        # Connect to the database
        conn = sqlite3.connect('vehicles.db')
        cursor = conn.cursor()
        
        # Get all records with tow_date
        cursor.execute("SELECT towbook_call_number, tow_date FROM vehicles WHERE tow_date IS NOT NULL AND tow_date != 'N/A'")
        records = cursor.fetchall()
        
        logging.info(f"Found {len(records)} records with tow dates to process")
        
        updated_count = 0
        skipped_count = 0
        error_count = 0
        
        for call_number, tow_date in records:
            normalized_date = parse_date_flexible(tow_date)
            
            if normalized_date is None:
                logging.error(f"Call Number {call_number}: Could not normalize date '{tow_date}'")
                error_count += 1
                continue
            
            if normalized_date == tow_date:
                logging.debug(f"Call Number {call_number}: Date already normalized: {tow_date}")
                skipped_count += 1
                continue
            
            # Update the record
            cursor.execute("UPDATE vehicles SET tow_date = ? WHERE towbook_call_number = ?", (normalized_date, call_number))
            logging.info(f"Call Number {call_number}: Normalized '{tow_date}' -> '{normalized_date}'")
            updated_count += 1
        
        # Commit changes
        conn.commit()
        
        # Log summary
        logging.info(f"Date normalization complete:")
        logging.info(f"  - Updated: {updated_count} records")
        logging.info(f"  - Skipped (already normalized): {skipped_count} records")
        logging.info(f"  - Errors: {error_count} records")
        
        # Verify the changes
        cursor.execute("SELECT DISTINCT tow_date FROM vehicles WHERE tow_date IS NOT NULL AND tow_date != 'N/A' ORDER BY tow_date")
        unique_dates = cursor.fetchall()
        
        logging.info("\nUnique date formats after normalization:")
        for date_tuple in unique_dates[:10]:  # Show first 10 as sample
            logging.info(f"  {date_tuple[0]}")
        
        if len(unique_dates) > 10:
            logging.info(f"  ... and {len(unique_dates) - 10} more")
        
        conn.close()
        
        return updated_count, skipped_count, error_count
        
    except Exception as e:
        logging.error(f"Error during date normalization: {e}")
        raise

def verify_date_consistency():
    """Verify all dates are in YYYY-MM-DD format"""
    try:
        conn = sqlite3.connect('vehicles.db')
        cursor = conn.cursor()
        
        # Check for non-standard date formats
        cursor.execute("""
            SELECT towbook_call_number, tow_date 
            FROM vehicles 
            WHERE tow_date IS NOT NULL 
            AND tow_date != 'N/A' 
            AND tow_date NOT LIKE '____-__-__'
        """)
        
        non_standard = cursor.fetchall()
        
        if non_standard:
            logging.warning(f"Found {len(non_standard)} records with non-standard date formats:")
            for call_number, tow_date in non_standard:
                logging.warning(f"  Call Number {call_number}: '{tow_date}'")
            return False
        else:
            logging.info("All dates are in YYYY-MM-DD format!")
            return True
            
    except Exception as e:
        logging.error(f"Error during verification: {e}")
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    setup_logging()
    
    logging.info("Starting database date normalization...")
    
    try:
        updated, skipped, errors = normalize_database_dates()
        
        logging.info("\nVerifying date consistency...")
        if verify_date_consistency():
            logging.info("✅ Date normalization completed successfully!")
        else:
            logging.warning("⚠️  Some dates may still need manual review")
            
    except Exception as e:
        logging.error(f"❌ Date normalization failed: {e}")
