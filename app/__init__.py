"""
iTow Vehicle Management System - Application Package
Enhanced architecture with modular design
"""

__version__ = "2.0.0"
__author__ = "iTow VMS Team"

# Package imports for easier access
from .factory import create_app

__all__ = ['create_app']
