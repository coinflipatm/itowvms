from datetime import datetime
import sqlite3
import logging

def get_progress_mock():
    return {'percentage': 50, 'is_running': True}

def update_vehicle_status(call_number, status, fields=None):
    """Update a vehicle's status and additional fields"""
    try:
        conn = sqlite3.connect('vehicles.db')
        cursor = conn.cursor()
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        if fields:
            set_clause = ', '.join([f"{k} = ?" for k in fields.keys()])
            values = list(fields.values()) + [status, current_time, call_number]
            
            cursor.execute(f'''
                UPDATE vehicles SET {set_clause}, status = ?, last_updated = ?
                WHERE towbook_call_number = ?
            ''', values)
        else:
            cursor.execute('''
                UPDATE vehicles SET status = ?, last_updated = ?
                WHERE towbook_call_number = ?
            ''', (status, current_time, call_number))
            
        conn.commit()
        conn.close()
        
        # Try to log the action
        try:
            log_action("STATUS_CHANGE", call_number, f"Changed status to {status}")
        except:
            # If logging fails, continue anyway
            pass
            
        return True
    except Exception as e:
        logging.error(f"Error updating vehicle status: {e}")
        return False

def generate_invoice_number():
    """Generate an invoice number in the format ITXXXX-YY starting from current sequence"""
    conn = sqlite3.connect('vehicles.db')
    cursor = conn.cursor()
    
    # Get current year
    current_year = datetime.now().strftime('%y')
    
    # Find the highest existing invoice number for this year
    cursor.execute("""
        SELECT invoice_number FROM vehicles 
        WHERE invoice_number LIKE ? 
        ORDER BY invoice_number DESC LIMIT 1
    """, (f'IT%-{current_year}',))
    
    result = cursor.fetchone()
    
    if result and result[0]:
        # Extract the sequence number from existing invoice
        try:
            current_sequence = int(result[0].split('-')[0].replace('IT', ''))
            next_sequence = current_sequence + 1
        except:
            # If parsing fails, start from 90 (current position)
            next_sequence = 90
    else:
        # First invoice of the year
        next_sequence = 1
    
    conn.close()
    
    # Format: ITXXXX-YY (e.g., IT0090-25)
    invoice_number = f"IT{next_sequence:04d}-{current_year}"
    
    return invoice_number, next_sequence, current_year

def ensure_logs_table_exists():
    """Ensure logs table exists before attempting to log actions"""
    try:
        conn = sqlite3.connect('vehicles.db')
        cursor = conn.cursor()
        
        # Create logs table if it doesn't exist
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action_type TEXT,
                vehicle_id TEXT,
                details TEXT,
                timestamp TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
    except Exception as e:
        logging.error(f"Failed to ensure logs table exists: {e}")

def log_action(action_type, vehicle_id, details):
    """Log an action with better error handling"""
    try:
        # Make sure logs table exists
        ensure_logs_table_exists()
        
        conn = sqlite3.connect('vehicles.db')
        cursor = conn.cursor()
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        cursor.execute(
            "INSERT INTO logs (action_type, vehicle_id, details, timestamp) VALUES (?, ?, ?, ?)",
            (action_type, vehicle_id, details, timestamp)
        )
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logging.error(f"Failed to log action: {e}")
        return False

def release_vehicle(call_number, reason, recipient=None, release_date=None):
    """Mark a vehicle as released and archive it"""
    fields = {
        'release_reason': reason,
        'release_date': release_date or datetime.now().strftime('%Y-%m-%d'),
        'release_time': datetime.now().strftime('%H:%M:%S'),
        'archived': 1
    }
    
    if recipient:
        fields['recipient'] = recipient
        
    success = update_vehicle_status(call_number, 'Released', fields)
    
    if success:
        try:
            log_action('RELEASE', call_number, f"Released with reason: {reason}, to: {recipient}, on: {fields['release_date']}")
        except:
            # If logging fails, continue anyway
            pass
    
    return success