"""
Role-Based Access Control (RBAC) Decorators
Ensures proper access control based on user roles
"""
from functools import wraps
from flask import jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import User, UserRole


def role_required(allowed_roles):
    """
    Decorator to require specific roles for access
    
    Args:
        allowed_roles: List of roles that are allowed to access the route
                       e.g., ['employer'] or ['job_seeker']
    
    Usage:
        @role_required(['employer'])
        @jwt_required()
        def post_job():
            ...
    
        @role_required(['employer', 'job_seeker'])
        @jwt_required()
        def some_view():
            ...
    """
    def decorator(fn):
        @wraps(fn)
        @jwt_required()
        def wrapper(*args, **kwargs):
            # Get current user from JWT token
            user_id = get_jwt_identity()
            user = User.query.get(user_id)
            
            # Check if user exists
            if not user:
                return jsonify({
                    'error': 'User not found',
                    'message': 'The user associated with this token no longer exists'
                }), 401
            
            # Check if user has required role
            if user.role not in allowed_roles:
                return jsonify({
                    'error': 'Access denied',
                    'message': f'This action requires one of the following roles: {", ".join(allowed_roles)}',
                    'required_roles': allowed_roles,
                    'your_role': user.role
                }), 403
            
            return fn(*args, **kwargs)
        return wrapper
    return decorator


def employer_required(fn):
    """
    Decorator to require 'employer' role for access
    
    Usage:
        @employer_required
        @jwt_required()
        def post_job():
            ...
    """
    @wraps(fn)
    @jwt_required()
    def wrapper(*args, **kwargs):
        # Get current user from JWT token
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        # Check if user exists
        if not user:
            return jsonify({
                'error': 'User not found',
                'message': 'The user associated with this token no longer exists'
            }), 401
        
        # Check if user is an employer
        if user.role != UserRole.EMPLOYER:
            return jsonify({
                'error': 'Access denied',
                'message': 'Only employers can access this resource',
                'your_role': user.role
            }), 403
        
        return fn(*args, **kwargs)
    return wrapper


def job_seeker_required(fn):
    """
    Decorator to require 'job_seeker' role for access
    
    Usage:
        @job_seeker_required
        @jwt_required()
        def apply_to_job():
            ...
    """
    @wraps(fn)
    @jwt_required()
    def wrapper(*args, **kwargs):
        # Get current user from JWT token
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        # Check if user exists
        if not user:
            return jsonify({
                'error': 'User not found',
                'message': 'The user associated with this token no longer exists'
            }), 401
        
        # Check if user is a job seeker
        if user.role != UserRole.JOB_SEEKER:
            return jsonify({
                'error': 'Access denied',
                'message': 'Only job seekers can access this resource',
                'your_role': user.role
            }), 403
        
        return fn(*args, **kwargs)
    return wrapper


def resource_owner_or_employer_required(resource_model, resource_id_param='id'):
    """
    Decorator to require resource ownership or employer role
    
    Args:
        resource_model: The SQLAlchemy model of the resource
        resource_id_param: The name of the URL parameter containing the resource ID
    
    Usage:
        @resource_owner_or_employer_required(Job, 'job_id')
        @jwt_required()
        def update_job(job_id):
            ...
    """
    def decorator(fn):
        @wraps(fn)
        @jwt_required()
        def wrapper(*args, **kwargs):
            # Get current user from JWT token
            user_id = get_jwt_identity()
            user = User.query.get(user_id)
            
            # Check if user exists
            if not user:
                return jsonify({
                    'error': 'User not found',
                    'message': 'The user associated with this token no longer exists'
                }), 401
            
            # Get resource ID from kwargs
            resource_id = kwargs.get(resource_id_param)
            if not resource_id:
                return jsonify({
                    'error': 'Resource ID not found',
                    'message': f'Could not find {resource_id_param} in request parameters'
                }), 400
            
            # Get the resource
            resource = resource_model.query.get(resource_id)
            if not resource:
                return jsonify({
                    'error': 'Resource not found',
                    'message': f'{resource_model.__name__} with ID {resource_id} not found'
                }), 404
            
            # Check if user is employer (for jobs) or resource owner
            if user.role == UserRole.EMPLOYER:
                # Employers can access their own resources
                if hasattr(resource, 'employer_id') and resource.employer_id == user.id:
                    return fn(*args, **kwargs)
                elif hasattr(resource, 'user_id') and resource.user_id == user.id:
                    return fn(*args, **kwargs)
            
            # For applications, check if user is the applicant
            if hasattr(resource, 'applicant_id') and resource.applicant_id == user.id:
                return fn(*args, **kwargs)
            
            # Check ownership for other resources
            if hasattr(resource, 'user_id') and resource.user_id == user.id:
                return fn(*args, **kwargs)
            
            return jsonify({
                'error': 'Access denied',
                'message': 'You do not have permission to access or modify this resource'
            }), 403
        
        return wrapper
    return decorator

