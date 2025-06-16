"""
Comprehensive Test Suite for AI Integration

This test suite validates all AI components and their integration with the core system.
"""

import pytest
import unittest
from unittest.mock import Mock, patch, MagicMock
import json
import os
import sys
from datetime import datetime, timedelta
import tempfile
from io import BytesIO

# Add the project root to Python path
sys.path.insert(0, '/workspaces/itowvms')

from app.ai import PredictiveEngine, NLPEngine, DocumentAI, DecisionEngine
from app.ai.integration import AIIntegrationManager
from app.api.ai_routes import ai_bp

class TestPredictiveEngine(unittest.TestCase):
    """Test the Predictive Engine component"""
    
    def setUp(self):
        """Set up test environment"""
        self.engine = PredictiveEngine()
        self.sample_vehicle_data = {
            'towbook_call_number': 'TEST001',
            'make': 'Toyota',
            'model': 'Camry',
            'year': '2018',
            'color': 'Blue',
            'vin': '1HGBH41JXMN109186',
            'tow_date': '2025-05-01',
            'status': 'New',
            'location': 'Downtown',
            'reason_for_tow': 'Abandoned',
            'days_in_lot': 15
        }
    
    def test_predict_disposition(self):
        """Test disposition prediction"""
        result = self.engine.predict_disposition(self.sample_vehicle_data)
        
        self.assertIsInstance(result, dict)
        self.assertIn('recommendation', result)
        self.assertIn('confidence', result)
        self.assertIn('reasoning', result)
        self.assertIn('factors', result)
        
        # Check confidence is between 0 and 1
        self.assertGreaterEqual(result['confidence'], 0.0)
        self.assertLessEqual(result['confidence'], 1.0)
        
        # Check recommendation is valid
        valid_recommendations = ['auction', 'scrap', 'release', 'hold']
        self.assertIn(result['recommendation'], valid_recommendations)
    
    def test_predict_timeline(self):
        """Test timeline prediction"""
        result = self.engine.predict_timeline(self.sample_vehicle_data)
        
        self.assertIsInstance(result, dict)
        self.assertIn('predictions', result)
        self.assertIn('overall_completion', result)
        
        predictions = result['predictions']
        self.assertIsInstance(predictions, dict)
        
        # Check each stage has required fields
        for stage, prediction in predictions.items():
            self.assertIn('estimated_days', prediction)
            self.assertIn('confidence', prediction)
            self.assertIn('completion_date', prediction)
    
    def test_optimize_revenue(self):
        """Test revenue optimization"""
        vehicles = [self.sample_vehicle_data.copy() for _ in range(3)]
        vehicles[1]['make'] = 'BMW'
        vehicles[1]['year'] = '2020'
        vehicles[2]['make'] = 'Honda'
        vehicles[2]['year'] = '2015'
        
        result = self.engine.optimize_revenue(vehicles)
        
        self.assertIsInstance(result, dict)
        self.assertIn('total_estimated_revenue', result)
        self.assertIn('optimization_strategy', result)
        self.assertIn('vehicle_recommendations', result)
        
        # Check each vehicle has recommendations
        for vehicle in vehicles:
            vehicle_id = vehicle['towbook_call_number']
            self.assertIn(vehicle_id, result['vehicle_recommendations'])
    
    def test_detect_anomalies(self):
        """Test anomaly detection"""
        vehicles = [self.sample_vehicle_data.copy() for _ in range(5)]
        
        # Create an anomalous vehicle
        vehicles[2]['days_in_lot'] = 200  # Unusually high
        vehicles[2]['towbook_call_number'] = 'ANOMALY001'
        
        result = self.engine.detect_anomalies(vehicles)
        
        self.assertIsInstance(result, dict)
        # Should detect the anomalous vehicle
        self.assertGreater(len(result), 0)
    
    def test_feature_engineering(self):
        """Test feature engineering"""
        features = self.engine._engineer_features(self.sample_vehicle_data)
        
        self.assertIsInstance(features, dict)
        self.assertIn('vehicle_age', features)
        self.assertIn('make_encoded', features)
        self.assertIn('model_encoded', features)
        self.assertIn('season', features)
        self.assertIn('is_luxury', features)


class TestNLPEngine(unittest.TestCase):
    """Test the NLP Engine component"""
    
    def setUp(self):
        """Set up test environment"""
        self.engine = NLPEngine()
        self.sample_vehicles = [
            {
                'towbook_call_number': 'TEST001',
                'make': 'Toyota',
                'model': 'Camry',
                'year': '2018',
                'color': 'Blue',
                'status': 'New'
            },
            {
                'towbook_call_number': 'TEST002',
                'make': 'BMW',
                'model': 'X5',
                'year': '2020',
                'color': 'Black',
                'status': 'Ready for Auction'
            }
        ]
    
    def test_process_query(self):
        """Test natural language query processing"""
        query = "Show me all blue Toyota vehicles"
        result = self.engine.process_query(query)
        
        self.assertIsInstance(result, dict)
        self.assertIn('intent', result)
        self.assertIn('entities', result)
        self.assertIn('confidence', result)
        self.assertIn('response_template', result)
    
    def test_semantic_search(self):
        """Test semantic search functionality"""
        query = "luxury black vehicles"
        result = self.engine.semantic_search(query, self.sample_vehicles)
        
        self.assertIsInstance(result, list)
        # Should find the BMW (luxury black vehicle)
        if result:
            self.assertIn('relevance_score', result[0])
            self.assertIn('vehicle', result[0])
    
    def test_extract_report_parameters(self):
        """Test report parameter extraction"""
        text = "Generate a report for vehicles from January 2025 to March 2025 with status Ready for Auction"
        result = self.engine.extract_report_parameters(text)
        
        self.assertIsInstance(result, dict)
        self.assertIn('date_range', result)
        self.assertIn('filters', result)
    
    def test_get_query_suggestions(self):
        """Test query suggestions"""
        partial_query = "show me"
        result = self.engine.get_query_suggestions(partial_query)
        
        self.assertIsInstance(result, list)
        if result:
            self.assertIsInstance(result[0], str)


class TestDocumentAI(unittest.TestCase):
    """Test the Document AI component"""
    
    def setUp(self):
        """Set up test environment"""
        self.engine = DocumentAI()
    
    def test_extract_vehicle_data(self):
        """Test vehicle data extraction from text"""
        sample_text = """
        Vehicle Registration
        VIN: 1HGBH41JXMN109186
        Make: Toyota
        Model: Camry
        Year: 2018
        License Plate: ABC123
        Owner: John Smith
        Address: 123 Main St, City, State 12345
        """
        
        result = self.engine.extract_vehicle_data(sample_text)
        
        self.assertIsInstance(result, dict)
        self.assertIn('extracted_fields', result)
        self.assertIn('confidence_scores', result)
        
        fields = result['extracted_fields']
        self.assertEqual(fields.get('vin'), '1HGBH41JXMN109186')
        self.assertEqual(fields.get('make'), 'Toyota')
        self.assertEqual(fields.get('model'), 'Camry')
    
    def test_validate_document(self):
        """Test document validation"""
        document_data = {
            'vin': '1HGBH41JXMN109186',
            'make': 'Toyota',
            'model': 'Camry',
            'year': '2018',
            'license_plate': 'ABC123'
        }
        
        result = self.engine.validate_document(document_data)
        
        self.assertIsInstance(result, dict)
        self.assertIn('is_valid', result)
        self.assertIn('validation_errors', result)
        self.assertIn('completeness_score', result)
    
    def test_generate_autofill_data(self):
        """Test autofill data generation"""
        extracted_data = {
            'extracted_fields': {
                'vin': '1HGBH41JXMN109186',
                'make': 'Toyota',
                'model': 'Camry',
                'year': '2018'
            }
        }
        
        result = self.engine.generate_autofill_data(extracted_data)
        
        self.assertIsInstance(result, dict)
        self.assertIn('form_fields', result)
        self.assertIn('confidence_scores', result)


class TestDecisionEngine(unittest.TestCase):
    """Test the Decision Engine component"""
    
    def setUp(self):
        """Set up test environment"""
        self.engine = DecisionEngine()
        self.sample_vehicle_data = {
            'towbook_call_number': 'TEST001',
            'make': 'Toyota',
            'model': 'Camry',
            'year': '2018',
            'status': 'New',
            'days_in_lot': 15,
            'estimated_value': 8000
        }
    
    def test_make_disposition_decision(self):
        """Test disposition decision making"""
        result = self.engine.make_disposition_decision(self.sample_vehicle_data)
        
        self.assertIsInstance(result, dict)
        self.assertIn('decision', result)
        self.assertIn('confidence', result)
        self.assertIn('reasoning', result)
        self.assertIn('factors_considered', result)
    
    def test_route_workflow(self):
        """Test workflow routing decisions"""
        result = self.engine.route_workflow(self.sample_vehicle_data, current_stage='New')
        
        self.assertIsInstance(result, dict)
        self.assertIn('next_stage', result)
        self.assertIn('confidence', result)
        self.assertIn('reasoning', result)
    
    def test_assign_priority(self):
        """Test priority assignment"""
        items = [
            {'id': 'task1', 'urgency': 'high', 'financial_impact': 5000},
            {'id': 'task2', 'urgency': 'medium', 'financial_impact': 2000},
            {'id': 'task3', 'urgency': 'low', 'financial_impact': 8000}
        ]
        
        result = self.engine.assign_priority(items)
        
        self.assertIsInstance(result, list)
        for item in result:
            self.assertIn('id', item)
            self.assertIn('priority_score', item)
            self.assertIn('priority_level', item)
    
    def test_assess_escalation(self):
        """Test escalation assessment"""
        situation_data = {
            'vehicle': self.sample_vehicle_data,
            'days_pending': 30,
            'complexity_score': 0.8
        }
        
        result = self.engine.assess_escalation(situation_data)
        
        self.assertIsInstance(result, dict)
        self.assertIn('should_escalate', result)
        self.assertIn('escalation_level', result)
        self.assertIn('reasoning', result)


class TestAIIntegration(unittest.TestCase):
    """Test the AI Integration Manager"""
    
    def setUp(self):
        """Set up test environment"""
        self.integration_manager = AIIntegrationManager()
        
        # Mock Flask app
        self.mock_app = Mock()
        self.mock_app.config = {
            'AI_ENABLED': True,
            'AI_CACHE_TTL': 300,
            'AI_ASYNC_PROCESSING': True,
            'AI_CONFIDENCE_THRESHOLD': 0.7
        }
    
    def test_initialization(self):
        """Test AI integration initialization"""
        self.integration_manager.init_app(self.mock_app)
        
        self.assertTrue(self.integration_manager.is_initialized)
        self.assertEqual(len(self.integration_manager.engines), 4)
    
    def test_enhance_vehicle_data(self):
        """Test vehicle data enhancement"""
        self.integration_manager.init_app(self.mock_app)
        
        vehicle_data = {
            'towbook_call_number': 'TEST001',
            'make': 'Toyota',
            'model': 'Camry',
            'year': '2018'
        }
        
        enhanced_data = self.integration_manager.enhance_vehicle_data(vehicle_data)
        
        self.assertIsInstance(enhanced_data, dict)
        self.assertIn('ai_disposition_prediction', enhanced_data)
        self.assertIn('ai_timeline_prediction', enhanced_data)
        self.assertIn('ai_recommendations', enhanced_data)
    
    def test_process_search_query(self):
        """Test search query processing"""
        self.integration_manager.init_app(self.mock_app)
        
        vehicles = [
            {'towbook_call_number': 'TEST001', 'make': 'Toyota', 'model': 'Camry'},
            {'towbook_call_number': 'TEST002', 'make': 'BMW', 'model': 'X5'}
        ]
        
        result = self.integration_manager.process_search_query("Toyota vehicles", vehicles)
        
        self.assertIsInstance(result, dict)
        self.assertIn('query_analysis', result)
        self.assertIn('search_results', result)
        self.assertIn('suggestions', result)
    
    def test_health_check(self):
        """Test AI system health check"""
        self.integration_manager.init_app(self.mock_app)
        
        health_status = self.integration_manager.health_check()
        
        self.assertIsInstance(health_status, dict)
        self.assertIn('overall', health_status)
        self.assertIn('engines', health_status)
        self.assertIn('issues', health_status)


class TestAIAPIRoutes(unittest.TestCase):
    """Test AI API routes"""
    
    def setUp(self):
        """Set up test Flask app with AI routes"""
        from flask import Flask
        
        self.app = Flask(__name__)
        self.app.config['TESTING'] = True
        self.app.config['AI_ENABLED'] = True
        
        # Register AI blueprint
        self.app.register_blueprint(ai_bp)
        
        # Mock AI engines
        self.app.predictive_engine = Mock()
        self.app.nlp_engine = Mock()
        self.app.document_ai = Mock()
        self.app.decision_engine = Mock()
        
        self.client = self.app.test_client()
    
    def test_predict_disposition_endpoint(self):
        """Test disposition prediction API endpoint"""
        # Mock response
        self.app.predictive_engine.predict_disposition.return_value = {
            'recommendation': 'auction',
            'confidence': 0.85,
            'reasoning': 'High value vehicle in good condition'
        }
        
        response = self.client.post('/api/ai/predict/disposition', 
                                  json={'vehicle_data': {'make': 'Toyota', 'model': 'Camry'}})
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertIn('prediction', data)
    
    def test_nlp_query_endpoint(self):
        """Test NLP query API endpoint"""
        # Mock response
        self.app.nlp_engine.process_query.return_value = {
            'intent': 'search',
            'entities': {'make': 'Toyota'},
            'confidence': 0.9
        }
        
        response = self.client.post('/api/ai/nlp/query',
                                  json={'query': 'Show me Toyota vehicles'})
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertIn('result', data)
    
    def test_ai_status_endpoint(self):
        """Test AI system status endpoint"""
        response = self.client.get('/api/ai/status')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertIn('engines', data)
    
    def test_error_handling(self):
        """Test API error handling"""
        # Test missing data
        response = self.client.post('/api/ai/predict/disposition', json={})
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertFalse(data['success'])
        self.assertEqual(data['error'], 'missing_data')


class TestIntegrationScenarios(unittest.TestCase):
    """Test complete integration scenarios"""
    
    def setUp(self):
        """Set up complete test environment"""
        self.integration_manager = AIIntegrationManager()
        
        # Mock Flask app
        self.mock_app = Mock()
        self.mock_app.config = {
            'AI_ENABLED': True,
            'AI_CACHE_TTL': 300,
            'AI_ASYNC_PROCESSING': True,
            'AI_CONFIDENCE_THRESHOLD': 0.7
        }
        
        self.integration_manager.init_app(self.mock_app)
    
    def test_complete_vehicle_intake_workflow(self):
        """Test complete AI-powered vehicle intake"""
        vehicle_data = {
            'towbook_call_number': 'TEST001',
            'make': 'Toyota',
            'model': 'Camry',
            'year': '2018',
            'vin': '1HGBH41JXMN109186',
            'tow_date': '2025-05-01'
        }
        
        # Test enhancement
        enhanced_data = self.integration_manager.enhance_vehicle_data(vehicle_data)
        self.assertIn('ai_disposition_prediction', enhanced_data)
        
        # Test workflow decision
        workflow_decision = self.integration_manager.make_workflow_decision(vehicle_data)
        self.assertIn('disposition', workflow_decision)
        self.assertIn('workflow', workflow_decision)
    
    def test_batch_processing_performance(self):
        """Test batch processing performance"""
        vehicles = []
        for i in range(100):
            vehicles.append({
                'towbook_call_number': f'TEST{i:03d}',
                'make': 'Toyota',
                'model': 'Camry',
                'year': '2018'
            })
        
        start_time = datetime.now()
        enhanced_vehicles = self.integration_manager.process_batch_vehicles(vehicles)
        end_time = datetime.now()
        
        processing_time = (end_time - start_time).total_seconds()
        
        # Should process 100 vehicles in reasonable time (less than 10 seconds)
        self.assertLess(processing_time, 10.0)
        self.assertEqual(len(enhanced_vehicles), 100)
    
    def test_ai_caching_performance(self):
        """Test AI caching functionality"""
        vehicle_data = {
            'towbook_call_number': 'CACHE001',
            'make': 'Toyota',
            'model': 'Camry'
        }
        
        # First call should populate cache
        start_time = datetime.now()
        enhanced_data1 = self.integration_manager.enhance_vehicle_data(vehicle_data)
        first_call_time = (datetime.now() - start_time).total_seconds()
        
        # Second call should use cache (faster)
        start_time = datetime.now()
        enhanced_data2 = self.integration_manager.enhance_vehicle_data(vehicle_data)
        second_call_time = (datetime.now() - start_time).total_seconds()
        
        # Cache should make subsequent calls faster
        self.assertLess(second_call_time, first_call_time * 0.5)


def run_ai_tests():
    """Run all AI integration tests"""
    
    print("=" * 80)
    print("RUNNING AI INTEGRATION TEST SUITE")
    print("=" * 80)
    
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add test classes
    test_classes = [
        TestPredictiveEngine,
        TestNLPEngine,
        TestDocumentAI,
        TestDecisionEngine,
        TestAIIntegration,
        TestAIAPIRoutes,
        TestIntegrationScenarios
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # Run tests with detailed output
    runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
    result = runner.run(test_suite)
    
    # Print summary
    print("\n" + "=" * 80)
    print("AI INTEGRATION TEST SUMMARY")
    print("=" * 80)
    print(f"Tests Run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(result.skipped) if hasattr(result, 'skipped') else 0}")
    
    if result.failures:
        print("\nFAILURES:")
        for test, traceback in result.failures:
            print(f"- {test}: {traceback}")
    
    if result.errors:
        print("\nERRORs:")
        for test, traceback in result.errors:
            print(f"- {test}: {traceback}")
    
    success_rate = ((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100) if result.testsRun > 0 else 0
    print(f"\nSuccess Rate: {success_rate:.1f}%")
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_ai_tests()
    sys.exit(0 if success else 1)
