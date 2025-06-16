"""
Background Task Scheduler
Handles automated workflow execution and periodic tasks
"""

import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import signal
import sys

logger = logging.getLogger(__name__)

class TaskScheduler:
    """
    Background task scheduler for automated workflows
    """
    
    def __init__(self, app):
        self.app = app
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.shutdown_event = threading.Event()
        
        # Task intervals (in seconds)
        self.workflow_check_interval = app.config.get('WORKFLOW_CHECK_INTERVAL', 3600)  # 1 hour
        self.status_update_interval = app.config.get('STATUS_UPDATE_INTERVAL', 21600)   # 6 hours
        self.notification_check_interval = app.config.get('NOTIFICATION_CHECK_INTERVAL', 1800)  # 30 minutes
        
        # Last execution times
        self.last_workflow_check = datetime.min
        self.last_status_update = datetime.min
        self.last_notification_check = datetime.min
        
        # Register shutdown handler
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
    
    def start(self):
        """Start the background scheduler"""
        if self.running:
            logger.warning("Scheduler is already running")
            return
        
        self.running = True
        self.shutdown_event.clear()
        self.thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.thread.start()
        logger.info("Background task scheduler started")
    
    def stop(self):
        """Stop the background scheduler"""
        if not self.running:
            return
        
        self.running = False
        self.shutdown_event.set()
        
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=10)
        
        logger.info("Background task scheduler stopped")
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, shutting down scheduler...")
        self.stop()
    
    def _run_scheduler(self):
        """Main scheduler loop"""
        logger.info("Background scheduler loop started")
        
        while self.running and not self.shutdown_event.is_set():
            try:
                current_time = datetime.now()
                
                # Check if workflow analysis is due
                if self._should_run_task(current_time, self.last_workflow_check, self.workflow_check_interval):
                    self._run_workflow_analysis()
                    self.last_workflow_check = current_time
                
                # Check if status updates are due
                if self._should_run_task(current_time, self.last_status_update, self.status_update_interval):
                    self._run_status_updates()
                    self.last_status_update = current_time
                
                # Check if notification processing is due
                if self._should_run_task(current_time, self.last_notification_check, self.notification_check_interval):
                    self._run_notification_processing()
                    self.last_notification_check = current_time
                
                # Sleep for a short interval before next check
                if not self.shutdown_event.wait(60):  # Check every minute
                    continue
                else:
                    break
                    
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}", exc_info=True)
                # Continue running even if one task fails
                time.sleep(60)
        
        logger.info("Background scheduler loop ended")
    
    def _should_run_task(self, current_time: datetime, last_run: datetime, interval: int) -> bool:
        """Check if enough time has passed to run a task"""
        return (current_time - last_run).total_seconds() >= interval
    
    def _run_workflow_analysis(self):
        """Run automated workflow analysis"""
        try:
            with self.app.app_context():
                logger.info("Starting automated workflow analysis...")
                
                # Get the automated workflow engine
                automated_workflow = getattr(self.app, 'automated_workflow', None)
                if not automated_workflow:
                    logger.warning("Automated workflow engine not available")
                    return
                
                # Execute automated actions
                results = automated_workflow.execute_automated_actions()
                
                logger.info(f"Automated workflow analysis completed: {results}")
                
        except Exception as e:
            logger.error(f"Error during workflow analysis: {e}", exc_info=True)
    
    def _run_status_updates(self):
        """Run periodic status updates"""
        try:
            with self.app.app_context():
                logger.info("Starting periodic status updates...")
                
                # Get the workflow engine
                workflow_engine = getattr(self.app, 'workflow_engine', None)
                if not workflow_engine:
                    logger.warning("Workflow engine not available")
                    return
                
                # Get vehicles needing attention
                vehicles = workflow_engine.get_daily_priorities()
                urgent_count = len(vehicles.get('urgent', []))
                
                # Log summary
                logger.info(f"Status update scan completed: {urgent_count} vehicles need attention")
                
        except Exception as e:
            logger.error(f"Error during status updates: {e}", exc_info=True)
    
    def _run_notification_processing(self):
        """Run notification processing"""
        try:
            with self.app.app_context():
                logger.info("Starting notification processing...")
                
                # Get the automated workflow engine
                automated_workflow = getattr(self.app, 'automated_workflow', None)
                if not automated_workflow:
                    logger.warning("Automated workflow engine not available")
                    return
                
                # Process pending notifications
                notifications_sent = automated_workflow._check_notification_queue()
                
                logger.info(f"Notification processing completed: {notifications_sent} notifications processed")
                
        except Exception as e:
            logger.error(f"Error during notification processing: {e}", exc_info=True)
    
    def get_status(self) -> Dict[str, Any]:
        """Get scheduler status information"""
        return {
            'running': self.running,
            'last_workflow_check': self.last_workflow_check.isoformat() if self.last_workflow_check != datetime.min else None,
            'last_status_update': self.last_status_update.isoformat() if self.last_status_update != datetime.min else None,
            'last_notification_check': self.last_notification_check.isoformat() if self.last_notification_check != datetime.min else None,
            'workflow_check_interval': self.workflow_check_interval,
            'status_update_interval': self.status_update_interval,
            'notification_check_interval': self.notification_check_interval
        }


def init_scheduler(app):
    """Initialize and start the task scheduler"""
    scheduler = TaskScheduler(app)
    app.scheduler = scheduler
    
    # Only start scheduler in production mode
    if app.config.get('ENV') == 'production':
        scheduler.start()
        logger.info("Task scheduler initialized and started for production")
    else:
        logger.info("Task scheduler initialized but not started (development mode)")
    
    return scheduler
