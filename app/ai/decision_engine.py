"""
AI-Powered Decision Engine for iTow VMS

This module provides intelligent decision-making capabilities:
- Automated workflow decisions and routing
- Risk assessment and mitigation strategies
- Resource allocation optimization
- Exception handling and escalation
- Business rule enforcement with AI insights
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import json
from enum import Enum

logger = logging.getLogger(__name__)

class DecisionConfidence(Enum):
    """Confidence levels for AI decisions"""
    VERY_LOW = "very_low"
    LOW = "low" 
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"

class DecisionType(Enum):
    """Types of decisions the AI can make"""
    DISPOSITION = "disposition"
    WORKFLOW_ROUTING = "workflow_routing"
    RESOURCE_ALLOCATION = "resource_allocation"
    ESCALATION = "escalation"
    COMPLIANCE = "compliance"
    PRIORITY_ASSIGNMENT = "priority_assignment"

@dataclass
class Decision:
    """AI decision with context and reasoning"""
    decision_id: str
    decision_type: DecisionType
    recommended_action: str
    confidence: DecisionConfidence
    reasoning: List[str]
    supporting_data: Dict[str, Any]
    alternative_options: List[Dict[str, Any]]
    risk_assessment: Dict[str, float]
    requires_human_approval: bool
    timestamp: datetime

@dataclass
class RiskAssessment:
    """Risk assessment for a decision or action"""
    overall_risk: float  # 0.0 to 1.0
    risk_factors: Dict[str, float]
    mitigation_strategies: List[str]
    escalation_triggers: List[str]
    confidence: float

@dataclass
class BusinessRule:
    """Business rule definition"""
    rule_id: str
    name: str
    condition: str
    action: str
    priority: int
    active: bool
    exceptions: List[str]

class DecisionEngine:
    """AI-powered decision engine for intelligent automation"""
    
    def __init__(self, app=None):
        self.app = app
        self.business_rules = self._setup_business_rules()
        self.decision_thresholds = self._setup_decision_thresholds()
        self.risk_models = self._setup_risk_models()
        self.escalation_rules = self._setup_escalation_rules()
        self.decision_history = []
        
        logger.info("DecisionEngine initialized")
    
    def make_disposition_decision(self, vehicle_data: Dict[str, Any], 
                                context: Dict[str, Any] = None) -> Decision:
        """Make AI-powered disposition decision for a vehicle"""
        try:
            decision_id = f"disp_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{vehicle_data.get('id', 'unknown')}"
            
            # Analyze vehicle characteristics
            vehicle_analysis = self._analyze_vehicle_characteristics(vehicle_data)
            
            # Calculate financial projections
            financial_analysis = self._analyze_financial_projections(vehicle_data)
            
            # Assess storage and processing costs
            cost_analysis = self._analyze_costs(vehicle_data)
            
            # Evaluate market conditions
            market_analysis = self._analyze_market_conditions(vehicle_data)
            
            # Apply business rules
            rule_results = self._apply_business_rules(vehicle_data, DecisionType.DISPOSITION)
            
            # Generate decision
            decision_data = {
                'vehicle_analysis': vehicle_analysis,
                'financial_analysis': financial_analysis,
                'cost_analysis': cost_analysis,
                'market_analysis': market_analysis,
                'rule_results': rule_results
            }
            
            recommended_action = self._determine_best_disposition(decision_data)
            confidence = self._calculate_disposition_confidence(decision_data)
            reasoning = self._generate_disposition_reasoning(decision_data, recommended_action)
            alternatives = self._generate_disposition_alternatives(decision_data)
            risk_assessment = self._assess_disposition_risks(vehicle_data, recommended_action)
            
            # Determine if human approval is needed
            requires_approval = self._requires_human_approval(
                DecisionType.DISPOSITION, confidence, risk_assessment, vehicle_data
            )
            
            decision = Decision(
                decision_id=decision_id,
                decision_type=DecisionType.DISPOSITION,
                recommended_action=recommended_action,
                confidence=confidence,
                reasoning=reasoning,
                supporting_data=decision_data,
                alternative_options=alternatives,
                risk_assessment=risk_assessment,
                requires_human_approval=requires_approval,
                timestamp=datetime.now()
            )
            
            self.decision_history.append(decision)
            logger.info(f"Generated disposition decision {decision_id}: {recommended_action}")
            
            return decision
            
        except Exception as e:
            logger.error(f"Error making disposition decision: {str(e)}")
            return self._create_error_decision(DecisionType.DISPOSITION, str(e))
    
    def make_workflow_routing_decision(self, vehicle_data: Dict[str, Any], 
                                     current_stage: str, context: Dict[str, Any] = None) -> Decision:
        """Make AI-powered workflow routing decision"""
        try:
            decision_id = f"route_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{vehicle_data.get('id', 'unknown')}"
            
            # Analyze current workflow state
            workflow_analysis = self._analyze_workflow_state(vehicle_data, current_stage)
            
            # Check stage completion criteria
            completion_analysis = self._analyze_stage_completion(vehicle_data, current_stage)
            
            # Evaluate next stage requirements
            next_stage_analysis = self._analyze_next_stage_requirements(vehicle_data, current_stage)
            
            # Check resource availability
            resource_analysis = self._analyze_resource_availability(current_stage)
            
            # Apply workflow rules
            rule_results = self._apply_business_rules(vehicle_data, DecisionType.WORKFLOW_ROUTING)
            
            decision_data = {
                'workflow_analysis': workflow_analysis,
                'completion_analysis': completion_analysis,
                'next_stage_analysis': next_stage_analysis,
                'resource_analysis': resource_analysis,
                'rule_results': rule_results
            }
            
            recommended_action = self._determine_next_workflow_action(decision_data, current_stage)
            confidence = self._calculate_workflow_confidence(decision_data)
            reasoning = self._generate_workflow_reasoning(decision_data, recommended_action)
            alternatives = self._generate_workflow_alternatives(decision_data, current_stage)
            risk_assessment = self._assess_workflow_risks(vehicle_data, recommended_action)
            
            requires_approval = self._requires_human_approval(
                DecisionType.WORKFLOW_ROUTING, confidence, risk_assessment, vehicle_data
            )
            
            decision = Decision(
                decision_id=decision_id,
                decision_type=DecisionType.WORKFLOW_ROUTING,
                recommended_action=recommended_action,
                confidence=confidence,
                reasoning=reasoning,
                supporting_data=decision_data,
                alternative_options=alternatives,
                risk_assessment=risk_assessment,
                requires_human_approval=requires_approval,
                timestamp=datetime.now()
            )
            
            self.decision_history.append(decision)
            logger.info(f"Generated workflow routing decision {decision_id}: {recommended_action}")
            
            return decision
            
        except Exception as e:
            logger.error(f"Error making workflow routing decision: {str(e)}")
            return self._create_error_decision(DecisionType.WORKFLOW_ROUTING, str(e))
    
    def make_priority_assignment(self, vehicle_data: Dict[str, Any], 
                               context: Dict[str, Any] = None) -> Decision:
        """Make AI-powered priority assignment decision"""
        try:
            decision_id = f"priority_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{vehicle_data.get('id', 'unknown')}"
            
            # Calculate urgency factors
            urgency_analysis = self._calculate_urgency_factors(vehicle_data)
            
            # Assess financial impact
            financial_impact = self._assess_financial_impact(vehicle_data)
            
            # Check compliance requirements
            compliance_analysis = self._analyze_compliance_requirements(vehicle_data)
            
            # Evaluate resource constraints
            resource_constraints = self._evaluate_resource_constraints()
            
            # Apply priority rules
            rule_results = self._apply_business_rules(vehicle_data, DecisionType.PRIORITY_ASSIGNMENT)
            
            decision_data = {
                'urgency_analysis': urgency_analysis,
                'financial_impact': financial_impact,
                'compliance_analysis': compliance_analysis,
                'resource_constraints': resource_constraints,
                'rule_results': rule_results
            }
            
            recommended_action = self._determine_priority_level(decision_data)
            confidence = self._calculate_priority_confidence(decision_data)
            reasoning = self._generate_priority_reasoning(decision_data, recommended_action)
            alternatives = self._generate_priority_alternatives(decision_data)
            risk_assessment = self._assess_priority_risks(vehicle_data, recommended_action)
            
            requires_approval = self._requires_human_approval(
                DecisionType.PRIORITY_ASSIGNMENT, confidence, risk_assessment, vehicle_data
            )
            
            decision = Decision(
                decision_id=decision_id,
                decision_type=DecisionType.PRIORITY_ASSIGNMENT,
                recommended_action=recommended_action,
                confidence=confidence,
                reasoning=reasoning,
                supporting_data=decision_data,
                alternative_options=alternatives,
                risk_assessment=risk_assessment,
                requires_human_approval=requires_approval,
                timestamp=datetime.now()
            )
            
            self.decision_history.append(decision)
            logger.info(f"Generated priority assignment decision {decision_id}: {recommended_action}")
            
            return decision
            
        except Exception as e:
            logger.error(f"Error making priority assignment decision: {str(e)}")
            return self._create_error_decision(DecisionType.PRIORITY_ASSIGNMENT, str(e))
    
    def assess_escalation_need(self, vehicle_data: Dict[str, Any], 
                             issue_context: Dict[str, Any]) -> Decision:
        """Assess if a situation requires escalation"""
        try:
            decision_id = f"escalation_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{vehicle_data.get('id', 'unknown')}"
            
            # Analyze issue severity
            severity_analysis = self._analyze_issue_severity(issue_context)
            
            # Check time criticality
            time_analysis = self._analyze_time_criticality(vehicle_data, issue_context)
            
            # Evaluate resource needs
            resource_needs = self._evaluate_escalation_resource_needs(issue_context)
            
            # Check escalation triggers
            trigger_analysis = self._check_escalation_triggers(vehicle_data, issue_context)
            
            decision_data = {
                'severity_analysis': severity_analysis,
                'time_analysis': time_analysis,
                'resource_needs': resource_needs,
                'trigger_analysis': trigger_analysis
            }
            
            recommended_action = self._determine_escalation_action(decision_data)
            confidence = self._calculate_escalation_confidence(decision_data)
            reasoning = self._generate_escalation_reasoning(decision_data, recommended_action)
            alternatives = self._generate_escalation_alternatives(decision_data)
            risk_assessment = self._assess_escalation_risks(vehicle_data, recommended_action)
            
            # Escalation decisions rarely need approval (they are the approval mechanism)
            requires_approval = False
            
            decision = Decision(
                decision_id=decision_id,
                decision_type=DecisionType.ESCALATION,
                recommended_action=recommended_action,
                confidence=confidence,
                reasoning=reasoning,
                supporting_data=decision_data,
                alternative_options=alternatives,
                risk_assessment=risk_assessment,
                requires_human_approval=requires_approval,
                timestamp=datetime.now()
            )
            
            self.decision_history.append(decision)
            logger.info(f"Generated escalation decision {decision_id}: {recommended_action}")
            
            return decision
            
        except Exception as e:
            logger.error(f"Error assessing escalation need: {str(e)}")
            return self._create_error_decision(DecisionType.ESCALATION, str(e))
    
    def optimize_resource_allocation(self, available_resources: Dict[str, Any], 
                                   pending_tasks: List[Dict[str, Any]]) -> Decision:
        """Optimize resource allocation across pending tasks"""
        try:
            decision_id = f"resource_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Analyze resource capacity
            capacity_analysis = self._analyze_resource_capacity(available_resources)
            
            # Prioritize tasks
            task_prioritization = self._prioritize_tasks(pending_tasks)
            
            # Calculate optimal allocation
            allocation_analysis = self._calculate_optimal_allocation(
                available_resources, task_prioritization
            )
            
            # Consider constraints
            constraint_analysis = self._analyze_allocation_constraints(
                available_resources, pending_tasks
            )
            
            decision_data = {
                'capacity_analysis': capacity_analysis,
                'task_prioritization': task_prioritization,
                'allocation_analysis': allocation_analysis,
                'constraint_analysis': constraint_analysis
            }
            
            recommended_action = self._determine_resource_allocation(decision_data)
            confidence = self._calculate_allocation_confidence(decision_data)
            reasoning = self._generate_allocation_reasoning(decision_data, recommended_action)
            alternatives = self._generate_allocation_alternatives(decision_data)
            risk_assessment = self._assess_allocation_risks(recommended_action)
            
            requires_approval = self._requires_human_approval(
                DecisionType.RESOURCE_ALLOCATION, confidence, risk_assessment, {}
            )
            
            decision = Decision(
                decision_id=decision_id,
                decision_type=DecisionType.RESOURCE_ALLOCATION,
                recommended_action=recommended_action,
                confidence=confidence,
                reasoning=reasoning,
                supporting_data=decision_data,
                alternative_options=alternatives,
                risk_assessment=risk_assessment,
                requires_human_approval=requires_approval,
                timestamp=datetime.now()
            )
            
            self.decision_history.append(decision)
            logger.info(f"Generated resource allocation decision {decision_id}")
            
            return decision
            
        except Exception as e:
            logger.error(f"Error optimizing resource allocation: {str(e)}")
            return self._create_error_decision(DecisionType.RESOURCE_ALLOCATION, str(e))
    
    def get_decision_explanation(self, decision_id: str) -> Dict[str, Any]:
        """Get detailed explanation of a decision"""
        try:
            decision = next((d for d in self.decision_history if d.decision_id == decision_id), None)
            
            if not decision:
                return {
                    'error': 'Decision not found',
                    'decision_id': decision_id
                }
            
            explanation = {
                'decision_id': decision.decision_id,
                'type': decision.decision_type.value,
                'recommended_action': decision.recommended_action,
                'confidence': decision.confidence.value,
                'timestamp': decision.timestamp.isoformat(),
                'reasoning': {
                    'primary_factors': decision.reasoning,
                    'supporting_data': decision.supporting_data,
                    'risk_assessment': decision.risk_assessment
                },
                'alternatives': decision.alternative_options,
                'approval_required': decision.requires_human_approval,
                'decision_tree': self._generate_decision_tree(decision),
                'what_if_scenarios': self._generate_what_if_scenarios(decision)
            }
            
            return explanation
            
        except Exception as e:
            logger.error(f"Error getting decision explanation: {str(e)}")
            return {
                'error': str(e),
                'decision_id': decision_id
            }
    
    def update_business_rules(self, new_rules: List[BusinessRule]) -> Dict[str, Any]:
        """Update business rules for decision making"""
        try:
            updated_count = 0
            added_count = 0
            
            for rule in new_rules:
                existing_rule = next((r for r in self.business_rules if r.rule_id == rule.rule_id), None)
                
                if existing_rule:
                    # Update existing rule
                    idx = self.business_rules.index(existing_rule)
                    self.business_rules[idx] = rule
                    updated_count += 1
                else:
                    # Add new rule
                    self.business_rules.append(rule)
                    added_count += 1
            
            # Sort rules by priority
            self.business_rules.sort(key=lambda r: r.priority)
            
            logger.info(f"Updated {updated_count} and added {added_count} business rules")
            
            return {
                'status': 'success',
                'updated_rules': updated_count,
                'added_rules': added_count,
                'total_rules': len(self.business_rules)
            }
            
        except Exception as e:
            logger.error(f"Error updating business rules: {str(e)}")
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def get_decision_statistics(self) -> Dict[str, Any]:
        """Get statistics about AI decisions"""
        try:
            if not self.decision_history:
                return {
                    'total_decisions': 0,
                    'by_type': {},
                    'by_confidence': {},
                    'approval_rate': 0.0,
                    'accuracy_metrics': {}
                }
            
            # Count decisions by type
            by_type = {}
            for decision in self.decision_history:
                decision_type = decision.decision_type.value
                by_type[decision_type] = by_type.get(decision_type, 0) + 1
            
            # Count decisions by confidence
            by_confidence = {}
            for decision in self.decision_history:
                confidence = decision.confidence.value
                by_confidence[confidence] = by_confidence.get(confidence, 0) + 1
            
            # Calculate approval rate
            requiring_approval = sum(1 for d in self.decision_history if d.requires_human_approval)
            approval_rate = requiring_approval / len(self.decision_history) * 100
            
            # Calculate average risk scores
            risk_scores = []
            for decision in self.decision_history:
                if 'overall_risk' in decision.risk_assessment:
                    risk_scores.append(decision.risk_assessment['overall_risk'])
            
            avg_risk = sum(risk_scores) / len(risk_scores) if risk_scores else 0.0
            
            return {
                'total_decisions': len(self.decision_history),
                'by_type': by_type,
                'by_confidence': by_confidence,
                'approval_rate': approval_rate,
                'average_risk_score': avg_risk,
                'recent_decisions': len([d for d in self.decision_history 
                                       if (datetime.now() - d.timestamp).days <= 7]),
                'accuracy_metrics': {
                    'high_confidence_decisions': len([d for d in self.decision_history 
                                                    if d.confidence in [DecisionConfidence.HIGH, DecisionConfidence.VERY_HIGH]]),
                    'low_risk_decisions': len([d for d in self.decision_history 
                                             if d.risk_assessment.get('overall_risk', 1.0) < 0.3])
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting decision statistics: {str(e)}")
            return {
                'total_decisions': 0,
                'error': str(e)
            }
    
    # Private helper methods
    
    def _setup_business_rules(self) -> List[BusinessRule]:
        """Setup default business rules"""
        return [
            BusinessRule(
                rule_id="high_value_auction",
                name="High Value Vehicle Auction Rule",
                condition="market_value > 15000 AND condition_score > 0.7",
                action="disposition_auction",
                priority=1,
                active=True,
                exceptions=["flood_damage", "total_loss"]
            ),
            BusinessRule(
                rule_id="low_value_scrap",
                name="Low Value Vehicle Scrap Rule", 
                condition="market_value < 2000 OR condition_score < 0.3",
                action="disposition_scrap",
                priority=2,
                active=True,
                exceptions=["classic_car", "rare_model"]
            ),
            BusinessRule(
                rule_id="storage_cost_threshold",
                name="Storage Cost Threshold Rule",
                condition="storage_cost > market_value * 0.5",
                action="expedite_disposition",
                priority=1,
                active=True,
                exceptions=[]
            ),
            BusinessRule(
                rule_id="compliance_hold",
                name="Compliance Hold Rule",
                condition="legal_hold = true OR investigation_pending = true",
                action="hold_disposition",
                priority=0,  # Highest priority
                active=True,
                exceptions=[]
            )
        ]
    
    def _setup_decision_thresholds(self) -> Dict[str, Dict[str, float]]:
        """Setup decision confidence thresholds"""
        return {
            'disposition': {
                'high_confidence': 0.8,
                'medium_confidence': 0.6,
                'low_confidence': 0.4
            },
            'workflow': {
                'high_confidence': 0.85,
                'medium_confidence': 0.65,
                'low_confidence': 0.45
            },
            'escalation': {
                'high_confidence': 0.9,
                'medium_confidence': 0.7,
                'low_confidence': 0.5
            }
        }
    
    def _setup_risk_models(self) -> Dict[str, Dict[str, float]]:
        """Setup risk assessment models"""
        return {
            'disposition_risks': {
                'market_volatility': 0.1,
                'storage_cost_escalation': 0.2,
                'legal_complications': 0.8,
                'documentation_issues': 0.3
            },
            'workflow_risks': {
                'processing_delays': 0.3,
                'resource_unavailability': 0.4,
                'compliance_violations': 0.9,
                'data_quality_issues': 0.2
            }
        }
    
    def _setup_escalation_rules(self) -> List[Dict[str, Any]]:
        """Setup escalation rules"""
        return [
            {
                'trigger': 'high_value_vehicle',
                'condition': 'market_value > 50000',
                'escalation_level': 'supervisor',
                'urgency': 'high'
            },
            {
                'trigger': 'legal_complications',
                'condition': 'legal_hold = true',
                'escalation_level': 'legal_team',
                'urgency': 'critical'
            },
            {
                'trigger': 'processing_delay',
                'condition': 'days_in_system > 60',
                'escalation_level': 'manager',
                'urgency': 'medium'
            }
        ]
    
    def _analyze_vehicle_characteristics(self, vehicle_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze vehicle characteristics for decision making"""
        analysis = {
            'market_value': vehicle_data.get('market_value', 0),
            'condition_score': vehicle_data.get('condition_score', 0.5),
            'age_factor': self._calculate_age_factor(vehicle_data),
            'desirability_score': self._calculate_desirability_score(vehicle_data),
            'maintenance_cost': self._estimate_maintenance_cost(vehicle_data)
        }
        
        # Calculate overall attractiveness for auction
        analysis['auction_attractiveness'] = (
            analysis['condition_score'] * 0.4 +
            analysis['desirability_score'] * 0.3 +
            (1 - analysis['age_factor']) * 0.3
        )
        
        return analysis
    
    def _analyze_financial_projections(self, vehicle_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze financial projections for different dispositions"""
        market_value = vehicle_data.get('market_value', 0)
        
        return {
            'auction_projection': {
                'expected_revenue': market_value * 0.8,
                'confidence': 0.7,
                'time_to_sale': 30
            },
            'scrap_projection': {
                'expected_revenue': market_value * 0.3,
                'confidence': 0.9,
                'time_to_sale': 7
            },
            'release_projection': {
                'expected_revenue': 0,
                'confidence': 1.0,
                'time_to_sale': 3
            }
        }
    
    def _analyze_costs(self, vehicle_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze storage and processing costs"""
        tow_date = vehicle_data.get('tow_date')
        if tow_date:
            if isinstance(tow_date, str):
                from datetime import datetime
                tow_date = datetime.fromisoformat(tow_date.replace('Z', '+00:00'))
            storage_days = (datetime.now() - tow_date).days
        else:
            storage_days = 0
        
        daily_storage_cost = 15.0
        current_storage_cost = storage_days * daily_storage_cost
        
        return {
            'current_storage_cost': current_storage_cost,
            'daily_storage_cost': daily_storage_cost,
            'projected_costs': {
                'auction': current_storage_cost + (30 * daily_storage_cost),
                'scrap': current_storage_cost + (7 * daily_storage_cost),
                'release': current_storage_cost + (3 * daily_storage_cost)
            },
            'processing_costs': {
                'auction': 300,
                'scrap': 150,
                'release': 100
            }
        }
    
    def _analyze_market_conditions(self, vehicle_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze current market conditions"""
        # Simplified market analysis
        make = vehicle_data.get('make', '').lower()
        
        demand_scores = {
            'toyota': 0.8,
            'honda': 0.8,
            'ford': 0.6,
            'chevrolet': 0.6,
            'bmw': 0.7,
            'mercedes': 0.7
        }
        
        demand_score = demand_scores.get(make, 0.5)
        
        return {
            'demand_score': demand_score,
            'market_trend': 'stable',
            'seasonal_factor': self._calculate_seasonal_factor(),
            'competition_level': 'medium'
        }
    
    def _apply_business_rules(self, vehicle_data: Dict[str, Any], 
                            decision_type: DecisionType) -> List[Dict[str, Any]]:
        """Apply business rules to vehicle data"""
        applicable_rules = []
        
        for rule in self.business_rules:
            if not rule.active:
                continue
            
            try:
                # Simplified rule evaluation
                if self._evaluate_rule_condition(rule.condition, vehicle_data):
                    applicable_rules.append({
                        'rule_id': rule.rule_id,
                        'name': rule.name,
                        'action': rule.action,
                        'priority': rule.priority,
                        'exceptions': rule.exceptions
                    })
            except Exception as e:
                logger.warning(f"Error evaluating rule {rule.rule_id}: {str(e)}")
        
        return sorted(applicable_rules, key=lambda x: x['priority'])
    
    def _determine_best_disposition(self, decision_data: Dict[str, Any]) -> str:
        """Determine the best disposition based on analysis"""
        # Check business rules first
        rule_results = decision_data.get('rule_results', [])
        if rule_results:
            top_rule = rule_results[0]
            if top_rule['action'].startswith('disposition_'):
                return top_rule['action'].replace('disposition_', '')
        
        # Use financial analysis
        financial = decision_data.get('financial_analysis', {})
        cost = decision_data.get('cost_analysis', {})
        
        net_revenues = {}
        for disposition in ['auction', 'scrap', 'release']:
            revenue = financial.get(f'{disposition}_projection', {}).get('expected_revenue', 0)
            costs = cost.get('projected_costs', {}).get(disposition, 0)
            processing = cost.get('processing_costs', {}).get(disposition, 0)
            net_revenues[disposition] = revenue - costs - processing
        
        # Return disposition with highest net revenue
        best_disposition = max(net_revenues.keys(), key=lambda x: net_revenues[x])
        return best_disposition
    
    def _calculate_disposition_confidence(self, decision_data: Dict[str, Any]) -> DecisionConfidence:
        """Calculate confidence for disposition decision"""
        base_confidence = 0.7
        
        # Boost confidence if business rules apply
        if decision_data.get('rule_results'):
            base_confidence += 0.2
        
        # Boost confidence based on data quality
        vehicle_analysis = decision_data.get('vehicle_analysis', {})
        if vehicle_analysis.get('condition_score', 0) > 0.8:
            base_confidence += 0.1
        
        # Reduce confidence for edge cases
        financial = decision_data.get('financial_analysis', {})
        if all(proj.get('confidence', 0) < 0.6 for proj in financial.values()):
            base_confidence -= 0.2
        
        if base_confidence >= 0.9:
            return DecisionConfidence.VERY_HIGH
        elif base_confidence >= 0.75:
            return DecisionConfidence.HIGH
        elif base_confidence >= 0.6:
            return DecisionConfidence.MEDIUM
        elif base_confidence >= 0.4:
            return DecisionConfidence.LOW
        else:
            return DecisionConfidence.VERY_LOW
    
    def _generate_disposition_reasoning(self, decision_data: Dict[str, Any], 
                                      recommended_action: str) -> List[str]:
        """Generate reasoning for disposition decision"""
        reasoning = []
        
        # Add rule-based reasoning
        rule_results = decision_data.get('rule_results', [])
        if rule_results:
            top_rule = rule_results[0]
            reasoning.append(f"Business rule '{top_rule['name']}' recommends this action")
        
        # Add financial reasoning
        financial = decision_data.get('financial_analysis', {})
        cost = decision_data.get('cost_analysis', {})
        
        if recommended_action in financial and recommended_action in cost.get('projected_costs', {}):
            revenue = financial[f'{recommended_action}_projection']['expected_revenue']
            costs = cost['projected_costs'][recommended_action]
            net = revenue - costs
            reasoning.append(f"Expected net revenue: ${net:,.2f}")
        
        # Add market reasoning
        market = decision_data.get('market_analysis', {})
        demand_score = market.get('demand_score', 0.5)
        if demand_score > 0.7 and recommended_action == 'auction':
            reasoning.append("High market demand supports auction disposition")
        
        # Add vehicle condition reasoning
        vehicle = decision_data.get('vehicle_analysis', {})
        condition = vehicle.get('condition_score', 0.5)
        if condition < 0.3 and recommended_action == 'scrap':
            reasoning.append("Poor vehicle condition supports scrap disposition")
        
        return reasoning
    
    def _generate_disposition_alternatives(self, decision_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate alternative disposition options"""
        alternatives = []
        
        financial = decision_data.get('financial_analysis', {})
        cost = decision_data.get('cost_analysis', {})
        
        for disposition in ['auction', 'scrap', 'release']:
            if disposition in financial and disposition in cost.get('projected_costs', {}):
                revenue = financial[f'{disposition}_projection']['expected_revenue']
                costs = cost['projected_costs'][disposition]
                processing = cost.get('processing_costs', {}).get(disposition, 0)
                net = revenue - costs - processing
                
                alternatives.append({
                    'action': disposition,
                    'expected_net_revenue': net,
                    'confidence': financial[f'{disposition}_projection']['confidence'],
                    'timeline': financial[f'{disposition}_projection']['time_to_sale']
                })
        
        return sorted(alternatives, key=lambda x: x['expected_net_revenue'], reverse=True)
    
    def _assess_disposition_risks(self, vehicle_data: Dict[str, Any], 
                                recommended_action: str) -> Dict[str, float]:
        """Assess risks for disposition decision"""
        risks = {
            'market_volatility': 0.1,
            'storage_cost_escalation': 0.2,
            'documentation_issues': 0.1,
            'overall_risk': 0.2
        }
        
        # Increase risks based on vehicle characteristics
        market_value = vehicle_data.get('market_value', 0)
        if market_value > 20000:
            risks['market_volatility'] += 0.1
        
        # Increase risks for auction
        if recommended_action == 'auction':
            risks['market_volatility'] += 0.1
            risks['storage_cost_escalation'] += 0.1
        
        # Calculate overall risk
        risks['overall_risk'] = (
            risks['market_volatility'] * 0.3 +
            risks['storage_cost_escalation'] * 0.3 +
            risks['documentation_issues'] * 0.4
        )
        
        return risks
    
    def _requires_human_approval(self, decision_type: DecisionType, 
                               confidence: DecisionConfidence,
                               risk_assessment: Dict[str, float],
                               context: Dict[str, Any]) -> bool:
        """Determine if decision requires human approval"""
        # High-risk decisions always need approval
        if risk_assessment.get('overall_risk', 0) > 0.7:
            return True
        
        # Low confidence decisions need approval
        if confidence in [DecisionConfidence.VERY_LOW, DecisionConfidence.LOW]:
            return True
        
        # High-value vehicles need approval
        if context.get('market_value', 0) > 25000:
            return True
        
        # Legal holds always need approval
        if context.get('legal_hold'):
            return True
        
        return False
    
    def _create_error_decision(self, decision_type: DecisionType, error_msg: str) -> Decision:
        """Create error decision when processing fails"""
        return Decision(
            decision_id=f"error_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            decision_type=decision_type,
            recommended_action="manual_review_required",
            confidence=DecisionConfidence.VERY_LOW,
            reasoning=[f"AI processing error: {error_msg}"],
            supporting_data={},
            alternative_options=[],
            risk_assessment={'overall_risk': 1.0},
            requires_human_approval=True,
            timestamp=datetime.now()
        )
    
    def _calculate_age_factor(self, vehicle_data: Dict[str, Any]) -> float:
        """Calculate age factor (0 = new, 1 = very old)"""
        year = vehicle_data.get('year', datetime.now().year)
        current_year = datetime.now().year
        age = current_year - year
        return min(1.0, age / 20.0)  # Normalize to 20 years
    
    def _calculate_desirability_score(self, vehicle_data: Dict[str, Any]) -> float:
        """Calculate vehicle desirability score"""
        make = vehicle_data.get('make', '').lower()
        
        desirability_scores = {
            'toyota': 0.8,
            'honda': 0.8,
            'bmw': 0.7,
            'mercedes': 0.7,
            'audi': 0.7,
            'ford': 0.6,
            'chevrolet': 0.6,
            'nissan': 0.6
        }
        
        return desirability_scores.get(make, 0.5)
    
    def _estimate_maintenance_cost(self, vehicle_data: Dict[str, Any]) -> float:
        """Estimate maintenance cost for vehicle"""
        age_factor = self._calculate_age_factor(vehicle_data)
        condition_score = vehicle_data.get('condition_score', 0.5)
        
        base_cost = 500
        age_multiplier = 1 + (age_factor * 2)
        condition_multiplier = 2 - condition_score
        
        return base_cost * age_multiplier * condition_multiplier
    
    def _calculate_seasonal_factor(self) -> float:
        """Calculate seasonal market factor"""
        month = datetime.now().month
        
        # Spring and fall are typically better for car sales
        if month in [3, 4, 5, 9, 10]:
            return 1.1
        elif month in [12, 1, 2]:  # Winter
            return 0.9
        else:  # Summer
            return 1.0
    
    def _evaluate_rule_condition(self, condition: str, vehicle_data: Dict[str, Any]) -> bool:
        """Evaluate business rule condition (simplified)"""
        try:
            # Replace variable names with actual values
            condition_code = condition
            
            # Simple substitutions for demonstration
            market_value = vehicle_data.get('market_value', 0)
            condition_score = vehicle_data.get('condition_score', 0.5)
            legal_hold = vehicle_data.get('legal_hold', False)
            
            condition_code = condition_code.replace('market_value', str(market_value))
            condition_code = condition_code.replace('condition_score', str(condition_score))
            condition_code = condition_code.replace('legal_hold', str(legal_hold))
            condition_code = condition_code.replace('AND', ' and ')
            condition_code = condition_code.replace('OR', ' or ')
            
            # Evaluate the condition safely (in production, use a proper expression parser)
            return eval(condition_code)
            
        except Exception:
            return False
    
    def _analyze_workflow_state(self, vehicle_data: Dict[str, Any], current_stage: str) -> Dict[str, Any]:
        """Analyze current workflow state"""
        return {
            'current_stage': current_stage,
            'stage_duration': vehicle_data.get('stage_duration', 0),
            'completion_percentage': vehicle_data.get('completion_percentage', 0),
            'blocking_issues': vehicle_data.get('blocking_issues', [])
        }
    
    def _analyze_stage_completion(self, vehicle_data: Dict[str, Any], current_stage: str) -> Dict[str, Any]:
        """Analyze stage completion criteria"""
        return {
            'requirements_met': vehicle_data.get('requirements_met', False),
            'documentation_complete': vehicle_data.get('documentation_complete', False),
            'approval_received': vehicle_data.get('approval_received', False)
        }
    
    def _analyze_next_stage_requirements(self, vehicle_data: Dict[str, Any], current_stage: str) -> Dict[str, Any]:
        """Analyze next stage requirements"""
        stage_flow = {
            'intake': 'processing',
            'processing': 'inspection',
            'inspection': 'disposition',
            'disposition': 'completion'
        }
        
        next_stage = stage_flow.get(current_stage, 'completion')
        
        return {
            'next_stage': next_stage,
            'prerequisites_met': True,  # Simplified
            'resource_availability': True
        }
    
    def _analyze_resource_availability(self, stage: str) -> Dict[str, Any]:
        """Analyze resource availability for stage"""
        return {
            'staff_available': True,
            'equipment_available': True,
            'capacity_utilization': 0.7
        }
    
    def _determine_next_workflow_action(self, decision_data: Dict[str, Any], current_stage: str) -> str:
        """Determine next workflow action"""
        completion_analysis = decision_data.get('completion_analysis', {})
        next_stage_analysis = decision_data.get('next_stage_analysis', {})
        
        if completion_analysis.get('requirements_met', False):
            return f"advance_to_{next_stage_analysis.get('next_stage', 'next_stage')}"
        else:
            return f"continue_{current_stage}"
    
    def _calculate_workflow_confidence(self, decision_data: Dict[str, Any]) -> DecisionConfidence:
        """Calculate confidence for workflow decision"""
        completion_analysis = decision_data.get('completion_analysis', {})
        
        if completion_analysis.get('requirements_met', False):
            return DecisionConfidence.HIGH
        else:
            return DecisionConfidence.MEDIUM
    
    def _generate_workflow_reasoning(self, decision_data: Dict[str, Any], recommended_action: str) -> List[str]:
        """Generate reasoning for workflow decision"""
        reasoning = []
        
        completion_analysis = decision_data.get('completion_analysis', {})
        
        if 'advance_to' in recommended_action:
            reasoning.append("All stage requirements have been met")
            reasoning.append("Next stage prerequisites are satisfied")
        else:
            reasoning.append("Stage requirements still pending")
            if not completion_analysis.get('documentation_complete', False):
                reasoning.append("Documentation incomplete")
        
        return reasoning
    
    def _generate_workflow_alternatives(self, decision_data: Dict[str, Any], current_stage: str) -> List[Dict[str, Any]]:
        """Generate workflow alternatives"""
        return [
            {
                'action': f'continue_{current_stage}',
                'description': f'Continue current {current_stage} stage',
                'estimated_time': '2-5 days'
            },
            {
                'action': 'escalate_for_review',
                'description': 'Escalate for supervisory review',
                'estimated_time': '1-2 days'
            }
        ]
    
    def _assess_workflow_risks(self, vehicle_data: Dict[str, Any], recommended_action: str) -> Dict[str, float]:
        """Assess workflow risks"""
        return {
            'processing_delays': 0.2,
            'compliance_issues': 0.1,
            'resource_constraints': 0.15,
            'overall_risk': 0.2
        }
    
    def _calculate_urgency_factors(self, vehicle_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate urgency factors for priority assignment"""
        return {
            'storage_duration': vehicle_data.get('storage_days', 0),
            'storage_cost_rate': 15.0,
            'legal_deadlines': vehicle_data.get('legal_deadlines', []),
            'market_value': vehicle_data.get('market_value', 0)
        }
    
    def _assess_financial_impact(self, vehicle_data: Dict[str, Any]) -> Dict[str, Any]:
        """Assess financial impact for priority assignment"""
        market_value = vehicle_data.get('market_value', 0)
        
        return {
            'potential_revenue': market_value * 0.8,
            'storage_cost_per_day': 15.0,
            'processing_cost': 200,
            'opportunity_cost': market_value * 0.01  # 1% per month
        }
    
    def _analyze_compliance_requirements(self, vehicle_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze compliance requirements"""
        return {
            'legal_hold': vehicle_data.get('legal_hold', False),
            'investigation_pending': vehicle_data.get('investigation_pending', False),
            'documentation_required': vehicle_data.get('documentation_required', []),
            'deadline_approaching': False  # Simplified
        }
    
    def _evaluate_resource_constraints(self) -> Dict[str, Any]:
        """Evaluate current resource constraints"""
        return {
            'staff_capacity': 0.8,
            'equipment_availability': 0.9,
            'storage_capacity': 0.7,
            'processing_backlog': 25
        }
    
    def _determine_priority_level(self, decision_data: Dict[str, Any]) -> str:
        """Determine priority level"""
        urgency = decision_data.get('urgency_analysis', {})
        financial = decision_data.get('financial_impact', {})
        compliance = decision_data.get('compliance_analysis', {})
        
        # Critical priority conditions
        if compliance.get('legal_hold') or compliance.get('investigation_pending'):
            return 'critical'
        
        # High priority conditions
        if financial.get('potential_revenue', 0) > 15000:
            return 'high'
        
        if urgency.get('storage_duration', 0) > 60:
            return 'high'
        
        # Medium priority (default)
        return 'medium'
    
    def _calculate_priority_confidence(self, decision_data: Dict[str, Any]) -> DecisionConfidence:
        """Calculate confidence for priority assignment"""
        # High confidence for clear priority indicators
        compliance = decision_data.get('compliance_analysis', {})
        
        if compliance.get('legal_hold') or compliance.get('investigation_pending'):
            return DecisionConfidence.VERY_HIGH
        
        return DecisionConfidence.HIGH
    
    def _generate_priority_reasoning(self, decision_data: Dict[str, Any], recommended_action: str) -> List[str]:
        """Generate reasoning for priority assignment"""
        reasoning = []
        
        compliance = decision_data.get('compliance_analysis', {})
        financial = decision_data.get('financial_impact', {})
        urgency = decision_data.get('urgency_analysis', {})
        
        if compliance.get('legal_hold'):
            reasoning.append("Legal hold requires immediate attention")
        
        if financial.get('potential_revenue', 0) > 15000:
            reasoning.append("High-value vehicle with significant revenue potential")
        
        if urgency.get('storage_duration', 0) > 60:
            reasoning.append("Extended storage period increasing costs")
        
        return reasoning
    
    def _generate_priority_alternatives(self, decision_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate priority alternatives"""
        return [
            {
                'action': 'critical',
                'description': 'Critical priority - immediate processing',
                'justification': 'Legal or compliance requirements'
            },
            {
                'action': 'high',
                'description': 'High priority - expedited processing',
                'justification': 'High value or time-sensitive'
            },
            {
                'action': 'medium',
                'description': 'Medium priority - standard processing',
                'justification': 'Normal processing queue'
            }
        ]
    
    def _assess_priority_risks(self, vehicle_data: Dict[str, Any], recommended_action: str) -> Dict[str, float]:
        """Assess risks for priority assignment"""
        return {
            'resource_overallocation': 0.2,
            'processing_delays': 0.1,
            'cost_escalation': 0.15,
            'overall_risk': 0.15
        }
    
    def _analyze_issue_severity(self, issue_context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze issue severity for escalation"""
        return {
            'severity_level': issue_context.get('severity', 'medium'),
            'impact_scope': issue_context.get('impact_scope', 'single_vehicle'),
            'financial_impact': issue_context.get('financial_impact', 0),
            'compliance_impact': issue_context.get('compliance_impact', False)
        }
    
    def _analyze_time_criticality(self, vehicle_data: Dict[str, Any], issue_context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze time criticality for escalation"""
        return {
            'deadline_proximity': issue_context.get('deadline_proximity', 'normal'),
            'urgency_level': issue_context.get('urgency_level', 'medium'),
            'time_sensitive': issue_context.get('time_sensitive', False)
        }
    
    def _evaluate_escalation_resource_needs(self, issue_context: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate resource needs for escalation"""
        return {
            'requires_supervisor': issue_context.get('requires_supervisor', False),
            'requires_specialist': issue_context.get('requires_specialist', False),
            'requires_external_approval': issue_context.get('requires_external_approval', False)
        }
    
    def _check_escalation_triggers(self, vehicle_data: Dict[str, Any], issue_context: Dict[str, Any]) -> Dict[str, Any]:
        """Check escalation triggers"""
        triggers_fired = []
        
        for rule in self.escalation_rules:
            if self._evaluate_rule_condition(rule['condition'], {**vehicle_data, **issue_context}):
                triggers_fired.append(rule)
        
        return {
            'triggers_fired': triggers_fired,
            'highest_urgency': max([t['urgency'] for t in triggers_fired], default='low')
        }
    
    def _determine_escalation_action(self, decision_data: Dict[str, Any]) -> str:
        """Determine escalation action"""
        trigger_analysis = decision_data.get('trigger_analysis', {})
        severity_analysis = decision_data.get('severity_analysis', {})
        
        triggers = trigger_analysis.get('triggers_fired', [])
        if triggers:
            return f"escalate_to_{triggers[0]['escalation_level']}"
        
        severity = severity_analysis.get('severity_level', 'medium')
        if severity == 'critical':
            return 'escalate_to_manager'
        elif severity == 'high':
            return 'escalate_to_supervisor'
        else:
            return 'no_escalation_needed'
    
    def _calculate_escalation_confidence(self, decision_data: Dict[str, Any]) -> DecisionConfidence:
        """Calculate confidence for escalation decision"""
        trigger_analysis = decision_data.get('trigger_analysis', {})
        
        if trigger_analysis.get('triggers_fired'):
            return DecisionConfidence.HIGH
        else:
            return DecisionConfidence.MEDIUM
    
    def _generate_escalation_reasoning(self, decision_data: Dict[str, Any], recommended_action: str) -> List[str]:
        """Generate reasoning for escalation decision"""
        reasoning = []
        
        trigger_analysis = decision_data.get('trigger_analysis', {})
        severity_analysis = decision_data.get('severity_analysis', {})
        
        triggers = trigger_analysis.get('triggers_fired', [])
        if triggers:
            reasoning.append(f"Escalation trigger fired: {triggers[0]['trigger']}")
        
        if severity_analysis.get('compliance_impact'):
            reasoning.append("Compliance implications require higher-level review")
        
        if severity_analysis.get('financial_impact', 0) > 10000:
            reasoning.append("Significant financial impact warrants escalation")
        
        return reasoning
    
    def _generate_escalation_alternatives(self, decision_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate escalation alternatives"""
        return [
            {
                'action': 'escalate_to_supervisor',
                'description': 'Escalate to immediate supervisor',
                'timeline': '2-4 hours'
            },
            {
                'action': 'escalate_to_manager',
                'description': 'Escalate to department manager',
                'timeline': '4-8 hours'
            },
            {
                'action': 'escalate_to_legal',
                'description': 'Escalate to legal team',
                'timeline': '1-2 days'
            }
        ]
    
    def _assess_escalation_risks(self, vehicle_data: Dict[str, Any], recommended_action: str) -> Dict[str, float]:
        """Assess risks for escalation decision"""
        return {
            'delay_risk': 0.3,
            'cost_escalation': 0.2,
            'relationship_impact': 0.1,
            'overall_risk': 0.2
        }
    
    def _analyze_resource_capacity(self, available_resources: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze resource capacity"""
        return {
            'staff_capacity': available_resources.get('staff_hours', 0),
            'equipment_availability': available_resources.get('equipment_units', 0),
            'budget_available': available_resources.get('budget', 0),
            'utilization_rate': 0.75  # Current utilization
        }
    
    def _prioritize_tasks(self, pending_tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Prioritize tasks for resource allocation"""
        # Sort by priority score (higher is better)
        for task in pending_tasks:
            task['priority_score'] = self._calculate_task_priority_score(task)
        
        return sorted(pending_tasks, key=lambda x: x['priority_score'], reverse=True)
    
    def _calculate_task_priority_score(self, task: Dict[str, Any]) -> float:
        """Calculate priority score for a task"""
        base_score = 0.5
        
        # Financial impact
        financial_impact = task.get('financial_impact', 0)
        base_score += min(0.3, financial_impact / 50000)
        
        # Urgency
        urgency = task.get('urgency', 'medium')
        urgency_scores = {'low': 0.1, 'medium': 0.2, 'high': 0.3, 'critical': 0.4}
        base_score += urgency_scores.get(urgency, 0.2)
        
        # Deadline proximity
        deadline = task.get('deadline_days', 30)
        if deadline <= 7:
            base_score += 0.2
        elif deadline <= 14:
            base_score += 0.1
        
        return base_score
    
    def _calculate_optimal_allocation(self, available_resources: Dict[str, Any], 
                                    prioritized_tasks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate optimal resource allocation"""
        allocation = {
            'task_assignments': [],
            'resource_utilization': {},
            'unassigned_tasks': []
        }
        
        remaining_capacity = available_resources.get('staff_hours', 0)
        
        for task in prioritized_tasks:
            required_hours = task.get('estimated_hours', 8)
            
            if remaining_capacity >= required_hours:
                allocation['task_assignments'].append({
                    'task_id': task.get('id'),
                    'assigned_hours': required_hours,
                    'priority_score': task.get('priority_score', 0)
                })
                remaining_capacity -= required_hours
            else:
                allocation['unassigned_tasks'].append(task.get('id'))
        
        allocation['resource_utilization'] = {
            'hours_assigned': available_resources.get('staff_hours', 0) - remaining_capacity,
            'hours_available': available_resources.get('staff_hours', 0),
            'utilization_percentage': (1 - remaining_capacity / max(available_resources.get('staff_hours', 1), 1)) * 100
        }
        
        return allocation
    
    def _analyze_allocation_constraints(self, available_resources: Dict[str, Any], 
                                      pending_tasks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze allocation constraints"""
        return {
            'capacity_constraints': available_resources.get('staff_hours', 0) < sum(t.get('estimated_hours', 8) for t in pending_tasks),
            'skill_constraints': False,  # Simplified
            'equipment_constraints': False,  # Simplified
            'budget_constraints': False  # Simplified
        }
    
    def _determine_resource_allocation(self, decision_data: Dict[str, Any]) -> str:
        """Determine resource allocation strategy"""
        allocation_analysis = decision_data.get('allocation_analysis', {})
        constraint_analysis = decision_data.get('constraint_analysis', {})
        
        if constraint_analysis.get('capacity_constraints'):
            return 'prioritize_high_value_tasks'
        else:
            return 'process_all_tasks'
    
    def _calculate_allocation_confidence(self, decision_data: Dict[str, Any]) -> DecisionConfidence:
        """Calculate confidence for allocation decision"""
        constraint_analysis = decision_data.get('constraint_analysis', {})
        
        if any(constraint_analysis.values()):
            return DecisionConfidence.MEDIUM
        else:
            return DecisionConfidence.HIGH
    
    def _generate_allocation_reasoning(self, decision_data: Dict[str, Any], recommended_action: str) -> List[str]:
        """Generate reasoning for allocation decision"""
        reasoning = []
        
        allocation_analysis = decision_data.get('allocation_analysis', {})
        utilization = allocation_analysis.get('resource_utilization', {})
        
        reasoning.append(f"Resource utilization: {utilization.get('utilization_percentage', 0):.1f}%")
        
        if 'prioritize' in recommended_action:
            reasoning.append("Resource constraints require task prioritization")
        
        return reasoning
    
    def _generate_allocation_alternatives(self, decision_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate allocation alternatives"""
        return [
            {
                'action': 'process_all_tasks',
                'description': 'Process all tasks with available resources',
                'resource_utilization': '100%'
            },
            {
                'action': 'prioritize_high_value_tasks',
                'description': 'Focus on highest priority tasks first',
                'resource_utilization': '80%'
            },
            {
                'action': 'request_additional_resources',
                'description': 'Request additional staff or overtime',
                'resource_utilization': '120%'
            }
        ]
    
    def _assess_allocation_risks(self, recommended_action: str) -> Dict[str, float]:
        """Assess risks for allocation decision"""
        return {
            'overcommitment_risk': 0.2,
            'quality_degradation': 0.1,
            'staff_burnout': 0.15,
            'overall_risk': 0.15
        }
    
    def _generate_decision_tree(self, decision: Decision) -> Dict[str, Any]:
        """Generate decision tree explanation"""
        return {
            'root_question': f"What is the best {decision.decision_type.value}?",
            'decision_path': [
                {
                    'step': 1,
                    'question': "Are business rules applicable?",
                    'answer': "Yes" if decision.supporting_data.get('rule_results') else "No",
                    'impact': "High" if decision.supporting_data.get('rule_results') else "Low"
                },
                {
                    'step': 2,
                    'question': "What is the financial impact?",
                    'answer': "Analyzed revenue vs. costs",
                    'impact': "High"
                },
                {
                    'step': 3,
                    'question': "What are the risk factors?",
                    'answer': f"Overall risk: {decision.risk_assessment.get('overall_risk', 0):.2f}",
                    'impact': "Medium"
                }
            ],
            'final_decision': decision.recommended_action,
            'confidence_factors': decision.reasoning
        }
    
    def _generate_what_if_scenarios(self, decision: Decision) -> List[Dict[str, Any]]:
        """Generate what-if scenarios for decision"""
        scenarios = []
        
        if decision.decision_type == DecisionType.DISPOSITION:
            scenarios = [
                {
                    'scenario': 'Market value 20% higher',
                    'impact': 'Would strengthen auction recommendation',
                    'confidence_change': '+10%'
                },
                {
                    'scenario': 'Storage costs doubled',
                    'impact': 'Would favor faster disposition',
                    'confidence_change': '+15%'
                },
                {
                    'scenario': 'Legal hold applied',
                    'impact': 'Would override all other factors',
                    'confidence_change': '+50%'
                }
            ]
        
        return scenarios
