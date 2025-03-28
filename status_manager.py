"""
Status Manager for iTow Impound Manager
Handles status transitions, validation, and side effects
"""
from datetime import datetime, timedelta
import logging
from database import get_db_connection, transaction
from utils import log_action

class StatusTransitionError(Exception):
    """Error raised when an invalid status transition is attempted"""
    pass

class StatusManager:
    """Manages vehicle status transitions and validation"""
    
    # Define allowed transitions
    ALLOWED_TRANSITIONS = {
        'New': ['TOP Generated'],
        'TOP Generated': ['Ready for Disposition'],
        'Ready for Disposition': ['Paperwork Received'],
        'Paperwork Received': ['Ready for Auction', 'Ready for Scrap'],
        'Ready for Auction': ['In Auction'],
        'Ready for Scrap': ['Scrapped'],
        'In Auction': ['Auctioned', 'Released'],
        # Special case: Any status can go to Released
        '_any_': ['Released']
    }
    
    # Status display names
    STATUS_DISPLAY_NAMES = {
        'New': 'New',
        'TOP Generated': 'TOP Sent',
        'Ready for Disposition': 'Ready for Disposition',
        'Paperwork Received': 'Paperwork Received',
        'Ready for Auction': 'Ready for Auction',
        'Ready for Scrap': 'Ready for Scrap',
        'In Auction': 'In Auction',
        'Released': 'Released',
        'Auctioned': 'Auctioned',
        'Scrapped': 'Scrapped'
    }
    
    # Frontend to database status mapping
    FRONTEND_TO_DB_STATUS = {
        'New': 'New',
        'TOP_Sent': 'TOP Generated',
        'Ready': 'Ready for Disposition',
        'Paperwork': 'Paperwork Received',
        'Action': 'Ready for Action',  # Special case, handled separately
        'InAuction': 'In Auction',
        'Completed': 'Released'  # Default completed status
    }
    
    # Database to frontend status mapping
    DB_TO_FRONTEND_STATUS = {
        'New': 'New',
        'TOP Generated': 'TOP_Sent',
        'Ready for Disposition': 'Ready',
        'Paperwork Received': 'Paperwork',
        'Ready for Auction': 'Action',
        'Ready for Scrap': 'Action',
        'In Auction': 'InAuction',
        'Released': 'Completed',
        'Auctioned': 'Completed',
        'Scrapped': 'Completed'
    }
    
    @classmethod
    def get_frontend_status(cls, db_status):
        """Convert database status to frontend status"""
        return cls.DB_TO_FRONTEND_STATUS.get(db_status, db_status)
    
    @classmethod
    def get_db_status(cls, frontend_status):
        """Convert frontend status to database status"""
        return cls.FRONTEND_TO_DB_STATUS.get(frontend_status, frontend_status)
    
    @classmethod
    def can_transition(cls, current_status, new_status):
        """Check if status transition is allowed"""
        # Direct transition check
        allowed = cls.ALLOWED_TRANSITIONS.get(current_status, [])
        
        # Add special "_any_" transitions
        allowed.extend(cls.ALLOWED_TRANSITIONS.get('_any_', []))
        
        # Special case: Allow any transition if the current status is unknown
        # This handles the case where a vehicle was added manually with no status
        if not current_status:
            return True
            
        return new_status in allowed
    
    @classmethod
    def update_status(cls, vehicle_id, new_status, update_fields=None):
        """Update vehicle status with validation and side effects"""
        try:
            # If new_status is a frontend status, convert it to db status
            new_status = cls.get_db_status(new_status)
            
            # Special case for "Action" frontend status
            if new_status == 'Ready for Action':
                # Default to "Ready for Auction"
                new_status = 'Ready for Auction'
            
            with transaction() as conn:
                cursor = conn.cursor()
                
                # Get current status
                cursor.execute(
                    "SELECT status FROM vehicles WHERE towbook_call_number = ?", 
                    (vehicle_id,)
                )
                result = cursor.fetchone()
                
                if not result:
                    return False, "Vehicle not found"
                    
                current_status = result['status']
                
                # Check if transition is allowed
                if not cls.can_transition(current_status, new_status):
                    return False, f"Cannot transition from {current_status} to {new_status}"
                
                # Prepare update fields
                if update_fields is None:
                    update_fields = {}
                
                fields = {
                    'status': new_status,
                    'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                
                # Add status-specific fields
                if new_status == 'TOP Generated':
                    fields['top_form_sent_date'] = datetime.now().strftime('%Y-%m-%d')
                    # Calculate TR-52 date (20 days after TOP generation)
                    tr52_date = datetime.now() + timedelta(days=20)
                    fields['tr52_available_date'] = tr52_date.strftime('%Y-%m-%d')
                    
                elif new_status == 'Paperwork Received':
                    fields['paperwork_received_date'] = datetime.now().strftime('%Y-%m-%d')
                    
                elif new_status == 'Ready for Auction':
                    # Calculate next auction date (next Monday after paper deadline)
                    try:
                        today = datetime.now().date()
                        days_to_monday = (7 - today.weekday()) % 7  # Days until next Monday
                        if days_to_monday < 3:  # If Monday is less than 3 days away, target the following Monday
                            days_to_monday += 7
                        next_monday = today + timedelta(days=days_to_monday)
                        
                        # Ensure we have at least 10 days for the newspaper ad
                        if (next_monday - today).days < 10:
                            next_monday += timedelta(days=7)
                            
                        fields['estimated_date'] = next_monday.strftime('%Y-%m-%d')
                        fields['decision'] = 'Auction'
                        fields['decision_date'] = datetime.now().strftime('%Y-%m-%d')
                    except Exception as e:
                        logging.warning(f"Error calculating auction date: {e}")
                        
                elif new_status == 'Ready for Scrap':
                    # 7 days after paperwork received
                    try:
                        cursor.execute("SELECT paperwork_received_date FROM vehicles WHERE towbook_call_number = ?", (vehicle_id,))
                        result = cursor.fetchone()
                        if result and result['paperwork_received_date']:
                            paperwork_date = datetime.strptime(result['paperwork_received_date'], '%Y-%m-%d')
                            scrap_date = paperwork_date + timedelta(days=7)
                            fields['estimated_date'] = scrap_date.strftime('%Y-%m-%d')
                        
                        fields['decision'] = 'Scrap'
                        fields['decision_date'] = datetime.now().strftime('%Y-%m-%d')
                    except Exception as e:
                        logging.warning(f"Error calculating scrap date: {e}")
                
                # For release-type statuses, ensure we have a proper release reason if not specified
                if new_status in ['Auctioned', 'Scrapped', 'Released']:
                    if 'release_reason' not in fields and 'release_reason' not in update_fields:
                        if new_status == 'Released':
                            fields['release_reason'] = 'Released to Owner'
                        elif new_status == 'Auctioned':
                            fields['release_reason'] = 'Auctioned'
                        elif new_status == 'Scrapped':
                            fields['release_reason'] = 'Scrapped'
                    
                    # Add release date and time if not present
                    if 'release_date' not in fields and 'release_date' not in update_fields:
                        fields['release_date'] = datetime.now().strftime('%Y-%m-%d')
                    if 'release_time' not in fields and 'release_time' not in update_fields:
                        fields['release_time'] = datetime.now().strftime('%H:%M')
                        
                    # Mark as archived to move to completed tab
                    fields['archived'] = 1
                
                # Add any additional fields passed in
                fields.update(update_fields)
                
                # Build the update query
                set_clause = ', '.join([f"{field} = ?" for field in fields.keys()])
                values = list(fields.values()) + [vehicle_id]
                
                cursor.execute(f"""
                    UPDATE vehicles 
                    SET {set_clause}
                    WHERE towbook_call_number = ?
                """, values)
                
                # Log the status change
                log_action("STATUS_CHANGE", vehicle_id, f"Changed status from {current_status} to {new_status}")
                
                return True, f"Status updated to {new_status}"
                
        except Exception as e:
            logging.error(f"Error updating status: {e}")
            return False, str(e)
    
    @classmethod
    def batch_update_status(cls, vehicle_ids, new_status):
        """Update status for multiple vehicles"""
        try:
            # Convert frontend status to db status if needed
            db_status = cls.get_db_status(new_status)
            
            # Special case for "Action" frontend status
            if db_status == 'Ready for Action':
                db_status = 'Ready for Auction'
            
            with transaction() as conn:
                cursor = conn.cursor()
                updated_count = 0
                failures = 0
                
                for vehicle_id in vehicle_ids:
                    # Get current status
                    cursor.execute(
                        "SELECT status FROM vehicles WHERE towbook_call_number = ?", 
                        (vehicle_id,)
                    )
                    result = cursor.fetchone()
                    
                    if not result:
                        failures += 1
                        continue
                        
                    current_status = result['status']
                    
                    # Skip if status is already set to the new status
                    if current_status == db_status:
                        continue
                    
                    # For batch operations, we don't strictly enforce transitions
                    # This allows admins to fix incorrectly set statuses
                    
                    # Update status and add timestamp
                    cursor.execute("""
                        UPDATE vehicles
                        SET status = ?, last_updated = ?
                        WHERE towbook_call_number = ?
                    """, (db_status, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), vehicle_id))
                    
                    if cursor.rowcount > 0:
                        updated_count += 1
                        log_action("STATUS_CHANGE", vehicle_id, f"Changed status from {current_status} to {db_status} (batch update)")
                
                return True, updated_count, f"Updated {updated_count} vehicles to {new_status}"
                
        except Exception as e:
            logging.error(f"Error in batch update: {e}")
            return False, 0, str(e)

# Standalone test if script is run directly
if __name__ == '__main__':
    # Configure logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    # Test frontend/backend status conversion
    print("Testing status conversion:")
    frontend_statuses = ['New', 'TOP_Sent', 'Ready', 'Paperwork', 'Action', 'InAuction', 'Completed']
    for status in frontend_statuses:
        db_status = StatusManager.get_db_status(status)
        back_to_frontend = StatusManager.get_frontend_status(db_status)
        print(f"Frontend: {status} -> DB: {db_status} -> Frontend: {back_to_frontend}")
    
    # Test allowed transitions
    print("\nTesting allowed transitions:")
    for from_status, to_statuses in StatusManager.ALLOWED_TRANSITIONS.items():
        if from_status == '_any_':
            continue  # Skip special case
        for to_status in to_statuses:
            can_transition = StatusManager.can_transition(from_status, to_status)
            print(f"{from_status} -> {to_status}: {can_transition}")
    
    # Test can't transition to invalid status
    print("\nTesting invalid transitions:")
    print(f"New -> Auctioned: {StatusManager.can_transition('New', 'Auctioned')}")
    print(f"TOP Generated -> Scrapped: {StatusManager.can_transition('TOP Generated', 'Scrapped')}")