"""
Email Notification System
Handles email notifications and queue management
"""

import logging
import smtplib
import sqlite3
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, Dict, List
from flask import current_app

logger = logging.getLogger(__name__)

class NotificationManager:
    """
    Manages email notifications and notification queue
    """
    
    def __init__(self, app=None):
        self.app = app
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize notification system with Flask app"""
        self.app = app
        
        # Initialize notification queue table (defer to first use)
        # self._create_notification_table()
    
    def _create_notification_table(self):
        """Create notification queue table if it doesn't exist"""
        try:
            from app.core.database import get_db_connection
            
            db = get_db_connection()
            cursor = db.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS notification_queue (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    vehicle_call_number TEXT,
                    notification_type TEXT NOT NULL,
                    recipient_email TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    body TEXT NOT NULL,
                    scheduled_date TEXT NOT NULL,
                    status TEXT DEFAULT 'pending',
                    retry_count INTEGER DEFAULT 0,
                    created_date TEXT DEFAULT CURRENT_TIMESTAMP,
                    sent_date TEXT,
                    error_message TEXT
                )
            """)
            
            # Create index for efficient querying
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_notification_status_date 
                ON notification_queue(status, scheduled_date)
            """)
            
            db.commit()
            logger.info("Notification queue table initialized")
        
        except Exception as e:
            logger.error(f"Error creating notification table: {e}")
    
    def queue_notification(self, 
                          recipient_email: str,
                          subject: str,
                          body: str,
                          notification_type: str,
                          vehicle_call_number: Optional[str] = None,
                          scheduled_date: Optional[datetime] = None) -> bool:
        """
        Add a notification to the queue
        
        Args:
            recipient_email: Email address to send to
            subject: Email subject
            body: Email body
            notification_type: Type of notification
            vehicle_call_number: Associated vehicle (optional)
            scheduled_date: When to send (defaults to now)
            
        Returns:
            True if queued successfully
        """
        
        try:
            # Ensure table exists
            self._create_notification_table()
            
            if scheduled_date is None:
                scheduled_date = datetime.now()
            
            from app.core.database import get_db_connection
            
            db = get_db_connection()
            cursor = db.cursor()
            cursor.execute("""
                INSERT INTO notification_queue 
                (vehicle_call_number, notification_type, recipient_email, 
                 subject, body, scheduled_date)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (vehicle_call_number, notification_type, recipient_email,
                  subject, body, scheduled_date.isoformat()))
            
            db.commit()
            notification_id = cursor.lastrowid
            
            logger.info(f"Notification {notification_id} queued for {recipient_email}")
            return True
        
        except Exception as e:
            logger.error(f"Error queueing notification: {e}")
            return False
    
    def send_immediate(self, 
                      recipient_email: str,
                      subject: str,
                      body: str,
                      notification_type: str = 'immediate') -> bool:
        """
        Send an email immediately (bypassing queue)
        
        Args:
            recipient_email: Email address
            subject: Email subject
            body: Email body
            notification_type: Type of notification
            
        Returns:
            True if sent successfully
        """
        
        try:
            return self._send_email(recipient_email, subject, body)
        
        except Exception as e:
            logger.error(f"Error sending immediate notification: {e}")
            return False
    
    def _send_email(self, recipient: str, subject: str, body: str, priority: str = 'normal') -> bool:
        """
        Send email using SMTP
        
        Args:
            recipient: Email address
            subject: Email subject
            body: Email body
            priority: Email priority (normal, high)
            
        Returns:
            True if sent successfully
        """
        
        try:
            # Get email configuration from app config
            smtp_server = self.app.config.get('SMTP_SERVER', 'localhost')
            smtp_port = self.app.config.get('SMTP_PORT', 587)
            smtp_username = self.app.config.get('SMTP_USERNAME')
            smtp_password = self.app.config.get('SMTP_PASSWORD')
            sender_email = self.app.config.get('SENDER_EMAIL', 'noreply@itowvms.com')
            use_tls = self.app.config.get('SMTP_USE_TLS', True)
            
            # Create message
            msg = MIMEMultipart()
            msg['From'] = sender_email
            msg['To'] = recipient
            msg['Subject'] = subject
            
            if priority == 'high':
                msg['X-Priority'] = '1'
                msg['X-MSMail-Priority'] = 'High'
            
            # Add body
            msg.attach(MIMEText(body, 'html' if '<html>' in body.lower() else 'plain'))
            
            # Send email
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                if use_tls:
                    server.starttls()
                
                if smtp_username and smtp_password:
                    server.login(smtp_username, smtp_password)
                
                text = msg.as_string()
                server.sendmail(sender_email, recipient, text)
            
            logger.info(f"Email sent successfully to {recipient}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending email to {recipient}: {e}")
            return False
    
    def get_queue_status(self) -> Dict[str, int]:
        """
        Get notification queue statistics
        
        Returns:
            Dictionary with queue statistics
        """
        
        stats = {
            'pending': 0,
            'sent': 0,
            'failed': 0,
            'total': 0
        }
        
        try:
            from app.core.database import get_db_connection
            
            db = get_db_connection()
            cursor = db.cursor()
            
            cursor.execute("""
                SELECT status, COUNT(*) as count
                FROM notification_queue
                GROUP BY status
            """)
            
            for row in cursor.fetchall():
                stats[row['status']] = row['count']
                stats['total'] += row['count']
        
        except Exception as e:
            logger.error(f"Error getting queue status: {e}")
        
        return stats
    
    def cleanup_old_notifications(self, days_old: int = 30) -> int:
        """
        Remove old notifications from the queue
        
        Args:
            days_old: Remove notifications older than this many days
            
        Returns:
            Number of notifications removed
        """
        
        removed_count = 0
        
        try:
            cutoff_date = datetime.now() - timedelta(days=days_old)
            
            with self.app.app_context():
                if hasattr(self.app, 'db'):
                    cursor = self.app.db.cursor()
                    
                    cursor.execute("""
                        DELETE FROM notification_queue
                        WHERE created_date < ? AND status IN ('sent', 'failed')
                    """, (cutoff_date.isoformat(),))
                    
                    removed_count = cursor.rowcount
                    self.app.db.commit()
                    
                    logger.info(f"Cleaned up {removed_count} old notifications")
        
        except Exception as e:
            logger.error(f"Error cleaning up old notifications: {e}")
        
        return removed_count


def init_notifications(app):
    """Initialize notification system"""
    notification_manager = NotificationManager(app)
    app.notification_manager = notification_manager
    return notification_manager
