"""
AI and ML Module for iTow Vehicle Management System

This module provides artificial intelligence and machine learning capabilities
for predictive analytics, intelligent automation, and decision support.

Components:
- Predictive Engine: ML models for disposition and timeline prediction
- NLP Engine: Natural language processing for queries and commands
- Document AI: Intelligent document processing and OCR
- Decision Engine: AI-powered decision making and recommendations
"""

from .predictive import PredictiveEngine
from .nlp import NLPEngine
from .document_ai import DocumentAI
from .decision_engine import DecisionEngine

__all__ = [
    'PredictiveEngine',
    'NLPEngine', 
    'DocumentAI',
    'DecisionEngine'
]
