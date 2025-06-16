"""
AI Integration Module for iTow Vehicle Management System

This module provides integration between AI engines and the core vehicle management system,
enabling seamless AI-powered features throughout the application.
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import asyncio
import json

# Import AI engines
from app.ai import PredictiveEngine, NLPEngine, DocumentAI, DecisionEngine

logger = logging.getLogger(__name__)

class AIIntegrationManager:
    """
    Central manager for AI integration with the core system.
    Handles initialization, coordination, and integration of AI engines.
    """
    
    def __init__(self, app=None):
        """Initialize AI Integration Manager"""
        self.app = app
        self.engines = {}
        self.is_initialized = False
        self.integration_callbacks = {}
        self.ai_cache = {}
        
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize AI integration with Flask app"""
        self.app = app
        
        # Configure AI settings
        app.config.setdefault('AI_ENABLED', True)
        app.config.setdefault('AI_CACHE_TTL', 300)  # 5 minutes
        app.config.setdefault('AI_ASYNC_PROCESSING', True)
        app.config.setdefault('AI_CONFIDENCE_THRESHOLD', 0.7)
        
        # Initialize AI engines
        try:
            self._initialize_engines()
            self.is_initialized = True
            logger.info("AI Integration Manager initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize AI Integration Manager: {e}")
            self.is_initialized = False
        
        # Store reference in app context
        app.ai_integration = self
    
    def _initialize_engines(self):
        """Initialize all AI engines"""
        try:
            # Initialize Predictive Engine
            self.engines['predictive'] = PredictiveEngine()
            self.app.predictive_engine = self.engines['predictive']
            
            # Initialize NLP Engine
            self.engines['nlp'] = NLPEngine()
            self.app.nlp_engine = self.engines['nlp']
            
            # Initialize Document AI
            self.engines['document'] = DocumentAI()
            self.app.document_ai = self.engines['document']
            
            # Initialize Decision Engine
            self.engines['decision'] = DecisionEngine()
            self.app.decision_engine = self.engines['decision']
            
            logger.info("All AI engines initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing AI engines: {e}")
            raise
    
    def get_engine(self, engine_type: str):
        """Get AI engine by type"""
        if not self.is_initialized:
            raise RuntimeError("AI Integration Manager not initialized")
        
        if engine_type not in self.engines:
            raise ValueError(f"Unknown AI engine type: {engine_type}")
        
        return self.engines[engine_type]
    
    def register_callback(self, event_type: str, callback):
        """Register callback for AI events"""
        if event_type not in self.integration_callbacks:
            self.integration_callbacks[event_type] = []
        self.integration_callbacks[event_type].append(callback)
    
    def trigger_callback(self, event_type: str, data: dict):
        """Trigger registered callbacks for an event"""
        if event_type in self.integration_callbacks:
            for callback in self.integration_callbacks[event_type]:
                try:
                    callback(data)
                except Exception as e:
                    logger.error(f"Error in callback for {event_type}: {e}")
    
    # ========================================================================
    # CORE SYSTEM INTEGRATION METHODS
    # ========================================================================
    
    def enhance_vehicle_data(self, vehicle_data: dict) -> dict:
        """Enhance vehicle data with AI predictions and insights"""
        if not self.is_initialized:
            return vehicle_data
        
        enhanced_data = vehicle_data.copy()
        
        try:
            # Add disposition prediction
            predictive_engine = self.get_engine('predictive')
            disposition_pred = predictive_engine.predict_disposition(vehicle_data)
            enhanced_data['ai_disposition_prediction'] = disposition_pred
            
            # Add timeline prediction
            timeline_pred = predictive_engine.predict_timeline(vehicle_data)
            enhanced_data['ai_timeline_prediction'] = timeline_pred
            
            # Add decision engine recommendations
            decision_engine = self.get_engine('decision')
            recommendations = decision_engine.make_disposition_decision(vehicle_data)
            enhanced_data['ai_recommendations'] = recommendations
            
            # Cache results
            cache_key = f"vehicle_ai_{vehicle_data.get('towbook_call_number')}"
            self.ai_cache[cache_key] = {
                'data': enhanced_data,
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error enhancing vehicle data: {e}")
        
        return enhanced_data
    
    def process_batch_vehicles(self, vehicles: List[dict]) -> List[dict]:
        """Process multiple vehicles with AI enhancement"""
        if not self.is_initialized:
            return vehicles
        
        enhanced_vehicles = []
        
        try:
            # Batch processing for efficiency
            predictive_engine = self.get_engine('predictive')
            
            # Detect anomalies across the batch
            anomalies = predictive_engine.detect_anomalies(vehicles)
            
            # Optimize revenue across the batch
            revenue_optimization = predictive_engine.optimize_revenue(vehicles)
            
            # Enhance each vehicle individually
            for vehicle in vehicles:
                enhanced_vehicle = self.enhance_vehicle_data(vehicle)
                
                # Add batch analysis results
                vehicle_id = vehicle.get('towbook_call_number')
                if vehicle_id in anomalies:
                    enhanced_vehicle['ai_anomaly_detection'] = anomalies[vehicle_id]
                
                if vehicle_id in revenue_optimization.get('vehicle_recommendations', {}):
                    enhanced_vehicle['ai_revenue_optimization'] = revenue_optimization['vehicle_recommendations'][vehicle_id]
                
                enhanced_vehicles.append(enhanced_vehicle)
            
            # Trigger batch processing callback
            self.trigger_callback('batch_processed', {
                'count': len(vehicles),
                'anomalies_found': len(anomalies),
                'revenue_optimization': revenue_optimization
            })
            
        except Exception as e:
            logger.error(f"Error in batch processing: {e}")
            enhanced_vehicles = vehicles
        
        return enhanced_vehicles
    
    def process_search_query(self, query: str, vehicles: List[dict], user_context: dict = None) -> dict:
        """Process search query with NLP enhancement"""
        if not self.is_initialized:
            return {'vehicles': vehicles, 'query': query}
        
        try:
            nlp_engine = self.get_engine('nlp')
            
            # Process natural language query
            query_analysis = nlp_engine.process_query(query, context=user_context or {})
            
            # Perform semantic search
            search_results = nlp_engine.semantic_search(query, vehicles, limit=50)
            
            # Get suggestions for query refinement
            suggestions = nlp_engine.get_query_suggestions(query, limit=5)
            
            return {
                'original_query': query,
                'query_analysis': query_analysis,
                'search_results': search_results,
                'suggestions': suggestions,
                'total_matches': len(search_results)
            }
            
        except Exception as e:
            logger.error(f"Error processing search query: {e}")
            return {'vehicles': vehicles, 'query': query, 'error': str(e)}
    
    def process_document_upload(self, file_data, file_type: str = 'auto') -> dict:
        """Process uploaded document with AI extraction"""
        if not self.is_initialized:
            return {'error': 'AI not available'}
        
        try:
            document_ai = self.get_engine('document')
            
            # Process document
            processing_result = document_ai.process_document(file_data)
            
            # Extract vehicle data
            extracted_data = document_ai.extract_vehicle_data(processing_result.get('extracted_text', ''))
            
            # Validate extracted data
            validation_result = document_ai.validate_document(extracted_data)
            
            # Generate auto-fill data
            autofill_data = document_ai.generate_autofill_data(extracted_data)
            
            return {
                'processing_result': processing_result,
                'extracted_data': extracted_data,
                'validation': validation_result,
                'autofill_data': autofill_data,
                'confidence': processing_result.get('confidence', 0.0)
            }
            
        except Exception as e:
            logger.error(f"Error processing document: {e}")
            return {'error': str(e)}
    
    def make_workflow_decision(self, vehicle_data: dict, current_stage: str = None) -> dict:
        """Make AI-powered workflow decision"""
        if not self.is_initialized:
            return {'decision': 'manual_review', 'confidence': 0.0}
        
        try:
            decision_engine = self.get_engine('decision')
            
            # Make disposition decision
            disposition_decision = decision_engine.make_disposition_decision(vehicle_data)
            
            # Make workflow routing decision
            workflow_decision = decision_engine.route_workflow(vehicle_data, current_stage)
            
            # Assess escalation needs
            escalation_assessment = decision_engine.assess_escalation({
                'vehicle': vehicle_data,
                'current_stage': current_stage,
                'disposition_confidence': disposition_decision.get('confidence', 0.0)
            })
            
            return {
                'disposition': disposition_decision,
                'workflow': workflow_decision,
                'escalation': escalation_assessment,
                'overall_confidence': (
                    disposition_decision.get('confidence', 0.0) + 
                    workflow_decision.get('confidence', 0.0)
                ) / 2
            }
            
        except Exception as e:
            logger.error(f"Error making workflow decision: {e}")
            return {'error': str(e), 'decision': 'manual_review', 'confidence': 0.0}
    
    def optimize_operations(self, pending_tasks: List[dict], available_resources: dict = None) -> dict:
        """Optimize operations with AI resource allocation"""
        if not self.is_initialized:
            return {'optimization': 'not_available'}
        
        try:
            decision_engine = self.get_engine('decision')
            
            # Assign priorities to tasks
            priority_assignments = decision_engine.assign_priority(pending_tasks)
            
            # Optimize resource allocation
            resource_allocation = decision_engine.optimize_resource_allocation(
                pending_tasks, 
                available_resources or {}
            )
            
            return {
                'priority_assignments': priority_assignments,
                'resource_allocation': resource_allocation,
                'optimization_score': resource_allocation.get('efficiency_score', 0.0)
            }
            
        except Exception as e:
            logger.error(f"Error optimizing operations: {e}")
            return {'error': str(e)}
    
    # ========================================================================
    # REAL-TIME AI FEATURES
    # ========================================================================
    
    def get_real_time_insights(self, vehicle_id: str) -> dict:
        """Get real-time AI insights for a vehicle"""
        if not self.is_initialized:
            return {}
        
        try:
            # Check cache first
            cache_key = f"insights_{vehicle_id}"
            if cache_key in self.ai_cache:
                cached = self.ai_cache[cache_key]
                cache_age = (datetime.utcnow() - datetime.fromisoformat(cached['timestamp'])).seconds
                if cache_age < self.app.config['AI_CACHE_TTL']:
                    return cached['data']
            
            # Get vehicle data (this would integrate with your database)
            # For now, we'll use a placeholder
            vehicle_data = self._get_vehicle_data(vehicle_id)
            
            if not vehicle_data:
                return {}
            
            # Generate insights
            insights = {
                'vehicle_id': vehicle_id,
                'timestamp': datetime.utcnow().isoformat(),
                'predictions': {},
                'recommendations': [],
                'alerts': []
            }
            
            # Add predictions
            predictive_engine = self.get_engine('predictive')
            disposition_pred = predictive_engine.predict_disposition(vehicle_data)
            timeline_pred = predictive_engine.predict_timeline(vehicle_data)
            
            insights['predictions'] = {
                'disposition': disposition_pred,
                'timeline': timeline_pred
            }
            
            # Add recommendations
            decision_engine = self.get_engine('decision')
            recommendations = decision_engine.make_disposition_decision(vehicle_data)
            insights['recommendations'] = recommendations
            
            # Check for alerts
            if disposition_pred.get('confidence', 0.0) < 0.5:
                insights['alerts'].append({
                    'type': 'low_confidence',
                    'message': 'Disposition prediction has low confidence',
                    'severity': 'warning'
                })
            
            # Cache results
            self.ai_cache[cache_key] = {
                'data': insights,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            return insights
            
        except Exception as e:
            logger.error(f"Error getting real-time insights: {e}")
            return {'error': str(e)}
    
    def get_ai_dashboard_metrics(self) -> dict:
        """Get AI metrics for dashboard display"""
        if not self.is_initialized:
            return {}
        
        try:
            metrics = {
                'timestamp': datetime.utcnow().isoformat(),
                'engines': {},
                'performance': {},
                'usage': {}
            }
            
            # Get engine status
            for engine_type, engine in self.engines.items():
                if hasattr(engine, 'get_metrics'):
                    metrics['engines'][engine_type] = engine.get_metrics()
                else:
                    metrics['engines'][engine_type] = {'status': 'available'}
            
            # Calculate cache performance
            cache_hits = sum(1 for entry in self.ai_cache.values() 
                           if (datetime.utcnow() - datetime.fromisoformat(entry['timestamp'])).seconds < 300)
            
            metrics['performance'] = {
                'cache_size': len(self.ai_cache),
                'cache_hits': cache_hits,
                'engines_active': len([e for e in metrics['engines'].values() 
                                     if e.get('status') == 'available'])
            }
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error getting dashboard metrics: {e}")
            return {'error': str(e)}
    
    # ========================================================================
    # UTILITY METHODS
    # ========================================================================
    
    def _get_vehicle_data(self, vehicle_id: str) -> dict:
        """Get vehicle data from database (placeholder for integration)"""
        # This would integrate with your actual database
        # For now, return empty dict
        return {}
    
    def clear_cache(self):
        """Clear AI cache"""
        self.ai_cache.clear()
        logger.info("AI cache cleared")
    
    def get_system_status(self) -> dict:
        """Get comprehensive AI system status"""
        return {
            'initialized': self.is_initialized,
            'engines_count': len(self.engines),
            'cache_size': len(self.ai_cache),
            'callbacks_registered': len(self.integration_callbacks),
            'engines': {
                engine_type: {
                    'available': engine is not None,
                    'type': type(engine).__name__ if engine else None
                }
                for engine_type, engine in self.engines.items()
            }
        }
    
    def health_check(self) -> dict:
        """Perform health check on AI system"""
        health_status = {
            'overall': 'healthy',
            'engines': {},
            'issues': []
        }
        
        if not self.is_initialized:
            health_status['overall'] = 'critical'
            health_status['issues'].append('AI Integration Manager not initialized')
            return health_status
        
        # Check each engine
        for engine_type, engine in self.engines.items():
            try:
                if hasattr(engine, 'health_check'):
                    engine_health = engine.health_check()
                else:
                    engine_health = {'status': 'available'}
                
                health_status['engines'][engine_type] = engine_health
                
                if engine_health.get('status') != 'available':
                    health_status['issues'].append(f"Engine {engine_type} is not available")
                    
            except Exception as e:
                health_status['engines'][engine_type] = {'status': 'error', 'error': str(e)}
                health_status['issues'].append(f"Engine {engine_type} error: {str(e)}")
        
        # Determine overall health
        if health_status['issues']:
            health_status['overall'] = 'degraded' if len(health_status['issues']) < 3 else 'critical'
        
        return health_status

# Global instance for easy access
ai_integration = AIIntegrationManager()

def init_ai_integration(app):
    """Initialize AI integration with Flask app"""
    return ai_integration.init_app(app)
