"""
Routes package initialization
"""
from routes.jobs import jobs_bp
from routes.applications import applications_bp

__all__ = ['jobs_bp', 'applications_bp']

