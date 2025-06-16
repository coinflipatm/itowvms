"""
Natural Language Processing Engine for iTow VMS

This module provides NLP capabilities for:
- Natural language queries for vehicle search and status
- Intelligent search with semantic understanding
- Voice command processing and recognition
- Automated report generation from natural language requests
- Chat-based interface for system interaction
"""

import logging
import re
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import json

logger = logging.getLogger(__name__)

@dataclass
class QueryResult:
    """Result of NLP query processing"""
    intent: str
    entities: Dict[str, Any]
    confidence: float
    response: str
    sql_query: Optional[str] = None
    data: Optional[List[Dict[str, Any]]] = None

@dataclass
class SearchResult:
    """Result of semantic search"""
    matches: List[Dict[str, Any]]
    query_interpretation: str
    search_strategy: str
    confidence: float
    suggestions: List[str]

class NLPEngine:
    """Natural Language Processing engine for intelligent system interaction"""
    
    def __init__(self, app=None):
        self.app = app
        self.intents = self._setup_intents()
        self.entity_patterns = self._setup_entity_patterns()
        self.query_templates = self._setup_query_templates()
        self.synonyms = self._setup_synonyms()
        
        logger.info("NLPEngine initialized")
    
    def process_query(self, query: str, user_context: Dict[str, Any] = None) -> QueryResult:
        """Process natural language query and return structured result"""
        try:
            # Clean and normalize query
            normalized_query = self._normalize_query(query)
            
            # Extract intent
            intent = self._extract_intent(normalized_query)
            
            # Extract entities
            entities = self._extract_entities(normalized_query)
            
            # Calculate confidence
            confidence = self._calculate_confidence(intent, entities, normalized_query)
            
            # Generate response based on intent
            if intent == 'vehicle_search':
                return self._handle_vehicle_search(entities, normalized_query, confidence)
            elif intent == 'status_inquiry':
                return self._handle_status_inquiry(entities, normalized_query, confidence)
            elif intent == 'report_request':
                return self._handle_report_request(entities, normalized_query, confidence)
            elif intent == 'analytics_request':
                return self._handle_analytics_request(entities, normalized_query, confidence)
            elif intent == 'help_request':
                return self._handle_help_request(entities, normalized_query, confidence)
            else:
                return self._handle_unknown_intent(normalized_query, confidence)
                
        except Exception as e:
            logger.error(f"Error processing query: {str(e)}")
            return QueryResult(
                intent='error',
                entities={},
                confidence=0.0,
                response=f"I'm sorry, I encountered an error processing your request: {str(e)}"
            )
    
    def semantic_search(self, query: str, search_scope: str = 'all') -> SearchResult:
        """Perform semantic search across vehicle database"""
        try:
            # Normalize query
            normalized_query = self._normalize_query(query)
            
            # Interpret search intent
            interpretation = self._interpret_search_query(normalized_query)
            
            # Generate search filters
            filters = self._generate_search_filters(interpretation)
            
            # Execute search
            matches = self._execute_semantic_search(filters, search_scope)
            
            # Generate suggestions
            suggestions = self._generate_search_suggestions(normalized_query, matches)
            
            # Determine search strategy
            strategy = self._determine_search_strategy(interpretation, filters)
            
            # Calculate confidence
            confidence = self._calculate_search_confidence(matches, interpretation)
            
            return SearchResult(
                matches=matches,
                query_interpretation=interpretation,
                search_strategy=strategy,
                confidence=confidence,
                suggestions=suggestions
            )
            
        except Exception as e:
            logger.error(f"Error in semantic search: {str(e)}")
            return SearchResult(
                matches=[],
                query_interpretation=query,
                search_strategy='error',
                confidence=0.0,
                suggestions=[]
            )
    
    def generate_voice_response(self, query_result: QueryResult) -> str:
        """Generate voice-optimized response"""
        try:
            response = query_result.response
            
            # Make response more conversational for voice
            if query_result.intent == 'vehicle_search':
                if query_result.data and len(query_result.data) > 0:
                    count = len(query_result.data)
                    response = f"I found {count} vehicle{'s' if count != 1 else ''} matching your search. "
                    
                    # Add details for first few results
                    for i, vehicle in enumerate(query_result.data[:3]):
                        make = vehicle.get('make', 'Unknown')
                        model = vehicle.get('model', 'Unknown')
                        status = vehicle.get('status', 'Unknown')
                        response += f"Vehicle {i+1}: {make} {model}, currently {status}. "
                    
                    if count > 3:
                        response += f"And {count - 3} more vehicles."
                else:
                    response = "I didn't find any vehicles matching your search criteria."
            
            elif query_result.intent == 'status_inquiry':
                if query_result.data and len(query_result.data) > 0:
                    vehicle = query_result.data[0]
                    make = vehicle.get('make', 'Unknown')
                    model = vehicle.get('model', 'Unknown')
                    status = vehicle.get('status', 'Unknown')
                    response = f"The {make} {model} is currently {status}."
                    
                    if vehicle.get('tow_date'):
                        tow_date = vehicle['tow_date']
                        response += f" It was towed on {tow_date}."
                else:
                    response = "I couldn't find information about that vehicle."
            
            # Add conversational elements
            response = self._add_voice_conversational_elements(response, query_result.confidence)
            
            return response
            
        except Exception as e:
            logger.error(f"Error generating voice response: {str(e)}")
            return "I'm sorry, I had trouble generating a response to your request."
    
    def extract_report_parameters(self, query: str) -> Dict[str, Any]:
        """Extract parameters for report generation from natural language"""
        try:
            parameters = {
                'report_type': 'summary',
                'date_range': 'last_30_days',
                'format': 'summary',
                'filters': {}
            }
            
            normalized_query = self._normalize_query(query)
            
            # Extract report type
            if any(word in normalized_query for word in ['financial', 'revenue', 'cost', 'money']):
                parameters['report_type'] = 'financial'
            elif any(word in normalized_query for word in ['operational', 'workflow', 'process', 'performance']):
                parameters['report_type'] = 'operational'
            elif any(word in normalized_query for word in ['compliance', 'audit', 'legal', 'regulation']):
                parameters['report_type'] = 'compliance'
            elif any(word in normalized_query for word in ['executive', 'summary', 'overview', 'dashboard']):
                parameters['report_type'] = 'executive'
            
            # Extract date range
            if any(word in normalized_query for word in ['today', 'daily']):
                parameters['date_range'] = 'today'
            elif any(word in normalized_query for word in ['week', 'weekly', 'last week']):
                parameters['date_range'] = 'last_7_days'
            elif any(word in normalized_query for word in ['month', 'monthly', 'last month']):
                parameters['date_range'] = 'last_30_days'
            elif any(word in normalized_query for word in ['quarter', 'quarterly']):
                parameters['date_range'] = 'last_90_days'
            elif any(word in normalized_query for word in ['year', 'yearly', 'annual']):
                parameters['date_range'] = 'last_365_days'
            
            # Extract format
            if any(word in normalized_query for word in ['detailed', 'complete', 'full']):
                parameters['format'] = 'detailed'
            elif any(word in normalized_query for word in ['brief', 'short', 'quick']):
                parameters['format'] = 'brief'
            
            # Extract filters
            entities = self._extract_entities(normalized_query)
            if 'status' in entities:
                parameters['filters']['status'] = entities['status']
            if 'location' in entities:
                parameters['filters']['location'] = entities['location']
            if 'vehicle_type' in entities:
                parameters['filters']['vehicle_type'] = entities['vehicle_type']
            
            return parameters
            
        except Exception as e:
            logger.error(f"Error extracting report parameters: {str(e)}")
            return {
                'report_type': 'summary',
                'date_range': 'last_30_days',
                'format': 'summary',
                'filters': {}
            }
    
    def get_query_suggestions(self, partial_query: str) -> List[str]:
        """Get intelligent query suggestions based on partial input"""
        try:
            suggestions = []
            normalized_partial = self._normalize_query(partial_query)
            
            # Common query patterns
            common_queries = [
                "Show me all vehicles",
                "What's the status of vehicle {license_plate}?",
                "Generate monthly financial report",
                "How many vehicles are pending disposition?",
                "Show vehicles towed today",
                "What's our processing time average?",
                "Generate compliance report for last quarter",
                "Show high-value vehicles",
                "What vehicles need immediate attention?",
                "Show storage cost analysis"
            ]
            
            # Filter suggestions based on partial query
            for query in common_queries:
                if self._query_matches_partial(query.lower(), normalized_partial):
                    suggestions.append(query)
            
            # Add context-specific suggestions
            if 'vehicle' in normalized_partial:
                suggestions.extend([
                    "Show vehicles by status",
                    "Find vehicles by make and model",
                    "Show vehicles towed in the last week"
                ])
            
            if 'report' in normalized_partial:
                suggestions.extend([
                    "Generate executive summary report",
                    "Create operational performance report",
                    "Generate financial analysis report"
                ])
            
            if 'status' in normalized_partial:
                suggestions.extend([
                    "Show vehicle status distribution",
                    "Find vehicles with pending status",
                    "Show status change history"
                ])
            
            return suggestions[:10]  # Limit to top 10 suggestions
            
        except Exception as e:
            logger.error(f"Error getting query suggestions: {str(e)}")
            return ["Show me all vehicles", "Generate summary report", "Vehicle status inquiry"]
    
    # Private helper methods
    
    def _setup_intents(self) -> Dict[str, List[str]]:
        """Setup intent recognition patterns"""
        return {
            'vehicle_search': [
                'show', 'find', 'search', 'list', 'get', 'display', 'vehicles', 'cars'
            ],
            'status_inquiry': [
                'status', 'what is', 'where is', 'how is', 'check status', 'current status'
            ],
            'report_request': [
                'report', 'generate', 'create', 'summary', 'analysis', 'export'
            ],
            'analytics_request': [
                'analytics', 'metrics', 'performance', 'statistics', 'dashboard', 'kpi'
            ],
            'help_request': [
                'help', 'how to', 'what can', 'explain', 'guide', 'tutorial'
            ]
        }
    
    def _setup_entity_patterns(self) -> Dict[str, List[str]]:
        """Setup entity extraction patterns"""
        return {
            'license_plate': [
                r'[A-Z0-9]{2,8}',  # Basic license plate pattern
                r'\b[A-Z]{1,3}[0-9]{1,4}[A-Z]?\b'
            ],
            'vehicle_make': [
                'toyota', 'honda', 'ford', 'chevrolet', 'bmw', 'mercedes', 'audi',
                'nissan', 'hyundai', 'kia', 'volkswagen', 'subaru', 'mazda'
            ],
            'status': [
                'pending', 'processing', 'completed', 'disposed', 'released',
                'auction', 'scrap', 'hold', 'investigation'
            ],
            'location': [
                'lot a', 'lot b', 'lot c', 'storage', 'impound', 'yard'
            ],
            'date_range': [
                'today', 'yesterday', 'this week', 'last week', 'this month',
                'last month', 'this year', 'last year'
            ]
        }
    
    def _setup_query_templates(self) -> Dict[str, str]:
        """Setup SQL query templates for different intents"""
        return {
            'vehicle_search': """
                SELECT * FROM vehicles 
                WHERE 1=1 
                {filters}
                ORDER BY tow_date DESC
                LIMIT 50
            """,
            'status_inquiry': """
                SELECT v.*, vl.action, vl.notes, vl.timestamp as last_update
                FROM vehicles v
                LEFT JOIN vehicle_logs vl ON v.id = vl.vehicle_id
                WHERE {vehicle_filter}
                ORDER BY vl.timestamp DESC
                LIMIT 1
            """,
            'analytics_summary': """
                SELECT 
                    COUNT(*) as total_vehicles,
                    COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending,
                    COUNT(CASE WHEN status = 'processing' THEN 1 END) as processing,
                    COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed
                FROM vehicles
                WHERE tow_date >= date('now', '{date_filter}')
            """
        }
    
    def _setup_synonyms(self) -> Dict[str, List[str]]:
        """Setup synonym mapping for better understanding"""
        return {
            'vehicle': ['car', 'auto', 'automobile', 'truck', 'van'],
            'status': ['state', 'condition', 'situation'],
            'find': ['search', 'locate', 'look for', 'get'],
            'show': ['display', 'list', 'present'],
            'report': ['summary', 'analysis', 'breakdown']
        }
    
    def _normalize_query(self, query: str) -> str:
        """Normalize query text for processing"""
        # Convert to lowercase
        normalized = query.lower().strip()
        
        # Remove extra whitespace
        normalized = re.sub(r'\s+', ' ', normalized)
        
        # Handle contractions
        contractions = {
            "what's": "what is",
            "where's": "where is",
            "how's": "how is",
            "can't": "cannot",
            "won't": "will not"
        }
        
        for contraction, expansion in contractions.items():
            normalized = normalized.replace(contraction, expansion)
        
        # Apply synonyms
        words = normalized.split()
        for i, word in enumerate(words):
            for base_word, synonyms in self.synonyms.items():
                if word in synonyms:
                    words[i] = base_word
        
        return ' '.join(words)
    
    def _extract_intent(self, query: str) -> str:
        """Extract intent from normalized query"""
        max_score = 0
        best_intent = 'unknown'
        
        for intent, keywords in self.intents.items():
            score = sum(1 for keyword in keywords if keyword in query)
            if score > max_score:
                max_score = score
                best_intent = intent
        
        return best_intent
    
    def _extract_entities(self, query: str) -> Dict[str, Any]:
        """Extract entities from query"""
        entities = {}
        
        # Extract license plate
        for pattern in self.entity_patterns['license_plate']:
            matches = re.findall(pattern, query.upper())
            if matches:
                entities['license_plate'] = matches[0]
                break
        
        # Extract vehicle make
        for make in self.entity_patterns['vehicle_make']:
            if make in query:
                entities['vehicle_make'] = make
                break
        
        # Extract status
        for status in self.entity_patterns['status']:
            if status in query:
                entities['status'] = status
                break
        
        # Extract location
        for location in self.entity_patterns['location']:
            if location in query:
                entities['location'] = location
                break
        
        # Extract date range
        for date_range in self.entity_patterns['date_range']:
            if date_range in query:
                entities['date_range'] = date_range
                break
        
        return entities
    
    def _calculate_confidence(self, intent: str, entities: Dict[str, Any], query: str) -> float:
        """Calculate confidence score for query interpretation"""
        base_confidence = 0.5
        
        # Boost confidence if intent was clearly identified
        if intent != 'unknown':
            base_confidence += 0.3
        
        # Boost confidence for each entity found
        base_confidence += len(entities) * 0.1
        
        # Boost confidence for specific patterns
        if any(keyword in query for keyword in ['show me', 'find all', 'get status']):
            base_confidence += 0.2
        
        return min(1.0, base_confidence)
    
    def _handle_vehicle_search(self, entities: Dict[str, Any], query: str, confidence: float) -> QueryResult:
        """Handle vehicle search queries"""
        try:
            filters = []
            
            if 'vehicle_make' in entities:
                filters.append(f"make LIKE '%{entities['vehicle_make']}%'")
            
            if 'status' in entities:
                filters.append(f"status = '{entities['status']}'")
            
            if 'location' in entities:
                filters.append(f"location LIKE '%{entities['location']}%'")
            
            if 'date_range' in entities:
                date_filter = self._convert_date_range(entities['date_range'])
                filters.append(f"tow_date >= {date_filter}")
            
            filter_clause = 'AND ' + ' AND '.join(filters) if filters else ''
            
            sql_query = self.query_templates['vehicle_search'].format(filters=filter_clause)
            
            # Execute query if app is available
            data = []
            if self.app:
                try:
                    from app.core.database import DatabaseManager
                    db = DatabaseManager()
                    results = db.execute_query(sql_query)
                    data = [dict(row) for row in results]
                except Exception as e:
                    logger.error(f"Database query error: {str(e)}")
            
            response = self._generate_search_response(data, entities)
            
            return QueryResult(
                intent='vehicle_search',
                entities=entities,
                confidence=confidence,
                response=response,
                sql_query=sql_query,
                data=data
            )
            
        except Exception as e:
            logger.error(f"Error handling vehicle search: {str(e)}")
            return QueryResult(
                intent='vehicle_search',
                entities=entities,
                confidence=0.0,
                response="I encountered an error searching for vehicles."
            )
    
    def _handle_status_inquiry(self, entities: Dict[str, Any], query: str, confidence: float) -> QueryResult:
        """Handle status inquiry queries"""
        try:
            if 'license_plate' in entities:
                vehicle_filter = f"license_plate = '{entities['license_plate']}'"
            else:
                # Try to find vehicle identifier in query
                words = query.split()
                vehicle_filter = "1=1"  # Default filter
            
            sql_query = self.query_templates['status_inquiry'].format(vehicle_filter=vehicle_filter)
            
            # Execute query if app is available
            data = []
            if self.app:
                try:
                    from app.core.database import DatabaseManager
                    db = DatabaseManager()
                    results = db.execute_query(sql_query)
                    data = [dict(row) for row in results]
                except Exception as e:
                    logger.error(f"Database query error: {str(e)}")
            
            response = self._generate_status_response(data, entities)
            
            return QueryResult(
                intent='status_inquiry',
                entities=entities,
                confidence=confidence,
                response=response,
                sql_query=sql_query,
                data=data
            )
            
        except Exception as e:
            logger.error(f"Error handling status inquiry: {str(e)}")
            return QueryResult(
                intent='status_inquiry',
                entities=entities,
                confidence=0.0,
                response="I encountered an error checking vehicle status."
            )
    
    def _handle_report_request(self, entities: Dict[str, Any], query: str, confidence: float) -> QueryResult:
        """Handle report generation requests"""
        try:
            report_params = self.extract_report_parameters(query)
            
            response = f"I can generate a {report_params['report_type']} report for {report_params['date_range']} in {report_params['format']} format."
            
            if report_params['filters']:
                filter_desc = ', '.join([f"{k}: {v}" for k, v in report_params['filters'].items()])
                response += f" Filters applied: {filter_desc}."
            
            response += " Would you like me to generate this report now?"
            
            return QueryResult(
                intent='report_request',
                entities=entities,
                confidence=confidence,
                response=response,
                data=[report_params]
            )
            
        except Exception as e:
            logger.error(f"Error handling report request: {str(e)}")
            return QueryResult(
                intent='report_request',
                entities=entities,
                confidence=0.0,
                response="I encountered an error processing your report request."
            )
    
    def _handle_analytics_request(self, entities: Dict[str, Any], query: str, confidence: float) -> QueryResult:
        """Handle analytics and metrics requests"""
        try:
            date_filter = '-30 days'  # Default to last 30 days
            
            if 'date_range' in entities:
                date_filter = self._convert_date_range_sql(entities['date_range'])
            
            sql_query = self.query_templates['analytics_summary'].format(date_filter=date_filter)
            
            # Execute query if app is available
            data = []
            if self.app:
                try:
                    from app.core.database import DatabaseManager
                    db = DatabaseManager()
                    results = db.execute_query(sql_query)
                    data = [dict(row) for row in results]
                except Exception as e:
                    logger.error(f"Database query error: {str(e)}")
            
            response = self._generate_analytics_response(data, entities)
            
            return QueryResult(
                intent='analytics_request',
                entities=entities,
                confidence=confidence,
                response=response,
                sql_query=sql_query,
                data=data
            )
            
        except Exception as e:
            logger.error(f"Error handling analytics request: {str(e)}")
            return QueryResult(
                intent='analytics_request',
                entities=entities,
                confidence=0.0,
                response="I encountered an error retrieving analytics data."
            )
    
    def _handle_help_request(self, entities: Dict[str, Any], query: str, confidence: float) -> QueryResult:
        """Handle help and guidance requests"""
        help_response = """
        Here are some things you can ask me:
        
        **Vehicle Search:**
        - "Show me all vehicles"
        - "Find Toyota vehicles"
        - "Show pending vehicles"
        
        **Status Inquiries:**
        - "What's the status of vehicle ABC123?"
        - "Check status of Honda Civic"
        
        **Reports:**
        - "Generate monthly financial report"
        - "Create compliance summary"
        - "Show operational metrics"
        
        **Analytics:**
        - "Show dashboard metrics"
        - "What's our processing time?"
        - "Vehicle status distribution"
        
        Just ask me in natural language and I'll do my best to help!
        """
        
        return QueryResult(
            intent='help_request',
            entities=entities,
            confidence=confidence,
            response=help_response.strip()
        )
    
    def _handle_unknown_intent(self, query: str, confidence: float) -> QueryResult:
        """Handle unknown or unclear queries"""
        response = f"I'm not sure I understand '{query}'. Here are some things you can try:\n\n"
        response += "• Ask about vehicle status: 'What's the status of vehicle ABC123?'\n"
        response += "• Search for vehicles: 'Show me all pending vehicles'\n"
        response += "• Request reports: 'Generate monthly summary report'\n"
        response += "• Get analytics: 'Show me the dashboard metrics'\n\n"
        response += "Type 'help' for more examples."
        
        return QueryResult(
            intent='unknown',
            entities={},
            confidence=confidence,
            response=response
        )
    
    def _interpret_search_query(self, query: str) -> str:
        """Interpret the semantic meaning of a search query"""
        interpretations = []
        
        if any(word in query for word in ['high value', 'expensive', 'valuable']):
            interpretations.append("high-value vehicles")
        
        if any(word in query for word in ['urgent', 'priority', 'immediate']):
            interpretations.append("urgent/priority vehicles")
        
        if any(word in query for word in ['old', 'aged', 'storage']):
            interpretations.append("long-term storage vehicles")
        
        if any(word in query for word in ['recent', 'new', 'today', 'latest']):
            interpretations.append("recently towed vehicles")
        
        return " and ".join(interpretations) if interpretations else "general vehicle search"
    
    def _generate_search_filters(self, interpretation: str) -> Dict[str, Any]:
        """Generate database filters based on search interpretation"""
        filters = {}
        
        if "high-value" in interpretation:
            filters['min_value'] = 10000
        
        if "urgent" in interpretation or "priority" in interpretation:
            filters['priority'] = 'high'
        
        if "long-term" in interpretation:
            filters['min_storage_days'] = 60
        
        if "recent" in interpretation:
            filters['max_days_since_tow'] = 7
        
        return filters
    
    def _execute_semantic_search(self, filters: Dict[str, Any], scope: str) -> List[Dict[str, Any]]:
        """Execute semantic search with generated filters"""
        try:
            if not self.app:
                return []
            
            from app.core.database import DatabaseManager
            db = DatabaseManager()
            
            # Build query based on filters
            conditions = []
            
            if 'min_value' in filters:
                conditions.append(f"market_value >= {filters['min_value']}")
            
            if 'priority' in filters:
                conditions.append(f"priority = '{filters['priority']}'")
            
            if 'min_storage_days' in filters:
                conditions.append(f"julianday('now') - julianday(tow_date) >= {filters['min_storage_days']}")
            
            if 'max_days_since_tow' in filters:
                conditions.append(f"julianday('now') - julianday(tow_date) <= {filters['max_days_since_tow']}")
            
            where_clause = " AND ".join(conditions) if conditions else "1=1"
            
            query = f"""
                SELECT * FROM vehicles 
                WHERE {where_clause}
                ORDER BY tow_date DESC
                LIMIT 50
            """
            
            results = db.execute_query(query)
            return [dict(row) for row in results]
            
        except Exception as e:
            logger.error(f"Error executing semantic search: {str(e)}")
            return []
    
    def _generate_search_suggestions(self, query: str, matches: List[Dict[str, Any]]) -> List[str]:
        """Generate search suggestions based on query and results"""
        suggestions = []
        
        # Suggest refinements if too many results
        if len(matches) > 20:
            suggestions.append("Try adding status filter (e.g., 'pending vehicles')")
            suggestions.append("Specify date range (e.g., 'vehicles towed this week')")
            suggestions.append("Add vehicle type (e.g., 'Toyota vehicles')")
        
        # Suggest alternatives if no results
        elif len(matches) == 0:
            suggestions.append("Try broader search terms")
            suggestions.append("Check spelling of vehicle details")
            suggestions.append("Remove specific filters")
        
        # Context-specific suggestions
        if 'status' not in query and len(matches) > 0:
            statuses = set(v.get('status', '') for v in matches[:10])
            for status in statuses:
                if status:
                    suggestions.append(f"Show only {status} vehicles")
        
        return suggestions[:5]  # Limit suggestions
    
    def _determine_search_strategy(self, interpretation: str, filters: Dict[str, Any]) -> str:
        """Determine the search strategy used"""
        if filters:
            return f"Filtered search: {interpretation}"
        else:
            return "Broad search across all vehicles"
    
    def _calculate_search_confidence(self, matches: List[Dict[str, Any]], interpretation: str) -> float:
        """Calculate confidence in search results"""
        base_confidence = 0.7
        
        # Boost confidence if results found
        if matches:
            base_confidence += 0.2
        
        # Boost confidence if interpretation was specific
        if any(term in interpretation for term in ['high-value', 'urgent', 'recent']):
            base_confidence += 0.1
        
        return min(1.0, base_confidence)
    
    def _convert_date_range(self, date_range: str) -> str:
        """Convert natural language date range to SQL"""
        conversions = {
            'today': "date('now')",
            'yesterday': "date('now', '-1 day')",
            'this week': "date('now', '-7 days')",
            'last week': "date('now', '-14 days')",
            'this month': "date('now', '-30 days')",
            'last month': "date('now', '-60 days')"
        }
        
        return conversions.get(date_range, "date('now', '-30 days')")
    
    def _convert_date_range_sql(self, date_range: str) -> str:
        """Convert date range to SQL days filter"""
        conversions = {
            'today': '-1 days',
            'this week': '-7 days',
            'last week': '-14 days',
            'this month': '-30 days',
            'last month': '-60 days'
        }
        
        return conversions.get(date_range, '-30 days')
    
    def _generate_search_response(self, data: List[Dict[str, Any]], entities: Dict[str, Any]) -> str:
        """Generate response for vehicle search"""
        if not data:
            return "No vehicles found matching your search criteria."
        
        count = len(data)
        response = f"Found {count} vehicle{'s' if count != 1 else ''}"
        
        # Add filter information
        filters = []
        if 'vehicle_make' in entities:
            filters.append(f"make: {entities['vehicle_make']}")
        if 'status' in entities:
            filters.append(f"status: {entities['status']}")
        
        if filters:
            response += f" matching {', '.join(filters)}"
        
        response += "."
        
        # Add summary of first few results
        if count <= 5:
            response += "\n\nResults:"
            for vehicle in data:
                make = vehicle.get('make', 'Unknown')
                model = vehicle.get('model', 'Unknown')
                license_plate = vehicle.get('license_plate', 'Unknown')
                status = vehicle.get('status', 'Unknown')
                response += f"\n• {make} {model} ({license_plate}) - {status}"
        else:
            response += f"\n\nShowing summary of results. Use filters to narrow down the search."
        
        return response
    
    def _generate_status_response(self, data: List[Dict[str, Any]], entities: Dict[str, Any]) -> str:
        """Generate response for status inquiry"""
        if not data:
            return "Vehicle not found or no status information available."
        
        vehicle = data[0]
        make = vehicle.get('make', 'Unknown')
        model = vehicle.get('model', 'Unknown')
        license_plate = vehicle.get('license_plate', 'Unknown')
        status = vehicle.get('status', 'Unknown')
        
        response = f"Vehicle {license_plate} ({make} {model}) is currently {status}."
        
        if vehicle.get('tow_date'):
            response += f" Towed on {vehicle['tow_date']}."
        
        if vehicle.get('last_update'):
            response += f" Last updated: {vehicle['last_update']}."
        
        if vehicle.get('notes'):
            response += f" Notes: {vehicle['notes'][:100]}..."
        
        return response
    
    def _generate_analytics_response(self, data: List[Dict[str, Any]], entities: Dict[str, Any]) -> str:
        """Generate response for analytics request"""
        if not data:
            return "Unable to retrieve analytics data."
        
        stats = data[0]
        total = stats.get('total_vehicles', 0)
        pending = stats.get('pending', 0)
        processing = stats.get('processing', 0)
        completed = stats.get('completed', 0)
        
        response = f"Vehicle Analytics Summary:\n"
        response += f"• Total vehicles: {total}\n"
        response += f"• Pending: {pending}\n"
        response += f"• Processing: {processing}\n"
        response += f"• Completed: {completed}"
        
        if total > 0:
            pending_pct = (pending / total) * 100
            response += f"\n• {pending_pct:.1f}% of vehicles are pending processing"
        
        return response
    
    def _add_voice_conversational_elements(self, response: str, confidence: float) -> str:
        """Add conversational elements for voice responses"""
        # Add confidence indicators
        if confidence < 0.6:
            response = "I think " + response.lower()
        elif confidence > 0.9:
            response = "I'm confident that " + response.lower()
        
        # Add polite elements
        if not response.startswith(("I", "Here", "You")):
            response = "Here's what I found: " + response
        
        return response
    
    def _query_matches_partial(self, full_query: str, partial: str) -> bool:
        """Check if full query matches partial input"""
        if not partial:
            return True
        
        words = partial.split()
        full_words = full_query.split()
        
        # Check if partial words match beginning of full query words
        for i, word in enumerate(words):
            if i < len(full_words) and full_words[i].startswith(word):
                continue
            else:
                return False
        
        return True
