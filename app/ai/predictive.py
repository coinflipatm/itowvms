"""
Predictive Analytics Engine for iTow VMS

This module implements machine learning models for:
- Vehicle disposition prediction (auction/scrap/release)
- Timeline prediction for workflow stages
- Revenue optimization and forecasting
- Risk assessment and anomaly detection
"""

import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, mean_squared_error
import joblib
import os

logger = logging.getLogger(__name__)

@dataclass
class PredictionResult:
    """Result of a prediction with confidence score and explanation"""
    prediction: Any
    confidence: float
    explanation: str
    model_used: str
    features_used: List[str]
    timestamp: datetime

@dataclass
class DispositionPrediction:
    """Vehicle disposition prediction result"""
    recommended_disposition: str  # 'auction', 'scrap', 'release'
    confidence: float
    expected_value: float
    time_to_disposition: int  # days
    risk_factors: List[str]
    
@dataclass
class TimelinePrediction:
    """Workflow timeline prediction result"""
    stage: str
    predicted_completion: datetime
    confidence: float
    delay_risk: float
    bottleneck_probability: float
    recommended_actions: List[str]

class PredictiveEngine:
    """Advanced predictive analytics engine using machine learning"""
    
    def __init__(self, app=None):
        self.app = app
        self.models = {}
        self.scalers = {}
        self.encoders = {}
        self.model_path = 'models'
        self.is_trained = False
        
        # Ensure models directory exists
        os.makedirs(self.model_path, exist_ok=True)
        
        # Initialize feature engineering
        self._setup_feature_engineering()
        
        logger.info("PredictiveEngine initialized")
    
    def _setup_feature_engineering(self):
        """Setup feature engineering pipelines"""
        self.feature_columns = {
            'disposition': [
                'vehicle_age', 'mileage', 'condition_score', 'market_value',
                'storage_days', 'tow_reason_encoded', 'make_encoded', 
                'model_encoded', 'location_encoded', 'season'
            ],
            'timeline': [
                'current_stage_duration', 'total_stages', 'complexity_score',
                'workload_factor', 'staff_availability', 'vehicle_priority',
                'documentation_complete', 'external_dependencies'
            ],
            'revenue': [
                'vehicle_age', 'mileage', 'condition_score', 'market_value',
                'disposition_type', 'storage_cost', 'processing_cost', 
                'market_trend', 'seasonal_factor'
            ]
        }
    
    def train_models(self, force_retrain: bool = False) -> Dict[str, float]:
        """Train all ML models with current data"""
        try:
            if self.is_trained and not force_retrain:
                logger.info("Models already trained. Use force_retrain=True to retrain.")
                return self._load_model_metrics()
            
            logger.info("Starting model training...")
            
            # Get training data
            training_data = self._prepare_training_data()
            
            if not training_data or len(training_data) < 50:
                logger.warning("Insufficient training data. Using synthetic data.")
                training_data = self._generate_synthetic_training_data()
            
            metrics = {}
            
            # Train disposition prediction model
            metrics['disposition'] = self._train_disposition_model(training_data)
            
            # Train timeline prediction model
            metrics['timeline'] = self._train_timeline_model(training_data)
            
            # Train revenue optimization model
            metrics['revenue'] = self._train_revenue_model(training_data)
            
            # Save models and metrics
            self._save_models()
            self._save_model_metrics(metrics)
            
            self.is_trained = True
            logger.info("Model training completed successfully")
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error training models: {str(e)}")
            return {}
    
    def predict_disposition(self, vehicle_data: Dict[str, Any]) -> DispositionPrediction:
        """Predict optimal disposition for a vehicle"""
        try:
            if not self.is_trained:
                self.train_models()
            
            # Prepare features
            features = self._prepare_disposition_features(vehicle_data)
            
            # Get model predictions
            model = self.models.get('disposition')
            if not model:
                raise ValueError("Disposition model not available")
            
            # Scale features
            scaler = self.scalers.get('disposition')
            if scaler:
                features_scaled = scaler.transform([features])
            else:
                features_scaled = [features]
            
            # Predict disposition
            disposition_prob = model.predict_proba(features_scaled)[0]
            disposition_classes = model.classes_
            
            # Get best prediction
            best_idx = np.argmax(disposition_prob)
            predicted_disposition = disposition_classes[best_idx]
            confidence = disposition_prob[best_idx]
            
            # Calculate expected value and timeline
            expected_value = self._calculate_expected_value(vehicle_data, predicted_disposition)
            time_to_disposition = self._estimate_disposition_timeline(vehicle_data, predicted_disposition)
            
            # Identify risk factors
            risk_factors = self._identify_risk_factors(vehicle_data, features)
            
            return DispositionPrediction(
                recommended_disposition=predicted_disposition,
                confidence=float(confidence),
                expected_value=expected_value,
                time_to_disposition=time_to_disposition,
                risk_factors=risk_factors
            )
            
        except Exception as e:
            logger.error(f"Error predicting disposition: {str(e)}")
            # Return default prediction
            return DispositionPrediction(
                recommended_disposition='auction',
                confidence=0.5,
                expected_value=0.0,
                time_to_disposition=30,
                risk_factors=['prediction_error']
            )
    
    def predict_timeline(self, vehicle_data: Dict[str, Any], stage: str) -> TimelinePrediction:
        """Predict timeline for workflow stage completion"""
        try:
            if not self.is_trained:
                self.train_models()
            
            # Prepare features
            features = self._prepare_timeline_features(vehicle_data, stage)
            
            # Get model predictions
            model = self.models.get('timeline')
            if not model:
                raise ValueError("Timeline model not available")
            
            # Scale features
            scaler = self.scalers.get('timeline')
            if scaler:
                features_scaled = scaler.transform([features])
            else:
                features_scaled = [features]
            
            # Predict timeline
            predicted_days = model.predict(features_scaled)[0]
            predicted_completion = datetime.now() + timedelta(days=int(predicted_days))
            
            # Calculate confidence and risk
            confidence = self._calculate_timeline_confidence(features, predicted_days)
            delay_risk = self._calculate_delay_risk(vehicle_data, stage)
            bottleneck_probability = self._calculate_bottleneck_probability(stage)
            
            # Generate recommendations
            recommended_actions = self._generate_timeline_recommendations(
                vehicle_data, stage, delay_risk
            )
            
            return TimelinePrediction(
                stage=stage,
                predicted_completion=predicted_completion,
                confidence=confidence,
                delay_risk=delay_risk,
                bottleneck_probability=bottleneck_probability,
                recommended_actions=recommended_actions
            )
            
        except Exception as e:
            logger.error(f"Error predicting timeline: {str(e)}")
            # Return default prediction
            return TimelinePrediction(
                stage=stage,
                predicted_completion=datetime.now() + timedelta(days=7),
                confidence=0.5,
                delay_risk=0.3,
                bottleneck_probability=0.2,
                recommended_actions=['monitor_progress']
            )
    
    def optimize_revenue(self, vehicle_data: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize revenue for vehicle disposition"""
        try:
            if not self.is_trained:
                self.train_models()
            
            # Analyze different disposition scenarios
            scenarios = ['auction', 'scrap', 'release']
            results = {}
            
            for scenario in scenarios:
                scenario_data = vehicle_data.copy()
                scenario_data['disposition_type'] = scenario
                
                features = self._prepare_revenue_features(scenario_data)
                
                # Get revenue model
                model = self.models.get('revenue')
                if not model:
                    continue
                
                # Scale features
                scaler = self.scalers.get('revenue')
                if scaler:
                    features_scaled = scaler.transform([features])
                else:
                    features_scaled = [features]
                
                # Predict revenue
                predicted_revenue = model.predict(features_scaled)[0]
                
                # Calculate costs
                storage_cost = self._calculate_storage_cost(vehicle_data, scenario)
                processing_cost = self._calculate_processing_cost(vehicle_data, scenario)
                
                net_revenue = predicted_revenue - storage_cost - processing_cost
                
                results[scenario] = {
                    'predicted_revenue': float(predicted_revenue),
                    'storage_cost': storage_cost,
                    'processing_cost': processing_cost,
                    'net_revenue': net_revenue,
                    'roi': net_revenue / max(processing_cost, 1) * 100
                }
            
            # Find optimal scenario
            optimal_scenario = max(results.keys(), 
                                 key=lambda x: results[x]['net_revenue'])
            
            return {
                'scenarios': results,
                'optimal_scenario': optimal_scenario,
                'optimization_factors': self._get_optimization_factors(vehicle_data),
                'confidence': self._calculate_revenue_confidence(results)
            }
            
        except Exception as e:
            logger.error(f"Error optimizing revenue: {str(e)}")
            return {
                'scenarios': {},
                'optimal_scenario': 'auction',
                'optimization_factors': ['error_occurred'],
                'confidence': 0.5
            }
    
    def detect_anomalies(self, vehicle_data: Dict[str, Any]) -> Dict[str, Any]:
        """Detect anomalies in vehicle data or processing"""
        anomalies = []
        risk_score = 0.0
        
        try:
            # Check for data anomalies
            if vehicle_data.get('tow_date'):
                tow_date = pd.to_datetime(vehicle_data['tow_date'])
                days_since_tow = (datetime.now() - tow_date).days
                
                if days_since_tow > 90:
                    anomalies.append('extended_storage_period')
                    risk_score += 0.3
            
            # Check for processing anomalies
            if vehicle_data.get('current_stage_duration', 0) > 14:
                anomalies.append('stage_processing_delay')
                risk_score += 0.2
            
            # Check for value anomalies
            market_value = vehicle_data.get('market_value', 0)
            storage_cost = vehicle_data.get('storage_cost', 0)
            
            if storage_cost > market_value * 0.5:
                anomalies.append('high_storage_cost_ratio')
                risk_score += 0.4
            
            # Check for workflow anomalies
            if vehicle_data.get('stage_reversals', 0) > 2:
                anomalies.append('multiple_stage_reversals')
                risk_score += 0.3
            
            return {
                'anomalies': anomalies,
                'risk_score': min(risk_score, 1.0),
                'recommendations': self._get_anomaly_recommendations(anomalies),
                'severity': self._calculate_anomaly_severity(risk_score)
            }
            
        except Exception as e:
            logger.error(f"Error detecting anomalies: {str(e)}")
            return {
                'anomalies': ['detection_error'],
                'risk_score': 0.5,
                'recommendations': ['review_manually'],
                'severity': 'medium'
            }
    
    def get_model_performance(self) -> Dict[str, Any]:
        """Get performance metrics for all trained models"""
        try:
            metrics = self._load_model_metrics()
            
            # Add model status information
            model_status = {}
            for model_name in ['disposition', 'timeline', 'revenue']:
                model_status[model_name] = {
                    'trained': model_name in self.models,
                    'last_trained': self._get_model_last_trained(model_name),
                    'accuracy': metrics.get(model_name, 0.0),
                    'needs_retraining': self._needs_retraining(model_name)
                }
            
            return {
                'model_metrics': metrics,
                'model_status': model_status,
                'training_data_size': self._get_training_data_size(),
                'feature_importance': self._get_feature_importance()
            }
            
        except Exception as e:
            logger.error(f"Error getting model performance: {str(e)}")
            return {}
    
    # Private helper methods
    
    def _prepare_training_data(self) -> List[Dict[str, Any]]:
        """Prepare training data from database"""
        try:
            if not self.app:
                return []
            
            from app.core.database import DatabaseManager
            db = DatabaseManager()
            
            # Get vehicle data with outcomes
            query = """
            SELECT v.*, vl.action, vl.notes, vl.timestamp
            FROM vehicles v
            LEFT JOIN vehicle_logs vl ON v.id = vl.vehicle_id
            WHERE v.status IN ('completed', 'disposed')
            ORDER BY v.tow_date DESC
            """
            
            results = db.execute_query(query)
            training_data = []
            
            for row in results:
                training_data.append(dict(row))
            
            return training_data
            
        except Exception as e:
            logger.error(f"Error preparing training data: {str(e)}")
            return []
    
    def _generate_synthetic_training_data(self) -> List[Dict[str, Any]]:
        """Generate synthetic training data for model training"""
        synthetic_data = []
        np.random.seed(42)
        
        dispositions = ['auction', 'scrap', 'release']
        makes = ['Toyota', 'Honda', 'Ford', 'Chevrolet', 'BMW']
        tow_reasons = ['abandoned', 'accident', 'illegal_parking', 'breakdown']
        
        for i in range(200):
            vehicle_age = np.random.randint(1, 20)
            mileage = np.random.randint(10000, 250000)
            condition_score = np.random.random()
            
            # Market value based on age and condition
            base_value = max(1000, 25000 - (vehicle_age * 1000) - (mileage * 0.05))
            market_value = base_value * (0.5 + condition_score * 0.5)
            
            storage_days = np.random.randint(1, 120)
            disposition = np.random.choice(dispositions)
            
            synthetic_data.append({
                'id': f'synthetic_{i}',
                'vehicle_age': vehicle_age,
                'mileage': mileage,
                'condition_score': condition_score,
                'market_value': market_value,
                'storage_days': storage_days,
                'tow_reason': np.random.choice(tow_reasons),
                'make': np.random.choice(makes),
                'disposition': disposition,
                'processing_time': np.random.randint(5, 45),
                'revenue': market_value * (0.7 + np.random.random() * 0.3)
            })
        
        logger.info(f"Generated {len(synthetic_data)} synthetic training samples")
        return synthetic_data
    
    def _train_disposition_model(self, training_data: List[Dict[str, Any]]) -> float:
        """Train the vehicle disposition prediction model"""
        try:
            # Prepare features and labels
            X, y = self._prepare_disposition_training_data(training_data)
            
            if len(X) < 10:
                logger.warning("Insufficient data for disposition model training")
                return 0.0
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42, stratify=y
            )
            
            # Scale features
            scaler = StandardScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            X_test_scaled = scaler.transform(X_test)
            
            # Train model
            model = RandomForestClassifier(
                n_estimators=100,
                random_state=42,
                class_weight='balanced'
            )
            model.fit(X_train_scaled, y_train)
            
            # Evaluate
            y_pred = model.predict(X_test_scaled)
            accuracy = accuracy_score(y_test, y_pred)
            
            # Save model and scaler
            self.models['disposition'] = model
            self.scalers['disposition'] = scaler
            
            logger.info(f"Disposition model trained with accuracy: {accuracy:.3f}")
            return accuracy
            
        except Exception as e:
            logger.error(f"Error training disposition model: {str(e)}")
            return 0.0
    
    def _train_timeline_model(self, training_data: List[Dict[str, Any]]) -> float:
        """Train the timeline prediction model"""
        try:
            # Prepare features and labels
            X, y = self._prepare_timeline_training_data(training_data)
            
            if len(X) < 10:
                logger.warning("Insufficient data for timeline model training")
                return 0.0
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42
            )
            
            # Scale features
            scaler = StandardScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            X_test_scaled = scaler.transform(X_test)
            
            # Train model
            model = RandomForestRegressor(
                n_estimators=100,
                random_state=42
            )
            model.fit(X_train_scaled, y_train)
            
            # Evaluate
            y_pred = model.predict(X_test_scaled)
            mse = mean_squared_error(y_test, y_pred)
            rmse = np.sqrt(mse)
            
            # Save model and scaler
            self.models['timeline'] = model
            self.scalers['timeline'] = scaler
            
            logger.info(f"Timeline model trained with RMSE: {rmse:.3f}")
            return 1.0 - (rmse / np.mean(y_test))  # Normalized accuracy
            
        except Exception as e:
            logger.error(f"Error training timeline model: {str(e)}")
            return 0.0
    
    def _train_revenue_model(self, training_data: List[Dict[str, Any]]) -> float:
        """Train the revenue optimization model"""
        try:
            # Prepare features and labels
            X, y = self._prepare_revenue_training_data(training_data)
            
            if len(X) < 10:
                logger.warning("Insufficient data for revenue model training")
                return 0.0
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42
            )
            
            # Scale features
            scaler = StandardScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            X_test_scaled = scaler.transform(X_test)
            
            # Train model
            model = RandomForestRegressor(
                n_estimators=100,
                random_state=42
            )
            model.fit(X_train_scaled, y_train)
            
            # Evaluate
            y_pred = model.predict(X_test_scaled)
            mse = mean_squared_error(y_test, y_pred)
            rmse = np.sqrt(mse)
            
            # Save model and scaler
            self.models['revenue'] = model
            self.scalers['revenue'] = scaler
            
            logger.info(f"Revenue model trained with RMSE: {rmse:.3f}")
            return 1.0 - (rmse / np.mean(y_test))  # Normalized accuracy
            
        except Exception as e:
            logger.error(f"Error training revenue model: {str(e)}")
            return 0.0
    
    def _prepare_disposition_features(self, vehicle_data: Dict[str, Any]) -> List[float]:
        """Prepare features for disposition prediction"""
        features = []
        
        # Vehicle characteristics
        features.append(vehicle_data.get('vehicle_age', 10))
        features.append(vehicle_data.get('mileage', 100000))
        features.append(vehicle_data.get('condition_score', 0.5))
        features.append(vehicle_data.get('market_value', 5000))
        
        # Storage and processing
        tow_date = pd.to_datetime(vehicle_data.get('tow_date', datetime.now()))
        storage_days = (datetime.now() - tow_date).days
        features.append(min(storage_days, 365))
        
        # Encoded categorical features (simplified)
        features.append(hash(vehicle_data.get('tow_reason', 'unknown')) % 100)
        features.append(hash(vehicle_data.get('make', 'unknown')) % 100)
        features.append(hash(vehicle_data.get('model', 'unknown')) % 100)
        features.append(hash(vehicle_data.get('location', 'unknown')) % 100)
        
        # Seasonal factor
        features.append(datetime.now().month)
        
        return features
    
    def _prepare_timeline_features(self, vehicle_data: Dict[str, Any], stage: str) -> List[float]:
        """Prepare features for timeline prediction"""
        features = []
        
        # Current stage information
        features.append(vehicle_data.get('current_stage_duration', 0))
        features.append(vehicle_data.get('total_stages', 5))
        features.append(vehicle_data.get('complexity_score', 0.5))
        
        # System load factors
        features.append(0.7)  # workload_factor (placeholder)
        features.append(0.8)  # staff_availability (placeholder)
        features.append(vehicle_data.get('priority', 1))
        
        # Documentation and dependencies
        features.append(1.0 if vehicle_data.get('documentation_complete') else 0.0)
        features.append(vehicle_data.get('external_dependencies', 0))
        
        return features
    
    def _prepare_revenue_features(self, vehicle_data: Dict[str, Any]) -> List[float]:
        """Prepare features for revenue prediction"""
        features = []
        
        # Vehicle value factors
        features.append(vehicle_data.get('vehicle_age', 10))
        features.append(vehicle_data.get('mileage', 100000))
        features.append(vehicle_data.get('condition_score', 0.5))
        features.append(vehicle_data.get('market_value', 5000))
        
        # Disposition type
        disposition_encoding = {
            'auction': 1.0,
            'scrap': 0.0,
            'release': 0.5
        }
        features.append(disposition_encoding.get(
            vehicle_data.get('disposition_type', 'auction'), 1.0
        ))
        
        # Cost factors
        features.append(vehicle_data.get('storage_cost', 100))
        features.append(vehicle_data.get('processing_cost', 200))
        
        # Market factors
        features.append(0.5)  # market_trend (placeholder)
        features.append(datetime.now().month / 12.0)  # seasonal_factor
        
        return features
    
    def _prepare_disposition_training_data(self, training_data: List[Dict[str, Any]]) -> Tuple[List[List[float]], List[str]]:
        """Prepare training data for disposition model"""
        X, y = [], []
        
        for record in training_data:
            if 'disposition' in record:
                features = self._prepare_disposition_features(record)
                X.append(features)
                y.append(record['disposition'])
        
        return X, y
    
    def _prepare_timeline_training_data(self, training_data: List[Dict[str, Any]]) -> Tuple[List[List[float]], List[float]]:
        """Prepare training data for timeline model"""
        X, y = [], []
        
        for record in training_data:
            if 'processing_time' in record:
                features = self._prepare_timeline_features(record, 'processing')
                X.append(features)
                y.append(record['processing_time'])
        
        return X, y
    
    def _prepare_revenue_training_data(self, training_data: List[Dict[str, Any]]) -> Tuple[List[List[float]], List[float]]:
        """Prepare training data for revenue model"""
        X, y = [], []
        
        for record in training_data:
            if 'revenue' in record:
                features = self._prepare_revenue_features(record)
                X.append(features)
                y.append(record['revenue'])
        
        return X, y
    
    def _calculate_expected_value(self, vehicle_data: Dict[str, Any], disposition: str) -> float:
        """Calculate expected value for disposition"""
        base_value = vehicle_data.get('market_value', 5000)
        
        multipliers = {
            'auction': 0.8,
            'scrap': 0.3,
            'release': 0.0
        }
        
        return base_value * multipliers.get(disposition, 0.5)
    
    def _estimate_disposition_timeline(self, vehicle_data: Dict[str, Any], disposition: str) -> int:
        """Estimate timeline for disposition completion"""
        base_days = {
            'auction': 30,
            'scrap': 14,
            'release': 7
        }
        
        complexity_factor = vehicle_data.get('complexity_score', 0.5)
        return int(base_days.get(disposition, 21) * (1 + complexity_factor))
    
    def _identify_risk_factors(self, vehicle_data: Dict[str, Any], features: List[float]) -> List[str]:
        """Identify risk factors for prediction"""
        risks = []
        
        if vehicle_data.get('vehicle_age', 0) > 15:
            risks.append('high_vehicle_age')
        
        if vehicle_data.get('mileage', 0) > 200000:
            risks.append('high_mileage')
        
        if vehicle_data.get('condition_score', 1.0) < 0.3:
            risks.append('poor_condition')
        
        tow_date = pd.to_datetime(vehicle_data.get('tow_date', datetime.now()))
        if (datetime.now() - tow_date).days > 60:
            risks.append('extended_storage')
        
        return risks
    
    def _calculate_timeline_confidence(self, features: List[float], predicted_days: float) -> float:
        """Calculate confidence for timeline prediction"""
        # Simplified confidence calculation
        base_confidence = 0.8
        
        # Reduce confidence for longer predictions
        if predicted_days > 30:
            base_confidence *= 0.9
        if predicted_days > 60:
            base_confidence *= 0.8
        
        return max(0.1, min(1.0, base_confidence))
    
    def _calculate_delay_risk(self, vehicle_data: Dict[str, Any], stage: str) -> float:
        """Calculate risk of delays"""
        risk = 0.2  # Base risk
        
        if vehicle_data.get('complexity_score', 0.5) > 0.7:
            risk += 0.2
        
        if vehicle_data.get('external_dependencies', 0) > 0:
            risk += 0.3
        
        if not vehicle_data.get('documentation_complete', True):
            risk += 0.2
        
        return min(1.0, risk)
    
    def _calculate_bottleneck_probability(self, stage: str) -> float:
        """Calculate probability of bottleneck at stage"""
        # Simplified bottleneck probabilities by stage
        bottleneck_probs = {
            'intake': 0.1,
            'processing': 0.3,
            'inspection': 0.4,
            'disposition': 0.2,
            'completion': 0.1
        }
        
        return bottleneck_probs.get(stage, 0.25)
    
    def _generate_timeline_recommendations(self, vehicle_data: Dict[str, Any], 
                                         stage: str, delay_risk: float) -> List[str]:
        """Generate recommendations for timeline optimization"""
        recommendations = []
        
        if delay_risk > 0.6:
            recommendations.append('prioritize_processing')
            recommendations.append('allocate_additional_resources')
        
        if not vehicle_data.get('documentation_complete', True):
            recommendations.append('complete_documentation')
        
        if vehicle_data.get('external_dependencies', 0) > 0:
            recommendations.append('follow_up_external_dependencies')
        
        if stage == 'inspection' and delay_risk > 0.5:
            recommendations.append('schedule_priority_inspection')
        
        return recommendations
    
    def _calculate_storage_cost(self, vehicle_data: Dict[str, Any], scenario: str) -> float:
        """Calculate storage cost for scenario"""
        daily_rate = 15.0
        tow_date = pd.to_datetime(vehicle_data.get('tow_date', datetime.now()))
        days = (datetime.now() - tow_date).days
        
        # Add estimated additional days based on scenario
        additional_days = {
            'auction': 30,
            'scrap': 14,
            'release': 7
        }
        
        total_days = days + additional_days.get(scenario, 21)
        return total_days * daily_rate
    
    def _calculate_processing_cost(self, vehicle_data: Dict[str, Any], scenario: str) -> float:
        """Calculate processing cost for scenario"""
        base_costs = {
            'auction': 300,
            'scrap': 150,
            'release': 100
        }
        
        complexity_multiplier = 1 + vehicle_data.get('complexity_score', 0.5)
        return base_costs.get(scenario, 200) * complexity_multiplier
    
    def _get_optimization_factors(self, vehicle_data: Dict[str, Any]) -> List[str]:
        """Get factors that influence revenue optimization"""
        factors = []
        
        if vehicle_data.get('market_value', 0) > 10000:
            factors.append('high_value_vehicle')
        
        if vehicle_data.get('condition_score', 0.5) > 0.8:
            factors.append('excellent_condition')
        
        if vehicle_data.get('vehicle_age', 10) < 5:
            factors.append('low_age')
        
        season = datetime.now().month
        if season in [3, 4, 5, 9, 10]:  # Spring and fall
            factors.append('favorable_season')
        
        return factors
    
    def _calculate_revenue_confidence(self, results: Dict[str, Any]) -> float:
        """Calculate confidence in revenue optimization"""
        if not results:
            return 0.5
        
        # Check variance in net revenue across scenarios
        revenues = [r['net_revenue'] for r in results.values()]
        if not revenues:
            return 0.5
        
        variance = np.var(revenues)
        mean_revenue = np.mean(revenues)
        
        # Higher variance = lower confidence
        if mean_revenue > 0:
            cv = np.sqrt(variance) / mean_revenue
            confidence = max(0.1, 1.0 - min(cv, 0.9))
        else:
            confidence = 0.5
        
        return confidence
    
    def _get_anomaly_recommendations(self, anomalies: List[str]) -> List[str]:
        """Get recommendations for handling anomalies"""
        recommendations = []
        
        if 'extended_storage_period' in anomalies:
            recommendations.append('expedite_disposition')
            recommendations.append('review_storage_costs')
        
        if 'stage_processing_delay' in anomalies:
            recommendations.append('investigate_bottleneck')
            recommendations.append('reassign_resources')
        
        if 'high_storage_cost_ratio' in anomalies:
            recommendations.append('immediate_disposition_review')
            recommendations.append('cost_benefit_analysis')
        
        if 'multiple_stage_reversals' in anomalies:
            recommendations.append('workflow_review')
            recommendations.append('staff_training')
        
        return recommendations
    
    def _calculate_anomaly_severity(self, risk_score: float) -> str:
        """Calculate severity level for anomalies"""
        if risk_score >= 0.8:
            return 'critical'
        elif risk_score >= 0.6:
            return 'high'
        elif risk_score >= 0.4:
            return 'medium'
        else:
            return 'low'
    
    def _save_models(self):
        """Save trained models to disk"""
        try:
            for model_name, model in self.models.items():
                model_file = os.path.join(self.model_path, f'{model_name}_model.joblib')
                joblib.dump(model, model_file)
            
            for scaler_name, scaler in self.scalers.items():
                scaler_file = os.path.join(self.model_path, f'{scaler_name}_scaler.joblib')
                joblib.dump(scaler, scaler_file)
            
            logger.info("Models saved successfully")
        except Exception as e:
            logger.error(f"Error saving models: {str(e)}")
    
    def _load_models(self):
        """Load trained models from disk"""
        try:
            for model_name in ['disposition', 'timeline', 'revenue']:
                model_file = os.path.join(self.model_path, f'{model_name}_model.joblib')
                scaler_file = os.path.join(self.model_path, f'{model_name}_scaler.joblib')
                
                if os.path.exists(model_file):
                    self.models[model_name] = joblib.load(model_file)
                
                if os.path.exists(scaler_file):
                    self.scalers[model_name] = joblib.load(scaler_file)
            
            self.is_trained = len(self.models) > 0
            logger.info(f"Loaded {len(self.models)} models")
        except Exception as e:
            logger.error(f"Error loading models: {str(e)}")
    
    def _save_model_metrics(self, metrics: Dict[str, float]):
        """Save model performance metrics"""
        try:
            metrics_file = os.path.join(self.model_path, 'model_metrics.json')
            import json
            with open(metrics_file, 'w') as f:
                json.dump(metrics, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving model metrics: {str(e)}")
    
    def _load_model_metrics(self) -> Dict[str, float]:
        """Load model performance metrics"""
        try:
            metrics_file = os.path.join(self.model_path, 'model_metrics.json')
            if os.path.exists(metrics_file):
                import json
                with open(metrics_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Error loading model metrics: {str(e)}")
        return {}
    
    def _get_model_last_trained(self, model_name: str) -> Optional[datetime]:
        """Get last training date for model"""
        try:
            model_file = os.path.join(self.model_path, f'{model_name}_model.joblib')
            if os.path.exists(model_file):
                return datetime.fromtimestamp(os.path.getmtime(model_file))
        except Exception:
            pass
        return None
    
    def _needs_retraining(self, model_name: str) -> bool:
        """Check if model needs retraining"""
        last_trained = self._get_model_last_trained(model_name)
        if not last_trained:
            return True
        
        # Retrain if model is older than 30 days
        return (datetime.now() - last_trained).days > 30
    
    def _get_training_data_size(self) -> int:
        """Get size of training dataset"""
        training_data = self._prepare_training_data()
        return len(training_data)
    
    def _get_feature_importance(self) -> Dict[str, Dict[str, float]]:
        """Get feature importance for each model"""
        importance = {}
        
        for model_name, model in self.models.items():
            if hasattr(model, 'feature_importances_'):
                feature_names = self.feature_columns.get(model_name, [])
                if len(feature_names) == len(model.feature_importances_):
                    importance[model_name] = dict(zip(
                        feature_names, 
                        model.feature_importances_
                    ))
        
        return importance
