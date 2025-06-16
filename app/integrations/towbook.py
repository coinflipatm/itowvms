77"""
Enhanced TowBook Integration Module
Connects existing scraper with enhanced architecture
"""

import logging
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

# Add root directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from app.core.database import VehicleRepository
from scraper import TowBookScraper

# Configure logging
towbook_logger = logging.getLogger('towbook')

@dataclass
class TowBookImportResult:
    """Result of TowBook import operation"""
    success: bool
    vehicles_imported: int
    vehicles_updated: int
    vehicles_skipped: int
    error_message: Optional[str] = None
    duration_seconds: Optional[float] = None

class EnhancedTowBookIntegration:
    """
    Enhanced TowBook integration that bridges legacy scraper with new architecture
    """
    
    def __init__(self, app=None):
        self.app = app
        self.vehicle_repo = None
        self.logger = towbook_logger
        
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize with Flask app"""
        self.app = app
        
        # Initialize vehicle repository
        from app.core.database import DatabaseManager
        db_manager = DatabaseManager(app)
        self.vehicle_repo = VehicleRepository(db_manager)
        
        self.logger.info("Enhanced TowBook integration initialized")
    
    def import_vehicles(self, username: str, password: str, 
                       start_date: str, end_date: str, 
                       test_mode: bool = False) -> TowBookImportResult:
        """
        Import vehicles from TowBook using enhanced architecture
        
        Args:
            username: TowBook username
            password: TowBook password  
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            test_mode: If True, use test mode with simulated data
            
        Returns:
            TowBookImportResult with import statistics
        """
        
        start_time = datetime.now()
        
        try:
            self.logger.info(f"Starting TowBook import: {start_date} to {end_date} (test_mode: {test_mode})")
            
            # Initialize TowBook scraper
            scraper = TowBookScraper(
                username=username,
                password=password,
                test_mode=test_mode
            )
            
            # Execute scraping
            success, message = scraper.scrape_data(start_date, end_date)
            
            if not success:
                return TowBookImportResult(
                    success=False,
                    vehicles_imported=0,
                    vehicles_updated=0,
                    vehicles_skipped=0,
                    error_message=message
                )
            
            # Get import statistics from scraper progress
            progress = scraper.get_progress()
            processed_count = progress.get('processed', 0)
            
            # Get actual counts from database
            new_vehicles = self._count_recent_vehicles(start_time)
            
            duration = (datetime.now() - start_time).total_seconds()
            
            result = TowBookImportResult(
                success=True,
                vehicles_imported=new_vehicles.get('new', 0),
                vehicles_updated=new_vehicles.get('updated', 0),
                vehicles_skipped=max(0, processed_count - new_vehicles.get('total', 0)),
                duration_seconds=duration
            )
            
            self.logger.info(f"TowBook import completed: {result}")
            
            # Trigger workflow engine analysis for new vehicles
            if hasattr(self.app, 'workflow_engine') and result.vehicles_imported > 0:
                self._trigger_workflow_analysis()
            
            return result
            
        except Exception as e:
            self.logger.error(f"TowBook import failed: {e}", exc_info=True)
            
            duration = (datetime.now() - start_time).total_seconds()
            
            return TowBookImportResult(
                success=False,
                vehicles_imported=0,
                vehicles_updated=0,
                vehicles_skipped=0,
                error_message=str(e),
                duration_seconds=duration
            )
    
    def get_import_progress(self, scraper_instance: TowBookScraper = None) -> Dict:
        """
        Get current import progress
        
        Args:
            scraper_instance: Optional scraper instance to get progress from
            
        Returns:
            Progress dictionary with percentage, status, etc.
        """
        
        if scraper_instance:
            return scraper_instance.get_progress()
        
        # Return default progress if no scraper instance
        return {
            "percentage": 0,
            "is_running": False,
            "processed": 0,
            "total": 0,
            "status": "Not currently importing",
            "error": None
        }
    
    def validate_credentials(self, username: str, password: str) -> Tuple[bool, str]:
        """
        Validate TowBook credentials without full import
        
        Args:
            username: TowBook username
            password: TowBook password
            
        Returns:
            Tuple of (success, message)
        """
        
        try:
            self.logger.info("Validating TowBook credentials")
            
            scraper = TowBookScraper(username=username, password=password)
            
            # Initialize driver and attempt login
            scraper._init_driver(headless=True)
            success = scraper.login()
            
            # Cleanup
            if scraper.driver:
                scraper.driver.quit()
            
            if success:
                self.logger.info("TowBook credentials validated successfully")
                return True, "Credentials validated successfully"
            else:
                error = scraper.progress.get('error', 'Login failed')
                self.logger.warning(f"TowBook credential validation failed: {error}")
                return False, error
                
        except Exception as e:
            self.logger.error(f"Credential validation error: {e}")
            return False, f"Validation error: {str(e)}"
    
    def get_available_date_range(self) -> Dict[str, str]:
        """
        Get recommended date range for imports
        
        Returns:
            Dictionary with start_date and end_date suggestions
        """
        
        # Get the most recent vehicle date from database
        try:
            latest_vehicle = self.vehicle_repo.get_latest_vehicle()
            
            if latest_vehicle and latest_vehicle.get('tow_date') and latest_vehicle.get('tow_date') != 'N/A':
                # Start from day after latest vehicle
                latest_date = datetime.strptime(latest_vehicle['tow_date'], '%Y-%m-%d')
                start_date = latest_date + timedelta(days=1)
            else:
                # Default to last 7 days if no vehicles found or invalid date
                start_date = datetime.now() - timedelta(days=7)
            
            end_date = datetime.now()
            
            return {
                'start_date': start_date.strftime('%Y-%m-%d'),
                'end_date': end_date.strftime('%Y-%m-%d'),
                'suggested_reason': 'Based on latest vehicle in database' if latest_vehicle else 'Default recent range'
            }
            
        except Exception as e:
            self.logger.error(f"Error getting date range: {e}")
            
            # Fallback to last 7 days
            end_date = datetime.now()
            start_date = end_date - timedelta(days=7)
            
            return {
                'start_date': start_date.strftime('%Y-%m-%d'),
                'end_date': end_date.strftime('%Y-%m-%d'),
                'suggested_reason': 'Fallback range due to error'
            }
    
    def _count_recent_vehicles(self, since_time: datetime) -> Dict[str, int]:
        """
        Count vehicles added/updated since given time
        
        Args:
            since_time: DateTime to count from
            
        Returns:
            Dictionary with counts
        """
        
        try:
            # Get vehicles updated since start time
            recent_vehicles = self.vehicle_repo.get_vehicles_updated_since(
                since_time.strftime('%Y-%m-%d %H:%M:%S')
            )
            
            new_count = 0
            updated_count = 0
            
            for vehicle in recent_vehicles:
                # Consider vehicles with 'New' status as newly imported
                if vehicle.get('status') == 'New':
                    new_count += 1
                else:
                    updated_count += 1
            
            return {
                'new': new_count,
                'updated': updated_count,
                'total': len(recent_vehicles)
            }
            
        except Exception as e:
            self.logger.error(f"Error counting recent vehicles: {e}")
            return {'new': 0, 'updated': 0, 'total': 0}
    
    def _trigger_workflow_analysis(self):
        """
        Trigger workflow engine to analyze newly imported vehicles
        """
        
        try:
            if hasattr(self.app, 'workflow_engine'):
                engine = self.app.workflow_engine
                
                # Get new vehicles that need analysis
                new_vehicles = self.vehicle_repo.get_vehicles_by_status('New')
                
                self.logger.info(f"Triggering workflow analysis for {len(new_vehicles)} new vehicles")
                
                # This could trigger priority calculations, notifications, etc.
                # For now, just log the analysis
                priorities = engine.get_daily_priorities()
                urgent_count = len(priorities.get('urgent', []))
                
                if urgent_count > 0:
                    self.logger.warning(f"Import resulted in {urgent_count} vehicles requiring urgent attention")
                
            else:
                self.logger.warning("Workflow engine not available for post-import analysis")
                
        except Exception as e:
            self.logger.error(f"Error triggering workflow analysis: {e}")

# Global integration instance
towbook_integration = EnhancedTowBookIntegration()

def init_towbook_integration(app):
    """Initialize TowBook integration with Flask app"""
    towbook_integration.init_app(app)
    return towbook_integration
