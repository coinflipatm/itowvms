"""
Automated Status Progression Scheduler for iTow Vehicle Management System

This module implements automated status progression using APScheduler to periodically
check and advance vehicle statuses based on time thresholds defined in the workflow.

Features:
- Periodic status checks (every hour by default)
- Automatic status advancement based on time thresholds
- Notification creation for due actions
- Background task management
- Logging of all automated actions
"""

import logging
import atexit
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_EXECUTED

# Import existing functions
from database import check_and_update_statuses, get_db_connection
from status_manager import StatusManager
from utils import log_action

class AutomatedStatusScheduler:
    """
    Manages automated status progression for vehicles
    """
    
    def __init__(self, app=None):
        self.scheduler = None
        self.app = app
        self.logger = logging.getLogger(__name__)
        # Default configuration for automation scheduler
        self.config = {
            'check_interval': 60,
            'rules': {
                'new_to_top_days': 3,
                'top_to_auction_days': 25,
                'top_to_scrap_days': 45,
                'auto_advance': {
                    'new_to_top': True,
                    'top_to_auction': True,
                    'top_to_scrap': False
                },
                'notifications': {
                    'new_to_top': True,
                    'top_to_auction': True,
                    'top_to_scrap': True
                }
            }
        }
        self._initialize_scheduler()
    
    def _initialize_scheduler(self):
        """Initialize the background scheduler"""
        try:
            # Configure job defaults
            job_defaults = {
                'coalesce': True,  # Combine multiple pending executions into one
                'max_instances': 1,  # Only allow one instance of each job to run
                'misfire_grace_time': 300  # 5 minutes grace time for missed jobs
            }
            
            # Configure executors
            executors = {
                'default': ThreadPoolExecutor(max_workers=1),
            }
            
            # Create scheduler
            self.scheduler = BackgroundScheduler(
                job_defaults=job_defaults,
                executors=executors,
                timezone='America/New_York'  # Adjust timezone as needed
            )
            
            # Add event listeners
            self.scheduler.add_listener(self._job_listener, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)
            
            self.logger.info("Automated status scheduler initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize scheduler: {e}")
            raise
    
    def _job_listener(self, event):
        """Listen for job events and log them"""
        if event.exception:
            self.logger.error(f"Scheduled job {event.job_id} failed: {event.exception}")
        else:
            self.logger.info(f"Scheduled job {event.job_id} executed successfully")
    
    def start_scheduler(self):
        """Start the background scheduler with all automated tasks"""
        if self.scheduler and not self.scheduler.running:
            try:
                # Add the main status progression job
                self.scheduler.add_job(
                    func=self._run_status_progression,
                    trigger=IntervalTrigger(hours=1),  # Run every hour
                    id='status_progression',
                    name='Automated Status Progression',
                    replace_existing=True
                )
                
                # Add daily morning status check job
                self.scheduler.add_job(
                    func=self._daily_morning_status_check,
                    trigger=CronTrigger(hour=8, minute=0),  # Run at 8:00 AM daily
                    id='daily_morning_status_check',
                    name='Daily Morning Status Refresh',
                    replace_existing=True
                )
                
                # Add notification processing job (more frequent)
                self.scheduler.add_job(
                    func=self._process_notifications,
                    trigger=IntervalTrigger(minutes=30),  # Run every 30 minutes
                    id='notification_processing',
                    name='Notification Processing',
                    replace_existing=True
                )
                
                # Add daily cleanup job
                self.scheduler.add_job(
                    func=self._daily_cleanup,
                    trigger=CronTrigger(hour=1, minute=0),  # Run at 1:00 AM daily
                    id='daily_cleanup',
                    name='Daily System Cleanup',
                    replace_existing=True
                )
                
                # Add automatic status advancement job (runs more frequently for time-sensitive updates)
                self.scheduler.add_job(
                    func=self._auto_advance_statuses,
                    trigger=IntervalTrigger(hours=6),  # Run every 6 hours
                    id='auto_advance_statuses',
                    name='Automatic Status Advancement',
                    replace_existing=True
                )
                
                self.scheduler.start()
                self.logger.info("Automated status scheduler started successfully")
                
                # Register shutdown handler
                atexit.register(self.shutdown_scheduler)
                
            except Exception as e:
                self.logger.error(f"Failed to start scheduler: {e}")
                raise
        else:
            self.logger.warning("Scheduler is already running or not initialized")
    
    def shutdown_scheduler(self):
        """Shutdown the scheduler gracefully"""
        if self.scheduler and self.scheduler.running:
            self.scheduler.shutdown(wait=True)
            self.logger.info("Automated status scheduler shut down")
    
    def _run_status_progression(self):
        """Run the existing status progression logic"""
        try:
            self.logger.info("Running automated status progression check")
            
            # Run the existing check_and_update_statuses function
            result = check_and_update_statuses()
            
            if result:
                self.logger.info("Status progression check completed successfully")
            else:
                self.logger.warning("Status progression check completed with issues")
                
        except Exception as e:
            self.logger.error(f"Error in status progression: {e}")
            # Don't raise the exception - let the scheduler continue
    
    def _auto_advance_statuses(self):
        """Automatically advance vehicles that meet criteria for status progression"""
        try:
            self.logger.info("Running automatic status advancement")
            
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Get all active vehicles
            cursor.execute("SELECT * FROM vehicles WHERE archived = 0")
            vehicles = cursor.fetchall()
            
            today = datetime.now().date()
            advanced_count = 0
            
            for vehicle in vehicles:
                try:
                    call_number = vehicle['towbook_call_number']
                    current_status = vehicle['status']
                    last_updated = vehicle['last_updated']
                    
                    # Parse last updated date
                    if last_updated:
                        try:
                            if ' ' in last_updated:
                                last_updated_date = datetime.strptime(last_updated, '%Y-%m-%d %H:%M:%S').date()
                            else:
                                last_updated_date = datetime.strptime(last_updated, '%Y-%m-%d').date()
                        except ValueError:
                            continue
                    else:
                        continue
                    
                    days_in_status = (today - last_updated_date).days
                    
                    # Check if vehicle should be automatically advanced
                    should_advance, new_status = self._should_advance_status(vehicle, days_in_status)
                    
                    if should_advance and new_status:
                        # Use StatusManager to update status
                        success, message = StatusManager.update_status(call_number, new_status)
                        
                        if success:
                            advanced_count += 1
                            log_action("AUTO_ADVANCE", call_number, 
                                     f"Automatically advanced from {current_status} to {new_status} after {days_in_status} days")
                            self.logger.info(f"Auto-advanced vehicle {call_number} from {current_status} to {new_status}")
                        else:
                            self.logger.warning(f"Failed to auto-advance vehicle {call_number}: {message}")
                            
                except Exception as e:
                    self.logger.error(f"Error processing vehicle {vehicle['towbook_call_number'] if 'towbook_call_number' in vehicle.keys() else 'unknown'}: {e}")
                    continue
            
            conn.close()
            
            if advanced_count > 0:
                self.logger.info(f"Automatically advanced {advanced_count} vehicles")
            else:
                self.logger.info("No vehicles required automatic advancement")
                
        except Exception as e:
            self.logger.error(f"Error in automatic status advancement: {e}")
    
    def _should_advance_status(self, vehicle, days_in_status):
        """Determine if a vehicle should be automatically advanced and to what status"""
        status = vehicle['status']
        owner_known = vehicle['owner_known'] if 'owner_known' in vehicle.keys() else 'No'
        
        # Define automatic advancement rules based on workflow thresholds
        advancement_rules = {
            'New': {
                'threshold': 3,  # Advance after 3 days (trigger is 2, advance at 3)
                'next_status': 'TOP Generated',
                'condition': lambda v: True  # Always advance New vehicles
            },
            'TOP Generated': {
                'threshold': 25,  # Advance after 25 days (trigger is 20, advance at 25)
                'next_status': 'Ready for Auction',  # Default to auction
                'condition': lambda v: True  # Always advance after redemption period
            },
            'Ready for Auction': {
                'threshold': 7,  # Advance after 7 days (trigger is 5, advance at 7)
                'next_status': 'Ready for Auction',  # Keep same status (no auto-advance from auction)
                'condition': lambda v: False  # Don't auto-advance auction status
            },
            'Ready for Scrap': {
                'threshold': 7,  # Advance after 7 days
                'next_status': 'Ready for Scrap',  # Keep same status (no auto-advance from scrap)
                'condition': lambda v: False  # Don't auto-advance scrap status
            }
            # Note: We don't auto-advance auction/scrap status as these require actual processing
        }
        
        rule = advancement_rules.get(status)
        if not rule:
            return False, None
        
        # Check if enough time has passed
        if days_in_status < rule['threshold']:
            return False, None
        
        # Check any additional conditions
        if not rule['condition'](vehicle):
            return False, None
        
        return True, rule['next_status']
    
    def _process_notifications(self):
        """Process pending notifications and create new ones as needed"""
        try:
            self.logger.info("Processing notifications")
            
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Get overdue notifications that haven't been sent
            today = datetime.now().date()
            cursor.execute("""
                SELECT * FROM notifications 
                WHERE status = 'pending' 
                AND due_date <= ? 
                AND sent_date IS NULL
            """, (today.strftime('%Y-%m-%d'),))
            
            overdue_notifications = cursor.fetchall()
            
            for notification in overdue_notifications:
                try:
                    # Log the overdue notification
                    log_action("NOTIFICATION_OVERDUE", notification['vehicle_id'], 
                             f"Overdue {notification['notification_type']} notification - due {notification['due_date']}")
                    
                    # Mark as processed to avoid repeated logs
                    cursor.execute("""
                        UPDATE notifications 
                        SET status = 'overdue', updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    """, (notification['id'],))
                    
                except Exception as e:
                    self.logger.error(f"Error processing notification {notification['id']}: {e}")
            
            conn.commit()
            conn.close()
            
            if overdue_notifications:
                self.logger.info(f"Processed {len(overdue_notifications)} overdue notifications")
            
        except Exception as e:
            self.logger.error(f"Error processing notifications: {e}")
    
    def _daily_cleanup(self):
        """Perform daily system cleanup tasks"""
        try:
            self.logger.info("Running daily cleanup tasks")
            
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Clean up old notifications (older than 90 days)
            cleanup_date = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
            cursor.execute("""
                DELETE FROM notifications 
                WHERE created_at < ? 
                AND status IN ('sent', 'completed')
            """, (cleanup_date,))
            
            deleted_notifications = cursor.rowcount
            
            # Update any stale status calculations
            cursor.execute("""
                UPDATE vehicles 
                SET last_updated = CASE 
                    WHEN last_updated IS NULL THEN datetime('now')
                    ELSE last_updated 
                END
                WHERE archived = 0
            """)
            
            conn.commit()
            conn.close()
            
            # Log cleanup results
            log_action("SYSTEM_CLEANUP", "SYSTEM", 
                     f"Daily cleanup: removed {deleted_notifications} old notifications")
            
            self.logger.info(f"Daily cleanup completed: removed {deleted_notifications} old notifications")
            
        except Exception as e:
            self.logger.error(f"Error in daily cleanup: {e}")
    
    def add_one_time_job(self, func, run_date, job_id, **kwargs):
        """Add a one-time job to the scheduler"""
        try:
            self.scheduler.add_job(
                func=func,
                trigger='date',
                run_date=run_date,
                id=job_id,
                replace_existing=True,
                **kwargs
            )
            self.logger.info(f"Added one-time job {job_id} scheduled for {run_date}")
        except Exception as e:
            self.logger.error(f"Failed to add one-time job {job_id}: {e}")
    
    def get_scheduler_status(self):
        """Get the current status of the scheduler and its jobs"""
        if not self.scheduler:
            return {"running": False, "jobs": []}
        jobs = []
        last_run = None
        next_run = None
        
        for job in self.scheduler.get_jobs():
            jobs.append({
                "id": job.id,
                "name": job.name,
                "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
                "trigger": str(job.trigger)
            })
            
            # Get last run and next run for the main status check job
            if job.id == 'status_progression_check':
                next_run = job.next_run_time.isoformat() if job.next_run_time else None
        
        # Try to get last run from job history or logs
        # For now, we'll use a placeholder
        
        return {
            "running": self.scheduler.running,
            "jobs": jobs
        }

    def get_configuration(self):
        """Get the current automation scheduler configuration"""
        return self.config

    def update_configuration(self, config_data):
        """Update the automation scheduler configuration"""
        # Merge incoming config with existing
        for key, value in config_data.items():
            if key == 'rules' and isinstance(value, dict):
                self.config['rules'].update(value)
            else:
                self.config[key] = value
        self.logger.info(f"Scheduler configuration updated: {self.config}")
    
    def _daily_morning_status_check(self):
        """Comprehensive daily morning status check and refresh for all vehicles"""
        try:
            self.logger.info("Running daily morning status check and refresh")
            
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Get all active vehicles for comprehensive status check
            cursor.execute("SELECT * FROM vehicles WHERE archived = 0")
            vehicles = cursor.fetchall()
            
            today = datetime.now().date()
            checked_count = 0
            updated_count = 0
            notifications_created = 0
            
            self.logger.info(f"Checking {len(vehicles)} active vehicles for status updates")
            
            for vehicle in vehicles:
                try:
                    call_number = vehicle['towbook_call_number']
                    current_status = vehicle['status']
                    last_updated = vehicle['last_updated']
                    
                    checked_count += 1
                    
                    # Parse last updated date
                    if last_updated:
                        try:
                            if ' ' in last_updated:
                                last_updated_date = datetime.strptime(last_updated, '%Y-%m-%d %H:%M:%S').date()
                            else:
                                last_updated_date = datetime.strptime(last_updated, '%Y-%m-%d').date()
                        except ValueError:
                            continue
                    else:
                        continue
                    
                    days_in_status = (today - last_updated_date).days
                    
                    # Check status-specific thresholds for notifications and actions
                    notifications_needed = self._check_status_thresholds(vehicle, days_in_status, conn)
                    
                    for notification_type in notifications_needed:
                        self._create_notification(call_number, notification_type, days_in_status, conn)
                        notifications_created += 1
                    
                    # Check if vehicle should be automatically advanced
                    should_advance, new_status = self._should_advance_status(vehicle, days_in_status)
                    
                    if should_advance and new_status:
                        # Use StatusManager to update status
                        success, message = StatusManager.update_status(call_number, new_status)
                        
                        if success:
                            updated_count += 1
                            log_action("MORNING_CHECK_ADVANCE", call_number, 
                                     f"Daily check: Advanced from {current_status} to {new_status} after {days_in_status} days")
                            self.logger.info(f"Morning check: Advanced vehicle {call_number} from {current_status} to {new_status}")
                        else:
                            self.logger.warning(f"Failed to advance vehicle {call_number}: {message}")
                    
                    # Log daily check activity for tracking
                    if days_in_status > 0 and days_in_status % 7 == 0:  # Weekly milestones
                        log_action("MORNING_CHECK", call_number, 
                                 f"Daily check: Vehicle has been in {current_status} status for {days_in_status} days")
                            
                except Exception as e:
                    self.logger.error(f"Error processing vehicle {vehicle['towbook_call_number'] if 'towbook_call_number' in vehicle.keys() else 'unknown'}: {e}")
                    continue
            
            conn.close()
            
            # Log comprehensive summary
            log_action("MORNING_CHECK_SUMMARY", "SYSTEM", 
                     f"Daily morning check: {checked_count} vehicles checked, {updated_count} advanced, {notifications_created} notifications created")
            
            self.logger.info(f"Daily morning check completed: checked {checked_count} vehicles, advanced {updated_count}, created {notifications_created} notifications")
            
            # Also run the regular status progression check
            self._run_status_progression()
            
        except Exception as e:
            self.logger.error(f"Error in daily morning status check: {e}")
    
    def _check_status_thresholds(self, vehicle, days_in_status, conn=None):
        """Check if vehicle meets thresholds for notifications based on status and days"""
        status = vehicle['status']
        notifications_needed = []
        
        # Define notification thresholds for each status
        thresholds = {
            'New': {
                2: 'new_vehicle_reminder',  # 2 days: reminder to generate TOP
                7: 'new_vehicle_overdue'    # 7 days: overdue for TOP generation
            },
            'TOP Generated': {
                20: 'redemption_ending_soon',  # 20 days: redemption period ending soon
                25: 'redemption_expired',      # 25 days: redemption period expired
                40: 'auction_preparation',     # 40 days: should prepare for auction
                50: 'auction_overdue'          # 50 days: overdue for auction
            },
            'Ready for Auction': {
                5: 'auction_pending',     # 5 days: auction has been pending
                14: 'auction_overdue'     # 14 days: auction is overdue
            },
            'Ready for Scrap': {
                7: 'scrap_pending',       # 7 days: scrap has been pending
                14: 'scrap_overdue'       # 14 days: scrap is overdue
            }
        }
        
        status_thresholds = thresholds.get(status, {})
        
        for threshold_days, notification_type in status_thresholds.items():
            if days_in_status >= threshold_days:
                # Check if notification already exists to avoid duplicates
                if not self._notification_exists(vehicle['towbook_call_number'], notification_type, conn):
                    notifications_needed.append(notification_type)
        
        return notifications_needed
    
    def _notification_exists(self, call_number, notification_type, conn=None):
        """Check if a notification of this type already exists for the vehicle"""
        try:
            # Use provided connection or create a new one
            close_conn = False
            if conn is None:
                conn = get_db_connection()
                close_conn = True
                
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT COUNT(*) FROM notifications 
                WHERE vehicle_id = ? AND notification_type = ? 
                AND created_at >= date('now', '-7 days')
            """, (call_number, notification_type))
            
            count = cursor.fetchone()[0]
            
            # Only close if we created the connection
            if close_conn:
                conn.close()
            
            return count > 0
        except Exception:
            return False  # If we can't check, create the notification anyway
    
    def _create_notification(self, call_number, notification_type, days_in_status, conn=None):
        """Create a notification for a vehicle"""
        try:
            # Use provided connection or create a new one
            close_conn = False
            if conn is None:
                conn = get_db_connection()
                close_conn = True
                
            cursor = conn.cursor()
            
            due_date = datetime.now().date()
            message = self._get_notification_message(notification_type, days_in_status)
            
            cursor.execute("""
                INSERT INTO notifications (vehicle_id, notification_type, message, due_date, status, created_at)
                VALUES (?, ?, ?, ?, 'pending', CURRENT_TIMESTAMP)
                """, (call_number, notification_type, message, due_date.strftime('%Y-%m-%d')))
            
            conn.commit()
            
            # Only close if we created the connection
            if close_conn:
                conn.close()
            
            log_action("NOTIFICATION_CREATED", call_number, 
                     f"Created {notification_type} notification - {message}")
            
        except Exception as e:
            self.logger.error(f"Error creating notification for {call_number}: {e}")
    
    def _get_notification_message(self, notification_type, days_in_status):
        """Get appropriate message for notification type"""
        messages = {
            'new_vehicle_reminder': f'Vehicle needs TOP generation (in New status for {days_in_status} days)',
            'new_vehicle_overdue': f'Vehicle overdue for TOP generation (in New status for {days_in_status} days)',
            'redemption_ending_soon': f'Redemption period ending soon (in TOP Generated for {days_in_status} days)',
            'redemption_expired': f'Redemption period expired (in TOP Generated for {days_in_status} days)',
            'auction_preparation': f'Vehicle should be prepared for auction (in TOP Generated for {days_in_status} days)',
            'auction_overdue': f'Vehicle overdue for auction (in TOP Generated for {days_in_status} days)',
            'auction_pending': f'Auction pending (in Ready for Auction for {days_in_status} days)',
            'auction_overdue': f'Auction overdue (in Ready for Auction for {days_in_status} days)',
            'scrap_pending': f'Scrap pending (in Ready for Scrap for {days_in_status} days)',
            'scrap_overdue': f'Scrap overdue (in Ready for Scrap for {days_in_status} days)'
        }
        
        return messages.get(notification_type, f'Status check notification ({days_in_status} days in current status)')

# Global scheduler instance
_scheduler_instance = None

def get_scheduler():
    """Get the global scheduler instance"""
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = AutomatedStatusScheduler()
    return _scheduler_instance

def init_scheduler(app):
    """Initialize the scheduler with Flask app context"""
    scheduler = get_scheduler()
    scheduler.app = app
    
    # Start the scheduler automatically
    try:
        scheduler.start_scheduler()
        app.logger.info("Automated status progression scheduler started")
    except Exception as e:
        app.logger.error(f"Failed to start scheduler: {e}")
    
    return scheduler
