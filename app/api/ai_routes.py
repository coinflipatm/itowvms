"""
AI API Routes for iTow Vehicle Management System

This module provides REST API endpoints to integrate AI engines with the core system,
enabling real-time AI-powered features through web interfaces.
"""

from flask import Blueprint, request, jsonify, current_app
from functools import wraps
import logging
import traceback
from datetime import datetime
import json

# Import AI engines
from app.ai import PredictiveEngine, NLPEngine, DocumentAI, DecisionEngine

# Create blueprint
ai_bp = Blueprint('ai', __name__, url_prefix='/api/ai')

logger = logging.getLogger(__name__)

def handle_ai_errors(f):
    """Decorator to handle AI-specific errors and provide consistent responses"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except ValueError as e:
            logger.error(f"AI Validation Error in {f.__name__}: {str(e)}")
            return jsonify({
                'success': False,
                'error': 'validation_error',
                'message': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }), 400
        except Exception as e:
            logger.error(f"AI Processing Error in {f.__name__}: {str(e)}\n{traceback.format_exc()}")
            return jsonify({
                'success': False,
                'error': 'processing_error',
                'message': 'An error occurred during AI processing',
                'timestamp': datetime.utcnow().isoformat()
            }), 500
    return decorated_function

def get_ai_engine(engine_type):
    """Get AI engine instance from Flask app context"""
    engine_map = {
        'predictive': 'predictive_engine',
        'nlp': 'nlp_engine',
        'document': 'document_ai',
        'decision': 'decision_engine'
    }
    
    engine_attr = engine_map.get(engine_type)
    if not engine_attr:
        raise ValueError(f"Unknown AI engine type: {engine_type}")
    
    engine = getattr(current_app, engine_attr, None)
    if not engine:
        raise RuntimeError(f"AI engine '{engine_type}' not initialized")
    
    return engine

# ============================================================================
# PREDICTIVE ANALYTICS ENDPOINTS
# ============================================================================

@ai_bp.route('/predict/disposition', methods=['POST'])
@handle_ai_errors
def predict_vehicle_disposition():
    """Predict optimal disposition for a vehicle"""
    data = request.get_json()
    
    if not data or 'vehicle_data' not in data:
        return jsonify({
            'success': False,
            'error': 'missing_data',
            'message': 'vehicle_data is required'
        }), 400
    
    predictive_engine = get_ai_engine('predictive')
    result = predictive_engine.predict_disposition(data['vehicle_data'])
    
    return jsonify({
        'success': True,
        'prediction': result,
        'timestamp': datetime.utcnow().isoformat()
    })

@ai_bp.route('/predict/timeline', methods=['POST'])
@handle_ai_errors
def predict_workflow_timeline():
    """Predict timeline for vehicle workflow completion"""
    data = request.get_json()
    
    if not data or 'vehicle_data' not in data:
        return jsonify({
            'success': False,
            'error': 'missing_data',
            'message': 'vehicle_data is required'
        }), 400
    
    predictive_engine = get_ai_engine('predictive')
    result = predictive_engine.predict_timeline(data['vehicle_data'])
    
    return jsonify({
        'success': True,
        'prediction': result,
        'timestamp': datetime.utcnow().isoformat()
    })

@ai_bp.route('/predict/revenue', methods=['POST'])
@handle_ai_errors
def optimize_revenue():
    """Get revenue optimization recommendations"""
    data = request.get_json()
    
    if not data or 'vehicles' not in data:
        return jsonify({
            'success': False,
            'error': 'missing_data',
            'message': 'vehicles array is required'
        }), 400
    
    predictive_engine = get_ai_engine('predictive')
    result = predictive_engine.optimize_revenue(data['vehicles'])
    
    return jsonify({
        'success': True,
        'optimization': result,
        'timestamp': datetime.utcnow().isoformat()
    })

@ai_bp.route('/predict/anomalies', methods=['POST'])
@handle_ai_errors
def detect_anomalies():
    """Detect anomalies in vehicle data"""
    data = request.get_json()
    
    if not data or 'vehicles' not in data:
        return jsonify({
            'success': False,
            'error': 'missing_data',
            'message': 'vehicles array is required'
        }), 400
    
    predictive_engine = get_ai_engine('predictive')
    result = predictive_engine.detect_anomalies(data['vehicles'])
    
    return jsonify({
        'success': True,
        'anomalies': result,
        'timestamp': datetime.utcnow().isoformat()
    })

# ============================================================================
# NATURAL LANGUAGE PROCESSING ENDPOINTS
# ============================================================================

@ai_bp.route('/nlp/query', methods=['POST'])
@handle_ai_errors
def process_natural_language_query():
    """Process natural language query about vehicles"""
    data = request.get_json()
    
    if not data or 'query' not in data:
        return jsonify({
            'success': False,
            'error': 'missing_data',
            'message': 'query is required'
        }), 400
    
    nlp_engine = get_ai_engine('nlp')
    result = nlp_engine.process_query(
        data['query'],
        context=data.get('context', {})
    )
    
    return jsonify({
        'success': True,
        'result': result,
        'timestamp': datetime.utcnow().isoformat()
    })

@ai_bp.route('/nlp/search', methods=['POST'])
@handle_ai_errors
def semantic_search():
    """Perform semantic search across vehicle database"""
    data = request.get_json()
    
    if not data or 'query' not in data:
        return jsonify({
            'success': False,
            'error': 'missing_data',
            'message': 'query is required'
        }), 400
    
    nlp_engine = get_ai_engine('nlp')
    result = nlp_engine.semantic_search(
        data['query'],
        vehicles=data.get('vehicles', []),
        limit=data.get('limit', 10)
    )
    
    return jsonify({
        'success': True,
        'results': result,
        'timestamp': datetime.utcnow().isoformat()
    })

@ai_bp.route('/nlp/extract', methods=['POST'])
@handle_ai_errors
def extract_report_parameters():
    """Extract report parameters from natural language"""
    data = request.get_json()
    
    if not data or 'text' not in data:
        return jsonify({
            'success': False,
            'error': 'missing_data',
            'message': 'text is required'
        }), 400
    
    nlp_engine = get_ai_engine('nlp')
    result = nlp_engine.extract_report_parameters(data['text'])
    
    return jsonify({
        'success': True,
        'parameters': result,
        'timestamp': datetime.utcnow().isoformat()
    })

@ai_bp.route('/nlp/suggestions', methods=['POST'])
@handle_ai_errors
def get_query_suggestions():
    """Get query suggestions and auto-completions"""
    data = request.get_json()
    
    if not data or 'partial_query' not in data:
        return jsonify({
            'success': False,
            'error': 'missing_data',
            'message': 'partial_query is required'
        }), 400
    
    nlp_engine = get_ai_engine('nlp')
    result = nlp_engine.get_query_suggestions(
        data['partial_query'],
        limit=data.get('limit', 5)
    )
    
    return jsonify({
        'success': True,
        'suggestions': result,
        'timestamp': datetime.utcnow().isoformat()
    })

# ============================================================================
# DOCUMENT AI ENDPOINTS
# ============================================================================

@ai_bp.route('/document/process', methods=['POST'])
@handle_ai_errors
def process_document():
    """Process a document with OCR and field extraction"""
    if 'file' not in request.files:
        return jsonify({
            'success': False,
            'error': 'missing_file',
            'message': 'file is required'
        }), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({
            'success': False,
            'error': 'invalid_file',
            'message': 'No file selected'
        }), 400
    
    document_ai = get_ai_engine('document')
    result = document_ai.process_document(file)
    
    return jsonify({
        'success': True,
        'result': result,
        'timestamp': datetime.utcnow().isoformat()
    })

@ai_bp.route('/document/extract', methods=['POST'])
@handle_ai_errors
def extract_vehicle_data():
    """Extract vehicle data from document text"""
    data = request.get_json()
    
    if not data or 'text' not in data:
        return jsonify({
            'success': False,
            'error': 'missing_data',
            'message': 'text is required'
        }), 400
    
    document_ai = get_ai_engine('document')
    result = document_ai.extract_vehicle_data(data['text'])
    
    return jsonify({
        'success': True,
        'extracted_data': result,
        'timestamp': datetime.utcnow().isoformat()
    })

@ai_bp.route('/document/validate', methods=['POST'])
@handle_ai_errors
def validate_document():
    """Validate document data against business rules"""
    data = request.get_json()
    
    if not data or 'document_data' not in data:
        return jsonify({
            'success': False,
            'error': 'missing_data',
            'message': 'document_data is required'
        }), 400
    
    document_ai = get_ai_engine('document')
    result = document_ai.validate_document(data['document_data'])
    
    return jsonify({
        'success': True,
        'validation': result,
        'timestamp': datetime.utcnow().isoformat()
    })

@ai_bp.route('/document/autofill', methods=['POST'])
@handle_ai_errors
def generate_autofill_data():
    """Generate form auto-fill data from extracted information"""
    data = request.get_json()
    
    if not data or 'extracted_data' not in data:
        return jsonify({
            'success': False,
            'error': 'missing_data',
            'message': 'extracted_data is required'
        }), 400
    
    document_ai = get_ai_engine('document')
    result = document_ai.generate_autofill_data(data['extracted_data'])
    
    return jsonify({
        'success': True,
        'autofill_data': result,
        'timestamp': datetime.utcnow().isoformat()
    })

# ============================================================================
# DECISION ENGINE ENDPOINTS
# ============================================================================

@ai_bp.route('/decision/disposition', methods=['POST'])
@handle_ai_errors
def make_disposition_decision():
    """Make automated disposition decision"""
    data = request.get_json()
    
    if not data or 'vehicle_data' not in data:
        return jsonify({
            'success': False,
            'error': 'missing_data',
            'message': 'vehicle_data is required'
        }), 400
    
    decision_engine = get_ai_engine('decision')
    result = decision_engine.make_disposition_decision(data['vehicle_data'])
    
    return jsonify({
        'success': True,
        'decision': result,
        'timestamp': datetime.utcnow().isoformat()
    })

@ai_bp.route('/decision/workflow', methods=['POST'])
@handle_ai_errors
def route_workflow():
    """Make workflow routing decisions"""
    data = request.get_json()
    
    if not data or 'vehicle_data' not in data:
        return jsonify({
            'success': False,
            'error': 'missing_data',
            'message': 'vehicle_data is required'
        }), 400
    
    decision_engine = get_ai_engine('decision')
    result = decision_engine.route_workflow(
        data['vehicle_data'],
        current_stage=data.get('current_stage')
    )
    
    return jsonify({
        'success': True,
        'routing': result,
        'timestamp': datetime.utcnow().isoformat()
    })

@ai_bp.route('/decision/priority', methods=['POST'])
@handle_ai_errors
def assign_priority():
    """Assign priority to vehicles/tasks"""
    data = request.get_json()
    
    if not data or 'items' not in data:
        return jsonify({
            'success': False,
            'error': 'missing_data',
            'message': 'items array is required'
        }), 400
    
    decision_engine = get_ai_engine('decision')
    result = decision_engine.assign_priority(data['items'])
    
    return jsonify({
        'success': True,
        'priorities': result,
        'timestamp': datetime.utcnow().isoformat()
    })

@ai_bp.route('/decision/escalation', methods=['POST'])
@handle_ai_errors
def assess_escalation():
    """Assess if situation requires escalation"""
    data = request.get_json()
    
    if not data or 'situation_data' not in data:
        return jsonify({
            'success': False,
            'error': 'missing_data',
            'message': 'situation_data is required'
        }), 400
    
    decision_engine = get_ai_engine('decision')
    result = decision_engine.assess_escalation(data['situation_data'])
    
    return jsonify({
        'success': True,
        'assessment': result,
        'timestamp': datetime.utcnow().isoformat()
    })

@ai_bp.route('/decision/resource-allocation', methods=['POST'])
@handle_ai_errors
def optimize_resource_allocation():
    """Optimize resource allocation across tasks"""
    data = request.get_json()
    
    if not data or 'pending_tasks' not in data:
        return jsonify({
            'success': False,
            'error': 'missing_data',
            'message': 'pending_tasks array is required'
        }), 400
    
    decision_engine = get_ai_engine('decision')
    result = decision_engine.optimize_resource_allocation(
        data['pending_tasks'],
        available_resources=data.get('available_resources', {})
    )
    
    return jsonify({
        'success': True,
        'allocation': result,
        'timestamp': datetime.utcnow().isoformat()
    })

@ai_bp.route('/decision/business-rules', methods=['POST'])
@handle_ai_errors
def evaluate_business_rules():
    """Evaluate business rules for a given context"""
    data = request.get_json()
    
    if not data or 'context' not in data:
        return jsonify({
            'success': False,
            'error': 'missing_data',
            'message': 'context is required'
        }), 400
    
    decision_engine = get_ai_engine('decision')
    result = decision_engine.evaluate_business_rules(
        data['context'],
        rules=data.get('rules', [])
    )
    
    return jsonify({
        'success': True,
        'evaluation': result,
        'timestamp': datetime.utcnow().isoformat()
    })

# ============================================================================
# AI SYSTEM MANAGEMENT ENDPOINTS
# ============================================================================

@ai_bp.route('/status', methods=['GET'])
@handle_ai_errors
def get_ai_system_status():
    """Get status of all AI engines"""
    engines = ['predictive', 'nlp', 'document', 'decision']
    status = {}
    
    for engine_type in engines:
        try:
            engine = get_ai_engine(engine_type)
            if hasattr(engine, 'get_status'):
                status[engine_type] = engine.get_status()
            else:
                status[engine_type] = {'status': 'available', 'initialized': True}
        except Exception as e:
            status[engine_type] = {'status': 'error', 'error': str(e)}
    
    overall_status = 'healthy' if all(
        s.get('status') in ['available', 'healthy'] for s in status.values()
    ) else 'degraded'
    
    return jsonify({
        'success': True,
        'overall_status': overall_status,
        'engines': status,
        'timestamp': datetime.utcnow().isoformat()
    })

@ai_bp.route('/retrain', methods=['POST'])
@handle_ai_errors
def retrain_models():
    """Retrain AI models with latest data"""
    data = request.get_json()
    engine_type = data.get('engine', 'predictive') if data else 'predictive'
    
    if engine_type not in ['predictive', 'nlp', 'document', 'decision']:
        return jsonify({
            'success': False,
            'error': 'invalid_engine',
            'message': f'Unknown engine type: {engine_type}'
        }), 400
    
    engine = get_ai_engine(engine_type)
    
    if not hasattr(engine, 'retrain'):
        return jsonify({
            'success': False,
            'error': 'not_supported',
            'message': f'Engine {engine_type} does not support retraining'
        }), 400
    
    result = engine.retrain(training_data=data.get('training_data'))
    
    return jsonify({
        'success': True,
        'result': result,
        'timestamp': datetime.utcnow().isoformat()
    })

@ai_bp.route('/metrics', methods=['GET'])
@handle_ai_errors
def get_ai_metrics():
    """Get AI performance metrics"""
    engines = ['predictive', 'nlp', 'document', 'decision']
    metrics = {}
    
    for engine_type in engines:
        try:
            engine = get_ai_engine(engine_type)
            if hasattr(engine, 'get_metrics'):
                metrics[engine_type] = engine.get_metrics()
            else:
                metrics[engine_type] = {'status': 'no_metrics_available'}
        except Exception as e:
            metrics[engine_type] = {'error': str(e)}
    
    return jsonify({
        'success': True,
        'metrics': metrics,
        'timestamp': datetime.utcnow().isoformat()
    })

# ============================================================================
# INTEGRATED AI WORKFLOW ENDPOINTS
# ============================================================================

@ai_bp.route('/workflow/vehicle-intake', methods=['POST'])
@handle_ai_errors
def ai_vehicle_intake():
    """Complete AI-powered vehicle intake workflow"""
    data = request.get_json()
    
    if not data:
        return jsonify({
            'success': False,
            'error': 'missing_data',
            'message': 'Request data is required'
        }), 400
    
    # Get all AI engines
    predictive_engine = get_ai_engine('predictive')
    nlp_engine = get_ai_engine('nlp')
    document_ai = get_ai_engine('document')
    decision_engine = get_ai_engine('decision')
    
    workflow_result = {
        'steps_completed': [],
        'vehicle_data': data.get('vehicle_data', {}),
        'recommendations': [],
        'confidence_scores': {}
    }
    
    # Step 1: Process any documents if provided
    if 'documents' in data:
        document_results = []
        for doc in data['documents']:
            doc_result = document_ai.extract_vehicle_data(doc)
            document_results.append(doc_result)
        
        workflow_result['document_extraction'] = document_results
        workflow_result['steps_completed'].append('document_processing')
    
    # Step 2: Make disposition prediction
    if workflow_result['vehicle_data']:
        disposition_pred = predictive_engine.predict_disposition(workflow_result['vehicle_data'])
        workflow_result['disposition_prediction'] = disposition_pred
        workflow_result['confidence_scores']['disposition'] = disposition_pred.get('confidence', 0.0)
        workflow_result['steps_completed'].append('disposition_prediction')
    
    # Step 3: Make workflow routing decision
    if workflow_result['vehicle_data']:
        routing_decision = decision_engine.route_workflow(workflow_result['vehicle_data'])
        workflow_result['workflow_routing'] = routing_decision
        workflow_result['confidence_scores']['routing'] = routing_decision.get('confidence', 0.0)
        workflow_result['steps_completed'].append('workflow_routing')
    
    # Step 4: Generate recommendations
    if workflow_result['vehicle_data']:
        recommendations = []
        
        # Add disposition recommendation
        if 'disposition_prediction' in workflow_result:
            pred = workflow_result['disposition_prediction']
            recommendations.append({
                'type': 'disposition',
                'action': pred.get('recommendation', 'review'),
                'confidence': pred.get('confidence', 0.0),
                'reasoning': pred.get('reasoning', 'Based on vehicle characteristics and market conditions')
            })
        
        # Add workflow recommendation
        if 'workflow_routing' in workflow_result:
            routing = workflow_result['workflow_routing']
            recommendations.append({
                'type': 'workflow',
                'action': routing.get('next_stage', 'review'),
                'confidence': routing.get('confidence', 0.0),
                'reasoning': routing.get('reasoning', 'Based on current stage and completion criteria')
            })
        
        workflow_result['recommendations'] = recommendations
        workflow_result['steps_completed'].append('recommendation_generation')
    
    # Calculate overall confidence
    if workflow_result['confidence_scores']:
        overall_confidence = sum(workflow_result['confidence_scores'].values()) / len(workflow_result['confidence_scores'])
        workflow_result['overall_confidence'] = overall_confidence
    
    return jsonify({
        'success': True,
        'workflow_result': workflow_result,
        'timestamp': datetime.utcnow().isoformat()
    })

@ai_bp.route('/workflow/smart-search', methods=['POST'])
@handle_ai_errors
def ai_smart_search():
    """AI-powered smart search combining NLP and ML"""
    data = request.get_json()
    
    if not data or 'query' not in data:
        return jsonify({
            'success': False,
            'error': 'missing_data',
            'message': 'query is required'
        }), 400
    
    nlp_engine = get_ai_engine('nlp')
    
    # Process natural language query
    query_result = nlp_engine.process_query(
        data['query'],
        context=data.get('context', {})
    )
    
    # Perform semantic search
    search_results = nlp_engine.semantic_search(
        data['query'],
        vehicles=data.get('vehicles', []),
        limit=data.get('limit', 10)
    )
    
    # Get query suggestions for refinement
    suggestions = nlp_engine.get_query_suggestions(
        data['query'],
        limit=5
    )
    
    return jsonify({
        'success': True,
        'query_analysis': query_result,
        'search_results': search_results,
        'suggestions': suggestions,
        'timestamp': datetime.utcnow().isoformat()
    })

# Error handlers
@ai_bp.errorhandler(404)
def ai_not_found(error):
    return jsonify({
        'success': False,
        'error': 'endpoint_not_found',
        'message': 'AI API endpoint not found',
        'timestamp': datetime.utcnow().isoformat()
    }), 404

@ai_bp.errorhandler(405)
def ai_method_not_allowed(error):
    return jsonify({
        'success': False,
        'error': 'method_not_allowed',
        'message': 'HTTP method not allowed for this AI endpoint',
        'timestamp': datetime.utcnow().isoformat()
    }), 405
