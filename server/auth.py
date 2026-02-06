"""
Authentication Routes using Flask-JWT-Extended
Handles user registration, login, and token management
"""
from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    jwt_required, get_jwt_identity, create_access_token,
    create_refresh_token, get_jwt, jwt_required
)
from models import User, UserRole, db

# Create blueprint for auth routes
auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')


@auth_bp.route('/register', methods=['POST'])
def register():
    """
    Register a new user (Employer or Job Seeker)
    
    Expected JSON payload:
    {
        "email": "user@example.com",
        "password": "securepassword123",
        "role": "employer" | "job_seeker",
        "full_name": "John Doe",  // optional
        "company_name": "Company Inc"  // required for employers
    }
    """
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data:
            return jsonify({
                'error': 'No data provided',
                'message': 'Request body must contain JSON data'
            }), 400
        
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        role = data.get('role', '').lower()
        full_name = data.get('full_name', '').strip()
        company_name = data.get('company_name', '').strip()
        phone = data.get('phone', '').strip()
        
        # Validation checks
        errors = []
        
        if not email:
            errors.append('Email is required')
        elif '@' not in email or '.' not in email:
            errors.append('Invalid email format')
        
        if not password:
            errors.append('Password is required')
        elif len(password) < 8:
            errors.append('Password must be at least 8 characters long')
        
        if not role:
            errors.append('Role is required')
        elif role not in [UserRole.EMPLOYER, UserRole.JOB_SEEKER]:
            errors.append(f"Role must be either '{UserRole.EMPLOYER}' or '{UserRole.JOB_SEEKER}'")
        
        if role == UserRole.EMPLOYER and not company_name:
            errors.append('Company name is required for employers')
        
        if errors:
            return jsonify({
                'error': 'Validation failed',
                'messages': errors
            }), 400
        
        # Check if email already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            return jsonify({
                'error': 'Email already registered',
                'message': 'An account with this email already exists'
            }), 409
        
        # Create new user
        user = User(
            email=email,
            role=role,
            full_name=full_name if full_name else None,
            company_name=company_name if company_name else None,
            phone=phone if phone else None
        )
        user.set_password(password)
        
        # Save to database
        db.session.add(user)
        db.session.commit()
        
        # Generate tokens
        access_token = create_access_token(identity=user.id)
        refresh_token = create_refresh_token(identity=user.id)
        
        return jsonify({
            'message': 'User registered successfully',
            'user': user.to_dict(),
            'access_token': access_token,
            'refresh_token': refresh_token,
            'token_type': 'Bearer'
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'error': 'Registration failed',
            'message': str(e)
        }), 500


@auth_bp.route('/login', methods=['POST'])
def login():
    """
    Authenticate user and return JWT tokens
    
    Expected JSON payload:
    {
        "email": "user@example.com",
        "password": "securepassword123"
    }
    """
    try:
        data = request.get_json()
        
        # Validate input
        if not data:
            return jsonify({
                'error': 'No data provided',
                'message': 'Request body must contain JSON data'
            }), 400
        
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        
        if not email or not password:
            return jsonify({
                'error': 'Missing credentials',
                'message': 'Email and password are required'
            }), 400
        
        # Find user by email
        user = User.query.filter_by(email=email).first()
        
        if not user:
            return jsonify({
                'error': 'Authentication failed',
                'message': 'Invalid email or password'
            }), 401
        
        # Check password
        if not user.check_password(password):
            return jsonify({
                'error': 'Authentication failed',
                'message': 'Invalid email or password'
            }), 401
        
        # Generate tokens
        access_token = create_access_token(identity=user.id)
        refresh_token = create_refresh_token(identity=user.id)
        
        return jsonify({
            'message': 'Login successful',
            'user': user.to_dict(),
            'access_token': access_token,
            'refresh_token': refresh_token,
            'token_type': 'Bearer'
        }), 200
        
    except Exception as e:
        return jsonify({
            'error': 'Login failed',
            'message': str(e)
        }), 500


@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user():
    """
    Get current authenticated user's information
    
    Requires: Valid JWT access token in Authorization header
    """
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({
                'error': 'User not found',
                'message': 'The user associated with this token no longer exists'
            }), 404
        
        return jsonify({
            'user': user.to_dict()
        }), 200
        
    except Exception as e:
        return jsonify({
            'error': 'Failed to get user info',
            'message': str(e)
        }), 500


@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh_token():
    """
    Refresh access token using refresh token
    
    Requires: Valid JWT refresh token in Authorization header
    """
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({
                'error': 'User not found',
                'message': 'The user associated with this token no longer exists'
            }), 404
        
        # Generate new access token
        access_token = create_access_token(identity=user.id)
        
        return jsonify({
            'message': 'Token refreshed successfully',
            'access_token': access_token,
            'token_type': 'Bearer'
        }), 200
        
    except Exception as e:
        return jsonify({
            'error': 'Token refresh failed',
            'message': str(e)
        }), 500


@auth_bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    """
    Logout user (client-side token removal, server-side blacklist can be implemented)
    
    Requires: Valid JWT access token
    """
    try:
        # In production, you would blacklist the token here
        # For now, we'll just return a success message
        return jsonify({
            'message': 'Logged out successfully',
            'note': 'Please remove the token from client storage'
        }), 200
        
    except Exception as e:
        return jsonify({
            'error': 'Logout failed',
            'message': str(e)
        }), 500


@auth_bp.route('/change-password', methods=['POST'])
@jwt_required()
def change_password():
    """
    Change user password
    
    Expected JSON payload:
    {
        "current_password": "oldpassword123",
        "new_password": "newpassword456"
    }
    """
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({
                'error': 'User not found',
                'message': 'The user associated with this token no longer exists'
            }), 404
        
        data = request.get_json()
        
        if not data:
            return jsonify({
                'error': 'No data provided',
                'message': 'Request body must contain JSON data'
            }), 400
        
        current_password = data.get('current_password', '')
        new_password = data.get('new_password', '')
        
        if not current_password or not new_password:
            return jsonify({
                'error': 'Missing credentials',
                'message': 'Current password and new password are required'
            }), 400
        
        # Verify current password
        if not user.check_password(current_password):
            return jsonify({
                'error': 'Invalid password',
                'message': 'Current password is incorrect'
            }), 401
        
        # Validate new password
        if len(new_password) < 8:
            return jsonify({
                'error': 'Invalid password',
                'message': 'New password must be at least 8 characters long'
            }), 400
        
        # Update password
        user.set_password(new_password)
        db.session.commit()
        
        return jsonify({
            'message': 'Password changed successfully'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'error': 'Password change failed',
            'message': str(e)
        }), 500


# Additional utility endpoint for role verification
@auth_bp.route('/verify-role/<role>', methods=['GET'])
@jwt_required()
def verify_role(role):
    """
    Verify if current user has a specific role
    
    URL parameter: role (employer or job_seeker)
    """
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({
            'error': 'User not found',
            'message': 'The user associated with this token no longer exists'
        }), 404
    
    has_role = user.role == role.lower()
    
    return jsonify({
        'has_role': has_role,
        'user_role': user.role,
        'requested_role': role
    }), 200

