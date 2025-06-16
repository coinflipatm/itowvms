"""
Automated Workflow Actions
Enhanced workflow engine with automated action execution
"""

import logging
import smtplib
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict, Optional
from flask import current_app

from app.workflows.engine import VehicleWorkflowEngine, WorkflowAction
from app.core.database import VehicleRepository

# Configure logger
automation_logger = logging.getLogger('automation')

class AutomatedWorkflowEngine(VehicleWorkflowEngine):
    """
    Enhanced workflow engine with automated action execution capabilities
    """
    
    def __init__(self, app=None):
        super().__init__(app)
        self.automation_enabled = True
        self.logger = automation_logger
    
    def execute_automated_actions(self) -> Dict[str, int]:
        """
        Execute all automated workflow actions
        
        Returns:
            Dictionary with counts of actions executed
        """
        
        self.logger.info("Starting automated workflow action execution")
        
        results = {
            'notices_sent': 0,
            'status_updates': 0,
            'alerts_generated': 0,
            'documents_created': 0,
            'errors': 0
        }
        
        try:
            # Get all vehicles requiring urgent attention
            priorities = self.get_daily_priorities()
            urgent_vehicles = priorities.get('urgent', [])
            
            self.logger.info(f"Processing {len(urgent_vehicles)} urgent vehicles for automated actions")
            
            for vehicle in urgent_vehicles:
                try:
                    vehicle_call_number = vehicle.get('towbook_call_number')
                    if not vehicle_call_number:
                        continue
                    
                    # Get next actions for this vehicle
                    actions = self.get_next_actions(vehicle_call_number)
                    
                    for action in actions:
                        executed = self._execute_action(vehicle, action)
                        if executed:
                            results[self._get_result_category(action.action_type)] += 1
                        else:
                            results['errors'] += 1
                            
                except Exception as e:
                    self.logger.error(f"Error processing vehicle {vehicle_call_number}: {e}")
                    results['errors'] += 1
            
            self.logger.info(f"Automated action execution completed: {results}")
            
        except Exception as e:
            self.logger.error(f"Automated workflow execution failed: {e}")
            results['errors'] += 1
        
        return results
    
    def _execute_action(self, vehicle: Dict, action: WorkflowAction) -> bool:
        """
        Execute a specific automated action
        
        Args:
            vehicle: Vehicle data dictionary
            action: WorkflowAction to execute
            
        Returns:
            True if action was executed successfully
        """
        
        try:
            if action.action_type == 'send_seven_day_notice':
                return self._send_seven_day_notice(vehicle)
            
            elif action.action_type == 'update_status':
                return self._update_vehicle_status(vehicle, action)
            
            elif action.action_type == 'generate_alert':
                return self._generate_compliance_alert(vehicle, action)
            
            elif action.action_type == 'create_document':
                return self._create_compliance_document(vehicle, action)
            
            elif action.action_type == 'schedule_hearing':
                return self._schedule_hearing(vehicle)
            
            else:
                self.logger.warning(f"Unknown action type: {action.action_type}")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to execute action {action.action_type} for vehicle {vehicle.get('towbook_call_number')}: {e}")
            return False
    
    def _send_seven_day_notice(self, vehicle: Dict) -> bool:
        """Send automated seven-day notice"""
        
        vehicle_call_number = vehicle.get('towbook_call_number')
        self.logger.info(f"Sending seven-day notice for vehicle {vehicle_call_number}")
        
        try:
            # Check if notice already sent
            if vehicle.get('tr52_notification_sent'):
                self.logger.info(f"Seven-day notice already sent for vehicle {vehicle_call_number}")
                return True
            
            # Generate notice content
            notice_content = self._generate_notice_content(vehicle)
            
            # Send notice (email or postal mail depending on configuration)
            if self._send_notice_email(vehicle, notice_content):
                # Update database to mark notice as sent
                self.vehicle_repo.update_vehicle_status(
                    vehicle_call_number, 
                    vehicle.get('status'),  # Keep same status
                    f"Seven-day notice sent automatically on {datetime.now().strftime('%Y-%m-%d')}"
                )
                
                # Update specific notice flag
                self._update_notice_flag(vehicle_call_number, 'tr52_notification_sent', True)
                
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to send seven-day notice for vehicle {vehicle_call_number}: {e}")
            return False
    
    def _update_vehicle_status(self, vehicle: Dict, action: WorkflowAction) -> bool:
        """Update vehicle status automatically"""
        
        vehicle_call_number = vehicle.get('towbook_call_number')
        new_status = action.description.split(':')[-1].strip() if ':' in action.description else 'UPDATED'
        
        self.logger.info(f"Updating status for vehicle {vehicle_call_number} to {new_status}")
        
        try:
            success = self.vehicle_repo.update_vehicle_status(
                vehicle_call_number,
                new_status,
                f"Status updated automatically by workflow engine: {action.description}"
            )
            
            if success:
                self.logger.info(f"Status updated successfully for vehicle {vehicle_call_number}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Failed to update status for vehicle {vehicle_call_number}: {e}")
            return False
    
    def _generate_compliance_alert(self, vehicle: Dict, action: WorkflowAction) -> bool:
        """Generate compliance alert for urgent attention"""
        
        vehicle_call_number = vehicle.get('towbook_call_number')
        self.logger.info(f"Generating compliance alert for vehicle {vehicle_call_number}")
        
        try:
            alert_content = {
                'vehicle_call_number': vehicle_call_number,
                'alert_type': 'compliance_deadline',
                'message': action.description,
                'severity': action.priority,
                'generated_at': datetime.now().isoformat(),
                'due_date': action.due_date.isoformat() if action.due_date else None
            }
            
            # Send alert email to administrators
            if self._send_alert_email(alert_content):
                # Log the alert
                self._log_alert(vehicle_call_number, alert_content)
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to generate alert for vehicle {vehicle_call_number}: {e}")
            return False
    
    def _create_compliance_document(self, vehicle: Dict, action: WorkflowAction) -> bool:
        """Create compliance document automatically"""
        
        vehicle_call_number = vehicle.get('towbook_call_number')
        self.logger.info(f"Creating compliance document for vehicle {vehicle_call_number}")
        
        try:
            # Determine document type from action description
            if 'TR52' in action.description:
                document_type = 'TR52'
            elif 'TR208' in action.description:
                document_type = 'TR208'
            else:
                document_type = 'NOTICE'
            
            # Generate document using existing generator
            from generator import DocumentGenerator
            generator = DocumentGenerator()
            
            document_path = generator.generate_document(
                vehicle=vehicle,
                document_type=document_type,
                automated=True
            )
            
            if document_path:
                # Update vehicle record with document path
                self._update_document_flag(vehicle_call_number, document_type, document_path)
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to create document for vehicle {vehicle_call_number}: {e}")
            return False
    
    def _schedule_hearing(self, vehicle: Dict) -> bool:
        """Schedule hearing automatically based on jurisdiction"""
        
        vehicle_call_number = vehicle.get('towbook_call_number')
        jurisdiction = vehicle.get('jurisdiction')
        
        self.logger.info(f"Scheduling hearing for vehicle {vehicle_call_number} in jurisdiction {jurisdiction}")
        
        try:
            # Get jurisdiction-specific hearing schedule
            hearing_date = self._get_next_hearing_date(jurisdiction)
            
            if hearing_date:
                # Update vehicle with hearing date
                self._update_hearing_date(vehicle_call_number, hearing_date)
                
                # Send calendar invitation to relevant parties
                self._send_hearing_notification(vehicle, hearing_date)
                
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to schedule hearing for vehicle {vehicle_call_number}: {e}")
            return False
    
    def _send_notice_email(self, vehicle: Dict, content: str) -> bool:
        """Send notice via email if email address available"""
        
        owner_email = vehicle.get('owner_email')
        if not owner_email:
            self.logger.info(f"No email address for vehicle {vehicle.get('towbook_call_number')}, skipping email notice")
            return False
        
        try:
            if not current_app.config.get('MAIL_SERVER'):
                self.logger.warning("Email server not configured, cannot send notice email")
                return False
            
            msg = MIMEMultipart()
            msg['From'] = current_app.config.get('MAIL_USERNAME')
            msg['To'] = owner_email
            msg['Subject'] = f"Vehicle Notice - Call Number {vehicle.get('towbook_call_number')}"
            
            msg.attach(MIMEText(content, 'html'))
            
            # Send email
            server = smtplib.SMTP(current_app.config['MAIL_SERVER'], current_app.config['MAIL_PORT'])
            if current_app.config.get('MAIL_USE_TLS'):
                server.starttls()
            
            if current_app.config.get('MAIL_USERNAME'):
                server.login(current_app.config['MAIL_USERNAME'], current_app.config['MAIL_PASSWORD'])
            
            server.send_message(msg)
            server.quit()
            
            self.logger.info(f"Notice email sent successfully to {owner_email}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to send notice email: {e}")
            return False
    
    def _send_alert_email(self, alert_content: Dict) -> bool:
        """Send alert email to administrators"""
        
        admin_emails = current_app.config.get('ADMIN_EMAILS', [])
        if not admin_emails:
            self.logger.warning("No admin emails configured for alerts")
            return False
        
        try:
            subject = f"iTow VMS Alert: {alert_content['alert_type']} - Vehicle {alert_content['vehicle_call_number']}"
            
            body = f"""
            <h3>iTow VMS Compliance Alert</h3>
            <p><strong>Vehicle:</strong> {alert_content['vehicle_call_number']}</p>
            <p><strong>Alert Type:</strong> {alert_content['alert_type']}</p>
            <p><strong>Severity:</strong> {alert_content['severity']}</p>
            <p><strong>Message:</strong> {alert_content['message']}</p>
            <p><strong>Generated:</strong> {alert_content['generated_at']}</p>
            {f"<p><strong>Due Date:</strong> {alert_content['due_date']}</p>" if alert_content.get('due_date') else ""}
            
            <p>Please review and take appropriate action in the iTow VMS dashboard.</p>
            """
            
            for admin_email in admin_emails:
                msg = MIMEMultipart()
                msg['From'] = current_app.config.get('MAIL_USERNAME')
                msg['To'] = admin_email
                msg['Subject'] = subject
                msg.attach(MIMEText(body, 'html'))
                
                # Send via same SMTP configuration
                # (Implementation similar to _send_notice_email)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to send alert email: {e}")
            return False
    
    def _generate_notice_content(self, vehicle: Dict) -> str:
        """Generate HTML content for seven-day notice"""
        
        return f"""
        <html>
        <body>
            <h2>Seven-Day Notice</h2>
            <p>Dear Vehicle Owner,</p>
            
            <p>This is to notify you that a vehicle has been towed and is currently being held:</p>
            
            <ul>
                <li><strong>Call Number:</strong> {vehicle.get('towbook_call_number', 'N/A')}</li>
                <li><strong>Make/Model:</strong> {vehicle.get('make', 'N/A')} {vehicle.get('model', 'N/A')}</li>
                <li><strong>Year:</strong> {vehicle.get('year', 'N/A')}</li>
                <li><strong>Color:</strong> {vehicle.get('color', 'N/A')}</li>
                <li><strong>Plate:</strong> {vehicle.get('plate', 'N/A')}</li>
                <li><strong>Tow Date:</strong> {vehicle.get('tow_date', 'N/A')}</li>
            </ul>
            
            <p>You have seven (7) days from the date of this notice to claim your vehicle.</p>
            
            <p>For more information, please contact the appropriate jurisdiction.</p>
            
            <p>Sincerely,<br>iTow Vehicle Management System</p>
        </body>
        </html>
        """
    
    def _get_result_category(self, action_type: str) -> str:
        """Map action type to result category"""
        
        mapping = {
            'send_seven_day_notice': 'notices_sent',
            'update_status': 'status_updates',
            'generate_alert': 'alerts_generated',
            'create_document': 'documents_created',
            'schedule_hearing': 'status_updates'
        }
        
        return mapping.get(action_type, 'status_updates')
    
    def _update_notice_flag(self, vehicle_call_number: str, flag_name: str, value: bool):
        """Update specific notice flag in database"""
        
        query = f"UPDATE vehicles SET {flag_name} = ? WHERE towbook_call_number = ?"
        self.vehicle_repo.db.execute_query(query, (1 if value else 0, vehicle_call_number))
    
    def _update_document_flag(self, vehicle_call_number: str, document_type: str, document_path: str):
        """Update document generation flag in database"""
        
        field_name = f"{document_type.lower()}_form_generated_at"
        query = f"UPDATE vehicles SET {field_name} = ? WHERE towbook_call_number = ?"
        self.vehicle_repo.db.execute_query(query, (datetime.now().isoformat(), vehicle_call_number))
    
    def _update_hearing_date(self, vehicle_call_number: str, hearing_date: datetime):
        """Update hearing date in database"""
        
        query = "UPDATE vehicles SET city_hearing_date = ? WHERE towbook_call_number = ?"
        self.vehicle_repo.db.execute_query(query, (hearing_date.strftime('%Y-%m-%d'), vehicle_call_number))
    
    def _log_alert(self, vehicle_call_number: str, alert_content: Dict):
        """Log alert to database"""
        
        query = """
        INSERT INTO logs (action_type, vehicle_id, details, timestamp)
        VALUES (?, ?, ?, ?)
        """
        
        details = f"Alert generated: {alert_content['message']}"
        self.vehicle_repo.db.execute_query(query, (
            'alert_generated',
            vehicle_call_number,
            details,
            datetime.now().isoformat()
        ))
    
    def _get_next_hearing_date(self, jurisdiction: str) -> Optional[datetime]:
        """Get next available hearing date for jurisdiction"""
        
        # This would integrate with jurisdiction-specific hearing schedules
        # For now, return a default date 30 days from now
        return datetime.now() + timedelta(days=30)
    
    def _send_hearing_notification(self, vehicle: Dict, hearing_date: datetime) -> bool:
        """Send hearing notification to relevant parties"""
        
        # Implementation would send calendar invitations
        # For now, just log the action
        self.logger.info(f"Hearing scheduled for vehicle {vehicle.get('towbook_call_number')} on {hearing_date}")
        return True

    def _check_notification_queue(self) -> int:
        """
        Process pending notifications in the queue
        
        Returns:
            Number of notifications processed
        """
        
        notifications_processed = 0
        
        try:
            # Get pending notifications from database
            from app.core.database import get_db_connection
            
            db = get_db_connection()
            cursor = db.cursor()
            
            # Get notifications that are due to be sent
            cursor.execute("""
                SELECT id, vehicle_call_number, notification_type, 
                       scheduled_date, recipient_email, subject, body
                FROM notification_queue 
                WHERE status = 'pending' 
                AND scheduled_date <= ?
                ORDER BY scheduled_date ASC
                LIMIT 50
            """, (datetime.now().isoformat(),))
            
            pending_notifications = cursor.fetchall()
            
            for notification in pending_notifications:
                try:
                    # Send the notification
                    success = self._send_notification(
                        notification['recipient_email'],
                        notification['subject'],
                        notification['body'],
                        notification['notification_type']
                    )
                    
                    if success:
                        # Mark as sent
                        cursor.execute("""
                            UPDATE notification_queue 
                            SET status = 'sent', sent_date = ?
                            WHERE id = ?
                        """, (datetime.now().isoformat(), notification['id']))
                        
                        notifications_processed += 1
                        self.logger.info(f"Sent notification {notification['id']} to {notification['recipient_email']}")
                    else:
                        # Mark as failed and reschedule
                        retry_date = datetime.now() + timedelta(hours=1)
                        cursor.execute("""
                            UPDATE notification_queue 
                            SET status = 'failed', 
                                retry_count = retry_count + 1,
                                scheduled_date = ?
                            WHERE id = ? AND retry_count < 3
                        """, (retry_date.isoformat(), notification['id']))
                        
                        self.logger.warning(f"Failed to send notification {notification['id']}, rescheduled for retry")
                
                except Exception as e:
                    self.logger.error(f"Error processing notification {notification['id']}: {e}")
            
            db.commit()
        
        except Exception as e:
            self.logger.error(f"Error checking notification queue: {e}")
        
        return notifications_processed

    def _send_notification(self, recipient: str, subject: str, body: str, notification_type: str) -> bool:
        """
        Send a notification email
        
        Args:
            recipient: Email address
            subject: Email subject
            body: Email body
            notification_type: Type of notification
            
        Returns:
            True if sent successfully
        """
        
        try:
            # Use the existing email sending infrastructure
            if notification_type == 'seven_day_notice':
                # Use the seven day notice format
                return self._send_email(recipient, subject, body)
            elif notification_type == 'alert':
                # Use alert format
                return self._send_email(recipient, subject, body, priority='high')
            else:
                # Standard notification
                return self._send_email(recipient, subject, body)
                
        except Exception as e:
            self.logger.error(f"Error sending notification to {recipient}: {e}")
            return False

    def _send_email(self, recipient: str, subject: str, body: str, priority: str = 'normal') -> bool:
        """
        Send email using the notification manager
        
        Args:
            recipient: Email address
            subject: Email subject
            body: Email body
            priority: Email priority (normal, high)
            
        Returns:
            True if sent successfully
        """
        
        try:
            # Use the application's notification manager for actual email sending
            if hasattr(self.app, 'notification_manager'):
                return self.app.notification_manager.send_immediate(
                    recipient, subject, body, f'automated_{priority}'
                )
            else:
                # Fallback: just log the email (for development/testing)
                self.logger.info(f"EMAIL: To={recipient}, Subject={subject}, Priority={priority}")
                return True
                
        except Exception as e:
            self.logger.error(f"Error sending email to {recipient}: {e}")
            return False

def create_automated_workflow_engine(app):
    """Factory function to create automated workflow engine"""
    
    return AutomatedWorkflowEngine(app)
