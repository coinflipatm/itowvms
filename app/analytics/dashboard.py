"""
Dashboard Manager for iTow VMS Analytics
Provides web interface for real-time analytics and business intelligence
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from flask import render_template, jsonify, request, current_app
import json

class DashboardManager:
    """Manages analytics dashboard functionality and data presentation"""
    
    def __init__(self, app=None):
        self.app = app
        self.logger = logging.getLogger(__name__)
        
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize dashboard manager with Flask application"""
        self.app = app
        app.dashboard_manager = self
        
        # Dashboard configuration
        self.refresh_interval = app.config.get('DASHBOARD_REFRESH_INTERVAL', 30)  # seconds
        self.chart_colors = app.config.get('DASHBOARD_CHART_COLORS', {
            'primary': '#2563eb',
            'success': '#16a34a', 
            'warning': '#d97706',
            'danger': '#dc2626',
            'info': '#0891b2'
        })
        
        self.logger.info("Dashboard Manager initialized")
    
    def get_executive_dashboard_data(self, timeframe: str = '30d') -> Dict[str, Any]:
        """
        Get comprehensive dashboard data for executive view
        
        Args:
            timeframe: Time period for analysis
        
        Returns:
            Dictionary with all dashboard data
        """
        try:
            analytics_engine = getattr(self.app, 'analytics_engine', None)
            if not analytics_engine:
                self.logger.error("Analytics engine not available")
                return self._get_empty_dashboard_data()
            
            # Get comprehensive analytics summary
            summary = analytics_engine.generate_analytics_summary(timeframe)
            
            # Get trend data for charts
            vehicle_trend = analytics_engine.get_trend_analysis('vehicles', timeframe)
            revenue_trend = analytics_engine.get_trend_analysis('revenue', timeframe)
            efficiency_trend = analytics_engine.get_trend_analysis('efficiency', timeframe)
            
            # Get real-time KPIs
            kpis = analytics_engine.get_real_time_kpis()
            
            dashboard_data = {
                'summary': summary,
                'kpis': kpis,
                'charts': {
                    'vehicle_processing': self._format_vehicle_chart_data(vehicle_trend),
                    'revenue_trend': self._format_revenue_chart_data(revenue_trend),
                    'efficiency_metrics': self._format_efficiency_chart_data(efficiency_trend),
                    'status_distribution': self._get_status_distribution_data(),
                    'urgency_breakdown': self._get_urgency_breakdown_data()
                },
                'alerts': self._generate_dashboard_alerts(summary, kpis),
                'configuration': {
                    'refresh_interval': self.refresh_interval,
                    'timeframe': timeframe,
                    'chart_colors': self.chart_colors,
                    'last_updated': datetime.now().isoformat()
                }
            }
            
            self.logger.info(f"Executive dashboard data prepared for {timeframe}")
            return dashboard_data
            
        except Exception as e:
            self.logger.error(f"Error preparing executive dashboard data: {e}")
            return self._get_empty_dashboard_data()
    
    def get_operational_dashboard_data(self, timeframe: str = '7d') -> Dict[str, Any]:
        """
        Get operational dashboard data for day-to-day management
        
        Args:
            timeframe: Time period for analysis
        
        Returns:
            Dictionary with operational dashboard data
        """
        try:
            analytics_engine = getattr(self.app, 'analytics_engine', None)
            if not analytics_engine:
                return self._get_empty_dashboard_data()
            
            # Get operational metrics
            operational_metrics = analytics_engine.get_operational_metrics(timeframe)
            vehicle_metrics = analytics_engine.get_vehicle_metrics(timeframe)
            kpis = analytics_engine.get_real_time_kpis()
            
            dashboard_data = {
                'operational_metrics': {
                    'workflow_completion_rate': operational_metrics.workflow_completion_rate,
                    'automation_success_rate': operational_metrics.automation_success_rate,
                    'bottleneck_stages': operational_metrics.bottleneck_stages,
                    'resource_utilization': operational_metrics.resource_utilization
                },
                'vehicle_metrics': {
                    'total_vehicles': vehicle_metrics.total_vehicles,
                    'active_vehicles': vehicle_metrics.active_vehicles,
                    'urgent_vehicles': vehicle_metrics.urgent_vehicles,
                    'processing_efficiency': vehicle_metrics.processing_efficiency
                },
                'real_time_status': kpis,
                'workflow_analysis': self._get_workflow_analysis_data(),
                'bottleneck_analysis': self._analyze_bottlenecks(operational_metrics),
                'automation_insights': self._get_automation_insights(),
                'configuration': {
                    'timeframe': timeframe,
                    'last_updated': datetime.now().isoformat()
                }
            }
            
            self.logger.info(f"Operational dashboard data prepared for {timeframe}")
            return dashboard_data
            
        except Exception as e:
            self.logger.error(f"Error preparing operational dashboard data: {e}")
            return self._get_empty_dashboard_data()
    
    def _format_vehicle_chart_data(self, trend_data: List[Dict]) -> Dict[str, Any]:
        """Format vehicle trend data for chart display"""
        try:
            labels = []
            created_data = []
            completed_data = []
            efficiency_data = []
            
            for point in trend_data:
                labels.append(point.get('timestamp', ''))
                created_data.append(point.get('created', 0))
                completed_data.append(point.get('completed', 0))
                efficiency_data.append(round(point.get('efficiency', 0), 1))
            
            return {
                'labels': labels,
                'datasets': [
                    {
                        'label': 'Vehicles Created',
                        'data': created_data,
                        'borderColor': self.chart_colors['primary'],
                        'backgroundColor': self.chart_colors['primary'] + '20',
                        'tension': 0.4
                    },
                    {
                        'label': 'Vehicles Completed',
                        'data': completed_data,
                        'borderColor': self.chart_colors['success'],
                        'backgroundColor': self.chart_colors['success'] + '20',
                        'tension': 0.4
                    }
                ],
                'efficiency_data': efficiency_data
            }
        except Exception as e:
            self.logger.error(f"Error formatting vehicle chart data: {e}")
            return {'labels': [], 'datasets': [], 'efficiency_data': []}
    
    def _format_revenue_chart_data(self, trend_data: List[Dict]) -> Dict[str, Any]:
        """Format revenue trend data for chart display"""
        try:
            labels = []
            revenue_data = []
            cumulative_revenue = 0
            cumulative_data = []
            
            for point in trend_data:
                labels.append(point.get('timestamp', ''))
                revenue = point.get('revenue', 0)
                revenue_data.append(revenue)
                cumulative_revenue += revenue
                cumulative_data.append(cumulative_revenue)
            
            return {
                'labels': labels,
                'datasets': [
                    {
                        'label': 'Daily Revenue',
                        'data': revenue_data,
                        'type': 'bar',
                        'backgroundColor': self.chart_colors['success'] + '80',
                        'borderColor': self.chart_colors['success']
                    },
                    {
                        'label': 'Cumulative Revenue',
                        'data': cumulative_data,
                        'type': 'line',
                        'borderColor': self.chart_colors['primary'],
                        'backgroundColor': 'transparent',
                        'tension': 0.4,
                        'yAxisID': 'y1'
                    }
                ]
            }
        except Exception as e:
            self.logger.error(f"Error formatting revenue chart data: {e}")
            return {'labels': [], 'datasets': []}
    
    def _format_efficiency_chart_data(self, trend_data: List[Dict]) -> Dict[str, Any]:
        """Format efficiency trend data for chart display"""
        try:
            labels = []
            processing_time_data = []
            volume_data = []
            efficiency_score_data = []
            
            for point in trend_data:
                labels.append(point.get('timestamp', ''))
                processing_time_data.append(round(point.get('avg_processing_time', 0), 2))
                volume_data.append(point.get('volume', 0))
                efficiency_score_data.append(round(point.get('efficiency_score', 0), 1))
            
            return {
                'labels': labels,
                'datasets': [
                    {
                        'label': 'Processing Time (days)',
                        'data': processing_time_data,
                        'borderColor': self.chart_colors['warning'],
                        'backgroundColor': self.chart_colors['warning'] + '20',
                        'tension': 0.4,
                        'yAxisID': 'y'
                    },
                    {
                        'label': 'Volume',
                        'data': volume_data,
                        'type': 'bar',
                        'backgroundColor': self.chart_colors['info'] + '40',
                        'yAxisID': 'y1'
                    }
                ],
                'efficiency_scores': efficiency_score_data
            }
        except Exception as e:
            self.logger.error(f"Error formatting efficiency chart data: {e}")
            return {'labels': [], 'datasets': [], 'efficiency_scores': []}
    
    def _get_status_distribution_data(self) -> Dict[str, Any]:
        """Get vehicle status distribution for pie chart"""
        try:
            from app.core.database import get_db_connection
            
            db = get_db_connection()
            cursor = db.cursor()
            
            cursor.execute('''
                SELECT status, COUNT(*) as count
                FROM vehicles
                GROUP BY status
                ORDER BY count DESC
            ''')
            
            status_data = cursor.fetchall()
            db.close()
            
            labels = []
            data = []
            colors = []
            
            color_map = {
                'ACTIVE': self.chart_colors['primary'],
                'PENDING': self.chart_colors['warning'],
                'DISPOSED': self.chart_colors['success'],
                'RELEASED': self.chart_colors['info'],
                'COMPLETED': self.chart_colors['success']
            }
            
            for status, count in status_data:
                labels.append(status)
                data.append(count)
                colors.append(color_map.get(status, '#6b7280'))
            
            return {
                'labels': labels,
                'datasets': [{
                    'data': data,
                    'backgroundColor': colors,
                    'borderWidth': 2,
                    'borderColor': '#ffffff'
                }]
            }
            
        except Exception as e:
            self.logger.error(f"Error getting status distribution data: {e}")
            return {'labels': [], 'datasets': []}
    
    def _get_urgency_breakdown_data(self) -> Dict[str, Any]:
        """Get urgency level breakdown for chart"""
        try:
            from app.core.database import get_db_connection
            
            db = get_db_connection()
            cursor = db.cursor()
            
            cursor.execute('''
                SELECT 
                    CASE 
                        WHEN urgency_score >= 90 THEN 'Critical'
                        WHEN urgency_score >= 70 THEN 'High'
                        WHEN urgency_score >= 40 THEN 'Medium'
                        ELSE 'Low'
                    END as urgency_level,
                    COUNT(*) as count
                FROM vehicles
                WHERE status NOT IN ('DISPOSED', 'RELEASED', 'COMPLETED')
                GROUP BY urgency_level
                ORDER BY 
                    CASE urgency_level
                        WHEN 'Critical' THEN 1
                        WHEN 'High' THEN 2
                        WHEN 'Medium' THEN 3
                        WHEN 'Low' THEN 4
                    END
            ''')
            
            urgency_data = cursor.fetchall()
            db.close()
            
            labels = []
            data = []
            colors = [
                self.chart_colors['danger'],   # Critical
                self.chart_colors['warning'],  # High
                self.chart_colors['info'],     # Medium
                self.chart_colors['success']   # Low
            ]
            
            for urgency_level, count in urgency_data:
                labels.append(urgency_level)
                data.append(count)
            
            return {
                'labels': labels,
                'datasets': [{
                    'data': data,
                    'backgroundColor': colors[:len(data)],
                    'borderWidth': 2,
                    'borderColor': '#ffffff'
                }]
            }
            
        except Exception as e:
            self.logger.error(f"Error getting urgency breakdown data: {e}")
            return {'labels': [], 'datasets': []}
    
    def _get_workflow_analysis_data(self) -> Dict[str, Any]:
        """Get workflow stage analysis for operational dashboard"""
        try:
            from app.core.database import get_db_connection
            
            db = get_db_connection()
            cursor = db.cursor()
            
            # Get vehicles by workflow stage
            cursor.execute('''
                SELECT 
                    COALESCE(current_stage, 'Unknown') as stage,
                    COUNT(*) as count,
                    AVG(urgency_score) as avg_urgency
                FROM vehicles
                WHERE status NOT IN ('DISPOSED', 'RELEASED', 'COMPLETED')
                GROUP BY current_stage
                ORDER BY count DESC
            ''')
            
            stage_data = cursor.fetchall()
            
            # Get stage durations
            cursor.execute('''
                SELECT 
                    action,
                    AVG(julianday(created_date) - LAG(julianday(created_date)) OVER (
                        PARTITION BY vehicle_id ORDER BY created_date
                    )) as avg_duration_days
                FROM vehicle_logs 
                WHERE created_date >= date('now', '-30 days')
                AND action IN ('STATUS_CHANGE', 'DISPOSITION_SET', 'INSPECTION_COMPLETED')
                GROUP BY action
            ''')
            
            duration_data = cursor.fetchall()
            db.close()
            
            # Format stage analysis
            stages = []
            for stage, count, avg_urgency in stage_data:
                stages.append({
                    'stage': stage,
                    'vehicle_count': count,
                    'avg_urgency': round(float(avg_urgency) if avg_urgency else 0, 1),
                    'status': 'attention' if avg_urgency and avg_urgency > 70 else 'normal'
                })
            
            # Format duration analysis
            durations = {}
            for action, avg_duration in duration_data:
                if avg_duration:
                    durations[action] = round(float(avg_duration), 2)
            
            return {
                'stage_analysis': stages,
                'average_durations': durations,
                'total_active_stages': len(stages),
                'high_urgency_stages': len([s for s in stages if s['avg_urgency'] > 70])
            }
            
        except Exception as e:
            self.logger.error(f"Error getting workflow analysis data: {e}")
            return {
                'stage_analysis': [],
                'average_durations': {},
                'total_active_stages': 0,
                'high_urgency_stages': 0
            }
    
    def _analyze_bottlenecks(self, operational_metrics) -> Dict[str, Any]:
        """Analyze workflow bottlenecks"""
        try:
            bottlenecks = operational_metrics.bottleneck_stages or []
            stage_durations = operational_metrics.average_stage_duration or {}
            
            analysis = {
                'identified_bottlenecks': len(bottlenecks),
                'bottleneck_stages': bottlenecks,
                'recommendations': [],
                'severity': 'low'
            }
            
            if len(bottlenecks) > 2:
                analysis['severity'] = 'high'
                analysis['recommendations'].append('Multiple bottlenecks detected - prioritize workflow optimization')
            elif len(bottlenecks) > 0:
                analysis['severity'] = 'medium'
                analysis['recommendations'].append('Monitor identified bottleneck stages')
            
            # Add specific recommendations based on bottleneck types
            for bottleneck in bottlenecks:
                if 'INSPECTION' in bottleneck:
                    analysis['recommendations'].append('Consider additional inspection resources')
                elif 'DISPOSITION' in bottleneck:
                    analysis['recommendations'].append('Review disposition approval process')
                elif 'STATUS' in bottleneck:
                    analysis['recommendations'].append('Automate status change workflows')
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"Error analyzing bottlenecks: {e}")
            return {
                'identified_bottlenecks': 0,
                'bottleneck_stages': [],
                'recommendations': [],
                'severity': 'unknown'
            }
    
    def _get_automation_insights(self) -> Dict[str, Any]:
        """Get automation performance insights"""
        try:
            from app.core.database import get_db_connection
            
            db = get_db_connection()
            cursor = db.cursor()
            
            # Get automation statistics from last 24 hours
            cursor.execute('''
                SELECT 
                    COUNT(*) as total_actions,
                    SUM(CASE WHEN notes LIKE '%automated%' OR notes LIKE '%system%' THEN 1 ELSE 0 END) as automated_actions,
                    COUNT(DISTINCT vehicle_id) as vehicles_affected
                FROM vehicle_logs 
                WHERE created_date >= datetime('now', '-24 hours')
            ''')
            
            result = cursor.fetchone()
            total_actions, automated_actions, vehicles_affected = result if result else (0, 0, 0)
            
            # Get automation success rate
            automation_rate = (automated_actions / total_actions * 100) if total_actions > 0 else 0
            
            # Get recent automation failures (if any tracking exists)
            cursor.execute('''
                SELECT COUNT(*) FROM vehicle_logs 
                WHERE created_date >= datetime('now', '-24 hours')
                AND notes LIKE '%error%' OR notes LIKE '%failed%'
            ''')
            
            failures = cursor.fetchone()[0]
            db.close()
            
            insights = {
                'automation_rate': round(automation_rate, 1),
                'total_actions_24h': total_actions,
                'automated_actions_24h': automated_actions,
                'vehicles_affected_24h': vehicles_affected,
                'failure_count_24h': failures,
                'success_rate': round((automated_actions - failures) / max(1, automated_actions) * 100, 1),
                'status': 'optimal' if automation_rate > 50 else 'suboptimal',
                'recommendations': []
            }
            
            # Generate recommendations
            if automation_rate < 30:
                insights['recommendations'].append('Consider expanding automation coverage')
            if failures > automated_actions * 0.1:
                insights['recommendations'].append('Review automation error handling')
            if vehicles_affected < total_actions * 0.5:
                insights['recommendations'].append('Optimize automation targeting')
            
            return insights
            
        except Exception as e:
            self.logger.error(f"Error getting automation insights: {e}")
            return {
                'automation_rate': 0,
                'total_actions_24h': 0,
                'automated_actions_24h': 0,
                'vehicles_affected_24h': 0,
                'failure_count_24h': 0,
                'success_rate': 0,
                'status': 'unknown',
                'recommendations': []
            }
    
    def _generate_dashboard_alerts(self, summary: Dict, kpis: Dict) -> List[Dict[str, Any]]:
        """Generate alerts for dashboard display"""
        alerts = []
        
        try:
            # High urgency vehicles alert
            urgent_count = kpis.get('urgent_vehicles', 0)
            if urgent_count > 10:
                alerts.append({
                    'type': 'danger',
                    'title': 'High Urgency Vehicles',
                    'message': f'{urgent_count} vehicles require immediate attention',
                    'action': 'Review urgent vehicle list',
                    'timestamp': datetime.now().isoformat()
                })
            elif urgent_count > 5:
                alerts.append({
                    'type': 'warning',
                    'title': 'Urgent Vehicles',
                    'message': f'{urgent_count} vehicles need attention',
                    'action': 'Monitor urgency levels',
                    'timestamp': datetime.now().isoformat()
                })
            
            # Low processing efficiency alert
            efficiency = summary.get('vehicle_metrics', {}).get('processing_efficiency', 0)
            if efficiency < 50:
                alerts.append({
                    'type': 'warning',
                    'title': 'Low Processing Efficiency',
                    'message': f'Processing efficiency at {efficiency:.1f}%',
                    'action': 'Review workflow bottlenecks',
                    'timestamp': datetime.now().isoformat()
                })
            
            # Revenue performance alert
            revenue_today = kpis.get('revenue_today', 0)
            if revenue_today == 0:
                alerts.append({
                    'type': 'info',
                    'title': 'No Revenue Today',
                    'message': 'No dispositions completed today',
                    'action': 'Check disposition pipeline',
                    'timestamp': datetime.now().isoformat()
                })
            
            # System performance alert
            automation_activity = kpis.get('automation_activity', 0)
            if automation_activity < 20:
                alerts.append({
                    'type': 'warning',
                    'title': 'Low Automation Activity',
                    'message': 'Automated systems may not be running optimally',
                    'action': 'Check system status',
                    'timestamp': datetime.now().isoformat()
                })
            
        except Exception as e:
            self.logger.error(f"Error generating dashboard alerts: {e}")
            alerts.append({
                'type': 'danger',
                'title': 'System Error',
                'message': 'Error generating dashboard alerts',
                'action': 'Check system logs',
                'timestamp': datetime.now().isoformat()
            })
        
        return alerts
    
    def _get_empty_dashboard_data(self) -> Dict[str, Any]:
        """Return empty dashboard data structure"""
        return {
            'summary': {
                'timeframe': '30d',
                'generated_at': datetime.now().isoformat(),
                'vehicle_metrics': {},
                'operational_metrics': {},
                'financial_metrics': {},
                'real_time_kpis': {},
                'performance_indicators': {}
            },
            'kpis': {},
            'charts': {
                'vehicle_processing': {'labels': [], 'datasets': []},
                'revenue_trend': {'labels': [], 'datasets': []},
                'efficiency_metrics': {'labels': [], 'datasets': []},
                'status_distribution': {'labels': [], 'datasets': []},
                'urgency_breakdown': {'labels': [], 'datasets': []}
            },
            'alerts': [],
            'configuration': {
                'refresh_interval': self.refresh_interval,
                'timeframe': '30d',
                'chart_colors': self.chart_colors,
                'last_updated': datetime.now().isoformat()
            }
        }
