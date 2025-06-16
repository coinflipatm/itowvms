"""
Advanced Analytics Engine for iTow VMS
Provides real-time business intelligence and operational metrics
"""
import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
import json

@dataclass
class VehicleMetrics:
    """Container for vehicle-related metrics"""
    total_vehicles: int = 0
    active_vehicles: int = 0
    completed_vehicles: int = 0
    urgent_vehicles: int = 0
    average_processing_time: float = 0.0
    total_revenue: float = 0.0
    processing_efficiency: float = 0.0

@dataclass
class OperationalMetrics:
    """Container for operational performance metrics"""
    workflow_completion_rate: float = 0.0
    average_stage_duration: Dict[str, float] = None
    bottleneck_stages: List[str] = None
    resource_utilization: float = 0.0
    automation_success_rate: float = 0.0

@dataclass
class FinancialMetrics:
    """Container for financial analytics"""
    total_revenue: float = 0.0
    total_costs: float = 0.0
    average_vehicle_value: float = 0.0
    profit_margin: float = 0.0
    revenue_trend: List[Tuple[datetime, float]] = None
    cost_per_vehicle: float = 0.0

class AnalyticsEngine:
    """Advanced analytics engine for comprehensive business intelligence"""
    
    def __init__(self, app=None):
        self.app = app
        self.logger = logging.getLogger(__name__)
        
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize analytics engine with Flask application"""
        self.app = app
        app.analytics_engine = self
        
        # Analytics configuration
        self.cache_duration = app.config.get('ANALYTICS_CACHE_DURATION', 300)  # 5 minutes
        self.enable_real_time = app.config.get('ANALYTICS_REAL_TIME', True)
        
        self.logger.info("Analytics Engine initialized")
    
    def get_db_connection(self):
        """Get database connection using app's database utility"""
        if hasattr(self.app, 'get_db_connection'):
            return self.app.get_db_connection()
        else:
            # Fallback to direct connection
            from app.core.database import get_db_connection
            return get_db_connection()
    
    def get_vehicle_metrics(self, timeframe: str = '30d') -> VehicleMetrics:
        """
        Calculate comprehensive vehicle metrics
        
        Args:
            timeframe: Time period for analysis ('7d', '30d', '90d', '1y')
        
        Returns:
            VehicleMetrics object with calculated values
        """
        try:
            db = self.get_db_connection()
            cursor = db.cursor()
            
            # Calculate date range
            end_date = datetime.now()
            if timeframe == '7d':
                start_date = end_date - timedelta(days=7)
            elif timeframe == '30d':
                start_date = end_date - timedelta(days=30)
            elif timeframe == '90d':
                start_date = end_date - timedelta(days=90)
            elif timeframe == '1y':
                start_date = end_date - timedelta(days=365)
            else:
                start_date = end_date - timedelta(days=30)
            
            metrics = VehicleMetrics()
            
            # Total vehicles in timeframe
            cursor.execute('''
                SELECT COUNT(*) FROM vehicles 
                WHERE created_date >= ? OR updated_date >= ?
            ''', (start_date.isoformat(), start_date.isoformat()))
            metrics.total_vehicles = cursor.fetchone()[0]
            
            # Active vehicles (not completed/disposed)
            cursor.execute('''
                SELECT COUNT(*) FROM vehicles 
                WHERE status NOT IN ('DISPOSED', 'RELEASED', 'COMPLETED')
                AND (created_date >= ? OR updated_date >= ?)
            ''', (start_date.isoformat(), start_date.isoformat()))
            metrics.active_vehicles = cursor.fetchone()[0]
            
            # Completed vehicles
            cursor.execute('''
                SELECT COUNT(*) FROM vehicles 
                WHERE status IN ('DISPOSED', 'RELEASED', 'COMPLETED')
                AND (created_date >= ? OR updated_date >= ?)
            ''', (start_date.isoformat(), start_date.isoformat()))
            metrics.completed_vehicles = cursor.fetchone()[0]
            
            # Urgent vehicles (urgency score > 70)
            cursor.execute('''
                SELECT COUNT(*) FROM vehicles 
                WHERE urgency_score > 70
                AND (created_date >= ? OR updated_date >= ?)
            ''', (start_date.isoformat(), start_date.isoformat()))
            metrics.urgent_vehicles = cursor.fetchone()[0]
            
            # Calculate average processing time
            cursor.execute('''
                SELECT AVG(
                    CASE 
                        WHEN status IN ('DISPOSED', 'RELEASED', 'COMPLETED') 
                        THEN (julianday(updated_date) - julianday(created_date))
                        ELSE NULL 
                    END
                ) FROM vehicles 
                WHERE created_date >= ?
            ''', (start_date.isoformat(),))
            
            result = cursor.fetchone()[0]
            metrics.average_processing_time = float(result) if result else 0.0
            
            # Calculate total revenue (if available)
            cursor.execute('''
                SELECT SUM(COALESCE(disposition_value, 0)) FROM vehicles 
                WHERE status IN ('DISPOSED', 'RELEASED') 
                AND created_date >= ?
            ''', (start_date.isoformat(),))
            
            result = cursor.fetchone()[0]
            metrics.total_revenue = float(result) if result else 0.0
            
            # Processing efficiency (completed vs total)
            if metrics.total_vehicles > 0:
                metrics.processing_efficiency = (metrics.completed_vehicles / metrics.total_vehicles) * 100
            
            db.close()
            
            self.logger.info(f"Vehicle metrics calculated for {timeframe}: {metrics.total_vehicles} vehicles")
            return metrics
            
        except Exception as e:
            self.logger.error(f"Error calculating vehicle metrics: {e}")
            return VehicleMetrics()
    
    def get_operational_metrics(self, timeframe: str = '30d') -> OperationalMetrics:
        """
        Calculate operational performance metrics
        
        Args:
            timeframe: Time period for analysis
        
        Returns:
            OperationalMetrics object with performance data
        """
        try:
            db = self.get_db_connection()
            cursor = db.cursor()
            
            # Calculate date range
            end_date = datetime.now()
            if timeframe == '7d':
                start_date = end_date - timedelta(days=7)
            elif timeframe == '30d':
                start_date = end_date - timedelta(days=30)
            elif timeframe == '90d':
                start_date = end_date - timedelta(days=90)
            else:
                start_date = end_date - timedelta(days=30)
            
            metrics = OperationalMetrics()
            
            # Workflow completion rate
            cursor.execute('''
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN status IN ('DISPOSED', 'RELEASED', 'COMPLETED') THEN 1 ELSE 0 END) as completed
                FROM vehicles 
                WHERE created_date >= ?
            ''', (start_date.isoformat(),))
            
            result = cursor.fetchone()
            total, completed = result if result else (0, 0)
            metrics.workflow_completion_rate = (completed / total * 100) if total > 0 else 0.0
            
            # Average stage duration (approximation based on log entries)
            cursor.execute('''
                SELECT 
                    action,
                    AVG(julianday(created_date) - LAG(julianday(created_date)) OVER (
                        PARTITION BY vehicle_id ORDER BY created_date
                    )) as avg_duration
                FROM vehicle_logs 
                WHERE created_date >= ?
                AND action IN ('STATUS_CHANGE', 'DISPOSITION_SET', 'INSPECTION_COMPLETED')
                GROUP BY action
            ''', (start_date.isoformat(),))
            
            stage_durations = {}
            for row in cursor.fetchall():
                action, duration = row
                if duration:
                    stage_durations[action] = float(duration)
            
            metrics.average_stage_duration = stage_durations
            
            # Identify bottleneck stages (stages taking longer than average)
            if stage_durations:
                avg_duration = sum(stage_durations.values()) / len(stage_durations)
                bottlenecks = [stage for stage, duration in stage_durations.items() 
                             if duration > avg_duration * 1.5]
                metrics.bottleneck_stages = bottlenecks
            else:
                metrics.bottleneck_stages = []
            
            # Resource utilization (based on automated actions)
            cursor.execute('''
                SELECT 
                    COUNT(*) as total_actions,
                    SUM(CASE WHEN notes LIKE '%automated%' OR notes LIKE '%system%' THEN 1 ELSE 0 END) as automated_actions
                FROM vehicle_logs 
                WHERE created_date >= ?
            ''', (start_date.isoformat(),))
            
            result = cursor.fetchone()
            total_actions, automated_actions = result if result else (0, 0)
            metrics.automation_success_rate = (automated_actions / total_actions * 100) if total_actions > 0 else 0.0
            
            # Rough resource utilization estimate
            metrics.resource_utilization = min(95.0, metrics.automation_success_rate + 20.0)
            
            db.close()
            
            self.logger.info(f"Operational metrics calculated: {metrics.workflow_completion_rate:.1f}% completion rate")
            return metrics
            
        except Exception as e:
            self.logger.error(f"Error calculating operational metrics: {e}")
            return OperationalMetrics()
    
    def get_financial_metrics(self, timeframe: str = '30d') -> FinancialMetrics:
        """
        Calculate financial performance metrics
        
        Args:
            timeframe: Time period for analysis
        
        Returns:
            FinancialMetrics object with financial data
        """
        try:
            db = self.get_db_connection()
            cursor = db.cursor()
            
            # Calculate date range
            end_date = datetime.now()
            if timeframe == '7d':
                start_date = end_date - timedelta(days=7)
            elif timeframe == '30d':
                start_date = end_date - timedelta(days=30)
            elif timeframe == '90d':
                start_date = end_date - timedelta(days=90)
            else:
                start_date = end_date - timedelta(days=30)
            
            metrics = FinancialMetrics()
            
            # Total revenue from dispositions
            cursor.execute('''
                SELECT SUM(COALESCE(disposition_value, 0)) 
                FROM vehicles 
                WHERE status IN ('DISPOSED', 'RELEASED') 
                AND created_date >= ?
            ''', (start_date.isoformat(),))
            
            result = cursor.fetchone()[0]
            metrics.total_revenue = float(result) if result else 0.0
            
            # Estimated total costs (storage + processing)
            cursor.execute('''
                SELECT 
                    COUNT(*) as vehicle_count,
                    AVG(julianday('now') - julianday(created_date)) as avg_days
                FROM vehicles 
                WHERE created_date >= ?
            ''', (start_date.isoformat(),))
            
            result = cursor.fetchone()
            vehicle_count, avg_days = result if result else (0, 0)
            
            # Estimated costs: $50/day storage + $200 processing per vehicle
            if vehicle_count > 0 and avg_days:
                estimated_storage_cost = vehicle_count * float(avg_days) * 50.0
                estimated_processing_cost = vehicle_count * 200.0
                metrics.total_costs = estimated_storage_cost + estimated_processing_cost
            
            # Average vehicle value
            cursor.execute('''
                SELECT AVG(COALESCE(disposition_value, 0)) 
                FROM vehicles 
                WHERE disposition_value IS NOT NULL 
                AND disposition_value > 0
                AND created_date >= ?
            ''', (start_date.isoformat(),))
            
            result = cursor.fetchone()[0]
            metrics.average_vehicle_value = float(result) if result else 0.0
            
            # Profit margin
            if metrics.total_costs > 0:
                metrics.profit_margin = ((metrics.total_revenue - metrics.total_costs) / metrics.total_revenue) * 100
            
            # Cost per vehicle
            if vehicle_count > 0:
                metrics.cost_per_vehicle = metrics.total_costs / vehicle_count
            
            # Revenue trend (daily data for the timeframe)
            cursor.execute('''
                SELECT 
                    DATE(created_date) as day,
                    SUM(COALESCE(disposition_value, 0)) as daily_revenue
                FROM vehicles 
                WHERE status IN ('DISPOSED', 'RELEASED') 
                AND created_date >= ?
                GROUP BY DATE(created_date)
                ORDER BY day
            ''', (start_date.isoformat(),))
            
            revenue_trend = []
            for row in cursor.fetchall():
                day_str, revenue = row
                day = datetime.strptime(day_str, '%Y-%m-%d')
                revenue_trend.append((day, float(revenue) if revenue else 0.0))
            
            metrics.revenue_trend = revenue_trend
            
            db.close()
            
            self.logger.info(f"Financial metrics calculated: ${metrics.total_revenue:,.2f} revenue, {metrics.profit_margin:.1f}% margin")
            return metrics
            
        except Exception as e:
            self.logger.error(f"Error calculating financial metrics: {e}")
            return FinancialMetrics()
    
    def get_real_time_kpis(self) -> Dict[str, Any]:
        """
        Get real-time key performance indicators for dashboard
        
        Returns:
            Dictionary with current KPI values
        """
        try:
            db = self.get_db_connection()
            cursor = db.cursor()
            
            kpis = {}
            
            # Current active vehicles
            cursor.execute('''
                SELECT COUNT(*) FROM vehicles 
                WHERE status NOT IN ('DISPOSED', 'RELEASED', 'COMPLETED')
            ''')
            kpis['active_vehicles'] = cursor.fetchone()[0]
            
            # Vehicles processed today
            today = datetime.now().date()
            cursor.execute('''
                SELECT COUNT(*) FROM vehicles 
                WHERE DATE(updated_date) = ?
                AND status IN ('DISPOSED', 'RELEASED', 'COMPLETED')
            ''', (today.isoformat(),))
            kpis['processed_today'] = cursor.fetchone()[0]
            
            # Urgent vehicles requiring attention
            cursor.execute('''
                SELECT COUNT(*) FROM vehicles 
                WHERE urgency_score > 70
                AND status NOT IN ('DISPOSED', 'RELEASED', 'COMPLETED')
            ''')
            kpis['urgent_vehicles'] = cursor.fetchone()[0]
            
            # Revenue today
            cursor.execute('''
                SELECT SUM(COALESCE(disposition_value, 0)) FROM vehicles 
                WHERE DATE(updated_date) = ?
                AND status IN ('DISPOSED', 'RELEASED')
            ''', (today.isoformat(),))
            
            result = cursor.fetchone()[0]
            kpis['revenue_today'] = float(result) if result else 0.0
            
            # System efficiency (automated actions in last hour)
            one_hour_ago = datetime.now() - timedelta(hours=1)
            cursor.execute('''
                SELECT COUNT(*) FROM vehicle_logs 
                WHERE created_date >= ?
                AND (notes LIKE '%automated%' OR notes LIKE '%system%')
            ''', (one_hour_ago.isoformat(),))
            kpis['automated_actions_hour'] = cursor.fetchone()[0]
            
            # Average processing time (last 30 days)
            thirty_days_ago = datetime.now() - timedelta(days=30)
            cursor.execute('''
                SELECT AVG(
                    julianday(updated_date) - julianday(created_date)
                ) FROM vehicles 
                WHERE status IN ('DISPOSED', 'RELEASED', 'COMPLETED')
                AND created_date >= ?
            ''', (thirty_days_ago.isoformat(),))
            
            result = cursor.fetchone()[0]
            kpis['avg_processing_days'] = float(result) if result else 0.0
            
            db.close()
            
            # Calculate derived metrics
            kpis['processing_efficiency'] = (kpis['processed_today'] / max(1, kpis['active_vehicles'])) * 100
            kpis['urgency_ratio'] = (kpis['urgent_vehicles'] / max(1, kpis['active_vehicles'])) * 100
            kpis['automation_activity'] = min(100.0, kpis['automated_actions_hour'] * 10)  # Scale for display
            
            kpis['last_updated'] = datetime.now().isoformat()
            
            self.logger.debug(f"Real-time KPIs updated: {kpis['active_vehicles']} active vehicles")
            return kpis
            
        except Exception as e:
            self.logger.error(f"Error calculating real-time KPIs: {e}")
            return {
                'active_vehicles': 0,
                'processed_today': 0,
                'urgent_vehicles': 0,
                'revenue_today': 0.0,
                'automated_actions_hour': 0,
                'avg_processing_days': 0.0,
                'processing_efficiency': 0.0,
                'urgency_ratio': 0.0,
                'automation_activity': 0.0,
                'last_updated': datetime.now().isoformat()
            }
    
    def get_trend_analysis(self, metric: str, timeframe: str = '30d') -> List[Dict[str, Any]]:
        """
        Get trend analysis for specific metrics
        
        Args:
            metric: The metric to analyze ('vehicles', 'revenue', 'efficiency')
            timeframe: Time period for analysis
        
        Returns:
            List of data points for trending
        """
        try:
            db = self.get_db_connection()
            cursor = db.cursor()
            
            # Calculate date range and interval
            end_date = datetime.now()
            if timeframe == '7d':
                start_date = end_date - timedelta(days=7)
                interval = 'hour'
                date_format = '%Y-%m-%d %H:00:00'
            elif timeframe == '30d':
                start_date = end_date - timedelta(days=30)
                interval = 'day'
                date_format = '%Y-%m-%d'
            elif timeframe == '90d':
                start_date = end_date - timedelta(days=90)
                interval = 'day'
                date_format = '%Y-%m-%d'
            else:
                start_date = end_date - timedelta(days=30)
                interval = 'day'
                date_format = '%Y-%m-%d'
            
            trend_data = []
            
            if metric == 'vehicles':
                # Vehicle processing trend
                if interval == 'day':
                    cursor.execute('''
                        SELECT 
                            DATE(created_date) as period,
                            COUNT(*) as created,
                            SUM(CASE WHEN status IN ('DISPOSED', 'RELEASED', 'COMPLETED') THEN 1 ELSE 0 END) as completed
                        FROM vehicles 
                        WHERE created_date >= ?
                        GROUP BY DATE(created_date)
                        ORDER BY period
                    ''', (start_date.isoformat(),))
                else:
                    cursor.execute('''
                        SELECT 
                            strftime('%Y-%m-%d %H:00:00', created_date) as period,
                            COUNT(*) as created,
                            SUM(CASE WHEN status IN ('DISPOSED', 'RELEASED', 'COMPLETED') THEN 1 ELSE 0 END) as completed
                        FROM vehicles 
                        WHERE created_date >= ?
                        GROUP BY strftime('%Y-%m-%d %H:00:00', created_date)
                        ORDER BY period
                    ''', (start_date.isoformat(),))
                
                for row in cursor.fetchall():
                    period, created, completed = row
                    trend_data.append({
                        'timestamp': period,
                        'created': created,
                        'completed': completed,
                        'efficiency': (completed / created * 100) if created > 0 else 0
                    })
            
            elif metric == 'revenue':
                # Revenue trend
                if interval == 'day':
                    cursor.execute('''
                        SELECT 
                            DATE(updated_date) as period,
                            SUM(COALESCE(disposition_value, 0)) as revenue
                        FROM vehicles 
                        WHERE status IN ('DISPOSED', 'RELEASED')
                        AND updated_date >= ?
                        GROUP BY DATE(updated_date)
                        ORDER BY period
                    ''', (start_date.isoformat(),))
                
                for row in cursor.fetchall():
                    period, revenue = row
                    trend_data.append({
                        'timestamp': period,
                        'revenue': float(revenue) if revenue else 0.0
                    })
            
            elif metric == 'efficiency':
                # Processing efficiency trend
                if interval == 'day':
                    cursor.execute('''
                        SELECT 
                            DATE(created_date) as period,
                            AVG(julianday(updated_date) - julianday(created_date)) as avg_processing_time,
                            COUNT(*) as volume
                        FROM vehicles 
                        WHERE status IN ('DISPOSED', 'RELEASED', 'COMPLETED')
                        AND created_date >= ?
                        GROUP BY DATE(created_date)
                        ORDER BY period
                    ''', (start_date.isoformat(),))
                
                for row in cursor.fetchall():
                    period, avg_time, volume = row
                    trend_data.append({
                        'timestamp': period,
                        'avg_processing_time': float(avg_time) if avg_time else 0.0,
                        'volume': volume,
                        'efficiency_score': max(0, 100 - (float(avg_time) * 10)) if avg_time else 0
                    })
            
            db.close()
            
            self.logger.debug(f"Trend analysis completed for {metric}: {len(trend_data)} data points")
            return trend_data
            
        except Exception as e:
            self.logger.error(f"Error generating trend analysis for {metric}: {e}")
            return []
    
    def generate_analytics_summary(self, timeframe: str = '30d') -> Dict[str, Any]:
        """
        Generate comprehensive analytics summary for executive reporting
        
        Args:
            timeframe: Time period for analysis
        
        Returns:
            Dictionary with complete analytics summary
        """
        try:
            # Gather all metrics
            vehicle_metrics = self.get_vehicle_metrics(timeframe)
            operational_metrics = self.get_operational_metrics(timeframe)
            financial_metrics = self.get_financial_metrics(timeframe)
            real_time_kpis = self.get_real_time_kpis()
            
            summary = {
                'timeframe': timeframe,
                'generated_at': datetime.now().isoformat(),
                'vehicle_metrics': {
                    'total_vehicles': vehicle_metrics.total_vehicles,
                    'active_vehicles': vehicle_metrics.active_vehicles,
                    'completed_vehicles': vehicle_metrics.completed_vehicles,
                    'urgent_vehicles': vehicle_metrics.urgent_vehicles,
                    'average_processing_time': round(vehicle_metrics.average_processing_time, 2),
                    'processing_efficiency': round(vehicle_metrics.processing_efficiency, 1)
                },
                'operational_metrics': {
                    'workflow_completion_rate': round(operational_metrics.workflow_completion_rate, 1),
                    'automation_success_rate': round(operational_metrics.automation_success_rate, 1),
                    'bottleneck_stages': operational_metrics.bottleneck_stages or [],
                    'resource_utilization': round(operational_metrics.resource_utilization, 1)
                },
                'financial_metrics': {
                    'total_revenue': round(financial_metrics.total_revenue, 2),
                    'total_costs': round(financial_metrics.total_costs, 2),
                    'profit_margin': round(financial_metrics.profit_margin, 1),
                    'average_vehicle_value': round(financial_metrics.average_vehicle_value, 2),
                    'cost_per_vehicle': round(financial_metrics.cost_per_vehicle, 2)
                },
                'real_time_kpis': real_time_kpis,
                'performance_indicators': {
                    'system_health': 'Operational' if real_time_kpis['active_vehicles'] > 0 else 'Idle',
                    'automation_status': 'Active' if real_time_kpis['automated_actions_hour'] > 0 else 'Standby',
                    'efficiency_rating': self._calculate_efficiency_rating(vehicle_metrics, operational_metrics),
                    'financial_health': self._calculate_financial_health(financial_metrics)
                }
            }
            
            self.logger.info(f"Analytics summary generated for {timeframe}")
            return summary
            
        except Exception as e:
            self.logger.error(f"Error generating analytics summary: {e}")
            return {
                'timeframe': timeframe,
                'generated_at': datetime.now().isoformat(),
                'error': str(e)
            }
    
    def _calculate_efficiency_rating(self, vehicle_metrics: VehicleMetrics, 
                                   operational_metrics: OperationalMetrics) -> str:
        """Calculate overall efficiency rating"""
        try:
            score = (
                vehicle_metrics.processing_efficiency * 0.4 +
                operational_metrics.workflow_completion_rate * 0.3 +
                operational_metrics.automation_success_rate * 0.3
            )
            
            if score >= 90:
                return 'Excellent'
            elif score >= 75:
                return 'Good'
            elif score >= 60:
                return 'Fair'
            else:
                return 'Needs Improvement'
        except:
            return 'Unknown'
    
    def _calculate_financial_health(self, financial_metrics: FinancialMetrics) -> str:
        """Calculate financial health rating"""
        try:
            if financial_metrics.profit_margin >= 20:
                return 'Strong'
            elif financial_metrics.profit_margin >= 10:
                return 'Healthy'
            elif financial_metrics.profit_margin >= 0:
                return 'Stable'
            else:
                return 'Concerning'
        except:
            return 'Unknown'
