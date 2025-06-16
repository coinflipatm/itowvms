"""
Vehicle Lifecycle Workflow Engine
Centralized workflow management to replace scattered status logic
"""

from enum import Enum
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import logging
from app.core.database import VehicleRepository, db_manager

class VehicleStage(Enum):
    """Clear disposition stages to track vehicle progress"""
    INITIAL_HOLD = "initial_hold"
    PENDING_NOTIFICATION = "pending_notification"
    NOTICE_SENT = "notice_sent"
    APPROVED_AUCTION = "approved_auction"
    APPROVED_SCRAP = "approved_scrap"
    SCHEDULED_PICKUP = "scheduled_pickup"
    PENDING_REMOVAL = "pending_removal"
    DISPOSED = "disposed"

class WorkflowAction:
    """Represents an action that needs to be taken for a vehicle"""
    
    def __init__(self, action_type: str, priority: str, due_date: datetime, 
                 vehicle_id: int, description: str, automated: bool = False):
        self.action_type = action_type
        self.priority = priority  # 'urgent', 'high', 'medium', 'low'
        self.due_date = due_date
        self.vehicle_id = vehicle_id
        self.description = description
        self.automated = automated

class VehicleWorkflowEngine:
    """
    Single source of truth for vehicle progression logic
    Replaces scattered status management throughout the codebase
    """
    
    def __init__(self, app=None):
        self.app = app
        self.vehicle_repo = VehicleRepository(db_manager)
        self.workflow_logger = logging.getLogger('workflow')
        
        # Business rules configuration
        self.SEVEN_DAY_PERIOD = timedelta(days=7)
        self.AUCTION_SCHEDULE_WINDOW = timedelta(days=3)
        self.SCRAP_SCHEDULE_WINDOW = timedelta(days=1)
        
    def get_daily_priorities(self) -> Dict[str, List[Dict]]:
        """
        Get prioritized list of actions needed today
        Replaces manual morning checking with automated priority system
        """
        
        priorities = {
            'urgent': [],
            'today': [],
            'upcoming': []
        }
        
        # Get all active vehicles
        active_vehicles = self._get_active_vehicles()
        
        for vehicle in active_vehicles:
            actions = self.get_next_actions(vehicle['towbook_call_number'])
            
            for action in actions:
                if action.priority == 'urgent':
                    priorities['urgent'].append(self._format_action_for_dashboard(action, vehicle))
                elif action.due_date.date() == datetime.now().date():
                    priorities['today'].append(self._format_action_for_dashboard(action, vehicle))
                elif action.due_date.date() <= (datetime.now() + timedelta(days=3)).date():
                    priorities['upcoming'].append(self._format_action_for_dashboard(action, vehicle))
        
        return priorities
    
    def get_next_actions(self, vehicle_call_number: str) -> List[WorkflowAction]:
        """
        Returns prioritized list of actions needed for vehicle
        Business logic consolidated here instead of scattered
        """
        
        vehicle = self.vehicle_repo.get_vehicle_by_call_number(vehicle_call_number)
        if not vehicle:
            return []
        
        actions = []
        current_stage = self._get_current_stage(vehicle)
        
        # Initial hold period logic
        if current_stage == VehicleStage.INITIAL_HOLD:
            days_held = self._calculate_days_held(vehicle)
            
            if days_held >= 7 and not vehicle.get('seven_day_notice_sent'):
                actions.append(WorkflowAction(
                    action_type='send_seven_day_notice',
                    priority='urgent' if days_held > 8 else 'high',
                    due_date=datetime.now(),
                    vehicle_id=vehicle_call_number,
                    description=f"Send 7-day abandonment notice (held {days_held} days)",
                    automated=True
                ))
            elif days_held < 7:
                notice_due_date = datetime.strptime(vehicle['tow_date'], '%Y-%m-%d') + self.SEVEN_DAY_PERIOD
                actions.append(WorkflowAction(
                    action_type='pending_seven_day_notice',
                    priority='medium',
                    due_date=notice_due_date,
                    vehicle_id=vehicle_call_number,
                    description=f"7-day notice due on {notice_due_date.strftime('%m/%d/%Y')}"
                ))
        
        # Notice sent - waiting for response period
        elif current_stage == VehicleStage.NOTICE_SENT:
            notice_date = datetime.strptime(vehicle.get('seven_day_notice_sent', vehicle['tow_date']), '%Y-%m-%d')
            response_deadline = notice_date + self.SEVEN_DAY_PERIOD
            
            if datetime.now() >= response_deadline:
                actions.append(WorkflowAction(
                    action_type='approve_for_disposition',
                    priority='high',
                    due_date=datetime.now(),
                    vehicle_id=vehicle_call_number,
                    description="Vehicle ready for auction/scrap approval"
                ))
            else:
                actions.append(WorkflowAction(
                    action_type='waiting_response_period',
                    priority='low',
                    due_date=response_deadline,
                    vehicle_id=vehicle_call_number,
                    description=f"Response period ends {response_deadline.strftime('%m/%d/%Y')}"
                ))
        
        # Approved for disposition
        elif current_stage == VehicleStage.APPROVED_AUCTION:
            actions.append(WorkflowAction(
                action_type='schedule_auction_pickup',
                priority='medium',
                due_date=datetime.now() + self.AUCTION_SCHEDULE_WINDOW,
                vehicle_id=vehicle_call_number,
                description="Schedule vehicle for auction pickup"
            ))
        
        elif current_stage == VehicleStage.APPROVED_SCRAP:
            actions.append(WorkflowAction(
                action_type='schedule_scrap_pickup',
                priority='medium',
                due_date=datetime.now() + self.SCRAP_SCHEDULE_WINDOW,
                vehicle_id=vehicle_call_number,
                description="Schedule vehicle for scrap pickup"
            ))
        
        # Scheduled pickup
        elif current_stage == VehicleStage.SCHEDULED_PICKUP:
            pickup_date = self._get_scheduled_pickup_date(vehicle_call_number)
            if pickup_date and pickup_date <= datetime.now().date():
                actions.append(WorkflowAction(
                    action_type='confirm_pickup',
                    priority='high',
                    due_date=datetime.now(),
                    vehicle_id=vehicle_call_number,
                    description="Confirm vehicle pickup completion"
                ))
        
        return actions
    
    def advance_stage(self, vehicle_id: int, new_stage: VehicleStage, 
                     notes: str = "", user_id: str = None) -> bool:
        """
        Controlled stage advancement with validation and audit trail
        """
        
        try:
            vehicle = self.vehicle_repo.get_vehicle_by_id(vehicle_id)
            if not vehicle:
                return False
            
            current_stage = self._get_current_stage(vehicle)
            
            # Validate stage transition
            if not self._is_valid_transition(current_stage, new_stage):
                self.workflow_logger.error(f"Invalid stage transition for vehicle {vehicle_id}: {current_stage} -> {new_stage}")
                return False
            
            # Record stage change
            self._record_stage_change(vehicle_id, current_stage, new_stage, notes, user_id)
            
            # Update vehicle status
            status_updated = self.vehicle_repo.update_vehicle_status(
                vehicle_id, new_stage.value, notes
            )
            
            if status_updated:
                self.workflow_logger.info(f"Vehicle {vehicle_id} advanced from {current_stage.value} to {new_stage.value}")
                
                # Trigger any automated actions for new stage
                self._trigger_stage_actions(vehicle_id, new_stage)
                
            return status_updated
            
        except Exception as e:
            self.workflow_logger.error(f"Failed to advance vehicle {vehicle_id} to stage {new_stage}: {e}")
            return False
    
    def process_automated_seven_day_notices(self) -> Dict[str, Any]:
        """
        Process all vehicles needing 7-day notices automatically
        """
        
        vehicles_needing_notices = self.vehicle_repo.get_vehicles_needing_seven_day_notice()
        
        results = {
            'notices_processed': 0,
            'notices_sent': 0,
            'errors': []
        }
        
        for vehicle in vehicles_needing_notices:
            try:
                results['notices_processed'] += 1
                
                # Send automated notice
                notice_sent = self._send_automated_seven_day_notice(vehicle['id'])
                
                if notice_sent:
                    results['notices_sent'] += 1
                    
                    # Advance to next stage
                    self.advance_stage(
                        vehicle['id'], 
                        VehicleStage.NOTICE_SENT,
                        notes="Automated 7-day notice sent",
                        user_id="system"
                    )
                    
            except Exception as e:
                error_msg = f"Failed to process 7-day notice for vehicle {vehicle['id']}: {e}"
                results['errors'].append(error_msg)
                self.workflow_logger.error(error_msg)
        
        return results
    
    def _get_current_stage(self, vehicle: Dict) -> VehicleStage:
        """Determine current workflow stage for vehicle"""
        
        status = vehicle.get('status', '').lower()
        
        # Map database statuses to workflow stages
        stage_mapping = {
            'impounded': VehicleStage.INITIAL_HOLD,
            'initial_hold': VehicleStage.INITIAL_HOLD,
            'notice_sent': VehicleStage.NOTICE_SENT,
            'approved_auction': VehicleStage.APPROVED_AUCTION,
            'approved_scrap': VehicleStage.APPROVED_SCRAP,
            'scheduled_pickup': VehicleStage.SCHEDULED_PICKUP,
            'disposed': VehicleStage.DISPOSED
        }
        
        return stage_mapping.get(status, VehicleStage.INITIAL_HOLD)
    
    def _calculate_days_held(self, vehicle: Dict) -> int:
        """Calculate number of days vehicle has been held"""
        
        date_received = datetime.strptime(vehicle['tow_date'], '%Y-%m-%d')
        return (datetime.now() - date_received).days
    
    def _is_valid_transition(self, current: VehicleStage, new: VehicleStage) -> bool:
        """Validate stage transitions"""
        
        valid_transitions = {
            VehicleStage.INITIAL_HOLD: [VehicleStage.NOTICE_SENT, VehicleStage.DISPOSED],
            VehicleStage.NOTICE_SENT: [VehicleStage.APPROVED_AUCTION, VehicleStage.APPROVED_SCRAP, VehicleStage.DISPOSED],
            VehicleStage.APPROVED_AUCTION: [VehicleStage.SCHEDULED_PICKUP, VehicleStage.DISPOSED],
            VehicleStage.APPROVED_SCRAP: [VehicleStage.SCHEDULED_PICKUP, VehicleStage.DISPOSED],
            VehicleStage.SCHEDULED_PICKUP: [VehicleStage.PENDING_REMOVAL, VehicleStage.DISPOSED],
            VehicleStage.PENDING_REMOVAL: [VehicleStage.DISPOSED]
        }
        
        return new in valid_transitions.get(current, [])
    
    def _record_stage_change(self, vehicle_id: int, old_stage: VehicleStage, 
                           new_stage: VehicleStage, notes: str, user_id: str):
        """Record stage change in lifecycle tracking"""
        
        # Exit current stage
        exit_query = """
        UPDATE vehicle_lifecycle_stages 
        SET exited_date = ?, duration_days = JULIANDAY('now') - JULIANDAY(entered_date)
        WHERE vehicle_id = ? AND stage = ? AND exited_date IS NULL
        """
        db_manager.execute_query(exit_query, (datetime.now(), vehicle_id, old_stage.value))
        
        # Enter new stage
        enter_query = """
        INSERT INTO vehicle_lifecycle_stages 
        (vehicle_id, stage, entered_date, stage_notes)
        VALUES (?, ?, ?, ?)
        """
        db_manager.execute_query(enter_query, (vehicle_id, new_stage.value, datetime.now(), notes))
    
    def _get_active_vehicles(self) -> List[Dict]:
        """Get all vehicles not yet disposed"""
        
        query = """
        SELECT * FROM vehicles 
        WHERE status NOT IN ('RELEASED', 'Released', 'Scrapped', 'Transferred')
        ORDER BY tow_date ASC
        """
        rows = db_manager.fetch_all(query)
        return [dict(row) for row in rows]
    
    def _format_action_for_dashboard(self, action: WorkflowAction, vehicle: Dict) -> Dict:
        """Format action for dashboard display"""
        
        return {
            'vehicle_id': action.vehicle_id,
            'action_type': action.action_type,
            'priority': action.priority,
            'due_date': action.due_date.strftime('%Y-%m-%d'),
            'description': action.description,
            'automated': action.automated,
            'vehicle_info': {
                'make_model': f"{vehicle.get('make', '')} {vehicle.get('model', '')}".strip(),
                'license_plate': vehicle.get('license_plate', ''),
                'call_number': vehicle.get('call_number', ''),
                'jurisdiction': vehicle.get('jurisdiction', '')
            }
        }
    
    def _send_automated_seven_day_notice(self, vehicle_id: int) -> bool:
        """Send automated 7-day notice (placeholder for integration)"""
        
        # This will integrate with the notification system
        # For now, just log the action
        self.workflow_logger.info(f"Automated 7-day notice sent for vehicle {vehicle_id}")
        
        # Record notification
        notification_query = """
        INSERT INTO notification_log 
        (vehicle_id, notification_type, recipient, sent_date, towbook_synced)
        VALUES (?, ?, ?, ?, ?)
        """
        
        vehicle = self.vehicle_repo.get_vehicle_by_id(vehicle_id)
        jurisdiction = vehicle.get('jurisdiction', 'Unknown')
        
        db_manager.execute_query(notification_query, (
            vehicle_id, '7_day_notice', jurisdiction, datetime.now(), False
        ))
        
        return True
    
    def _trigger_stage_actions(self, vehicle_id: int, new_stage: VehicleStage):
        """Trigger automated actions when entering new stage"""
        
        if new_stage == VehicleStage.NOTICE_SENT:
            # Could trigger TowBook sync, document generation, etc.
            pass
        elif new_stage == VehicleStage.APPROVED_AUCTION:
            # Could automatically contact auction houses
            pass
