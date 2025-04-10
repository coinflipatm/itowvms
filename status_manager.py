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
        'TOP Generated': ['TR52 Ready'],
        'TR52 Ready': ['Ready for Auction', 'Ready for Scrap'],
        'Ready for Auction': ['Auctioned'],
        'Ready for Scrap': ['Scrapped'],
        # Special case: Any status can go to Released
        '_any_': ['Released']
    }
    
    # Status display names
    STATUS_DISPLAY_NAMES = {
        'New': 'New',
        'TOP Generated': 'TOP Generated',
        'TR52 Ready': 'TR52 Ready',
        'Ready for Auction': 'Ready for Auction',
        'Ready for Scrap': 'Ready for Scrap',
        'Auctioned': 'Auctioned',
        'Scrapped': 'Scrapped',
        'Released': 'Released'
    }
    
    # Frontend to database status mapping
    FRONTEND_TO_DB_STATUS = {
        'New': 'New',
        'TOP_Generated': 'TOP Generated',
        'TR52_Ready': 'TR52 Ready', 
        'Ready_Auction': 'Ready for Auction',
        'Ready_Scrap': 'Ready for Scrap',
        'Auctioned': 'Auctioned',
        'Scrapped': 'Scrapped',
        'Released': 'Released',
        'Completed': 'Released'  # For backward compatibility
    }
    
    # Database to frontend status mapping
    DB_TO_FRONTEND_STATUS = {
        'New': 'New',
        'TOP Generated': 'TOP_Generated',
        'TR52 Ready': 'TR52_Ready',
        'Ready for Auction': 'Ready_Auction',
        'Ready for Scrap': 'Ready_Scrap',
        'Auctioned': 'Completed',
        'Scrapped': 'Completed',
        'Released': 'Completed'
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
                    
                elif new_status == 'TR52 Ready':
                    # No additional fields needed for TR52 Ready status
                    pass
                    
                elif new_status == 'Ready for Auction':
                    # Calculate next auction date
                    try:
                        today = datetime.now().date()
                        days_to_monday = (7 - today.weekday()) % 7  # Days until next Monday
                        if days_to_monday < 3:  # If Monday is less than 3 days away, target the following Monday
                            days_to_monday += 7
                        next_monday = today + timedelta(days=days_to_monday)
                        
                        # Auction must be at least 10 days from now for newspaper ad
                        if (next_monday - today).days < 10:
                            next_monday += timedelta(days=7)
                            
                        fields['auction_date'] = next_monday.strftime('%Y-%m-%d')
                        fields['decision'] = 'Auction'
                        fields['decision_date'] = datetime.now().strftime('%Y-%m-%d')
                    except Exception as e:
                        logging.warning(f"Error calculating auction date: {e}")
                        
                elif new_status == 'Ready for Scrap':
                    # 7 days after TR52 Ready status
                    scrap_date = datetime.now() + timedelta(days=7)
                    fields['estimated_date'] = scrap_date.strftime('%Y-%m-%d')
                    fields['decision'] = 'Scrap'
                    fields['decision_date'] = datetime.now().strftime('%Y-%m-%d')
                
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