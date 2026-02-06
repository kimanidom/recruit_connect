"""
Application Routes - Job Application Management
Job Seekers can apply to jobs, Employers can manage applications
"""
from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import Job, User, UserRole, Application, ApplicationStatus, db
from decorators import job_seeker_required, employer_required, resource_owner_or_employer_required

# Create blueprint for application routes
applications_bp = Blueprint('applications', __name__, url_prefix='/api/applications')


@applications_bp.route('', methods=['POST'])
@job_seeker_required
def create_application():
    """
    Apply to a job (Job Seeker only)
    
    Expected JSON payload:
    {
        "job_id": 123,
        "cover_letter": "My cover letter...",
        "resume_url": "https://example.com/resume.pdf",  // optional
        "additional_info": "Any additional information..."  // optional
    }
    """
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        data = request.get_json()
        
        if not data:
            return jsonify({
                'error': 'No data provided',
                'message': 'Request body must contain JSON data'
            }), 400
        
        job_id = data.get('job_id')
        
        if not job_id:
            return jsonify({
                'error': 'Missing job ID',
                'message': 'Job ID is required'
            }), 400
        
        # Get the job
        job = Job.query.get(job_id)
        
        if not job:
            return jsonify({
                'error': 'Job not found',
                'message': f'No job found with ID {job_id}'
            }), 404
        
        if not job.is_active:
            return jsonify({
                'error': 'Job not available',
                'message': 'This job posting is no longer active'
            }), 400
        
        # Check if user already applied
        existing_application = Application.query.filter_by(
            job_id=job_id, 
            applicant_id=user.id
        ).first()
        
        if existing_application:
            return jsonify({
                'error': 'Already applied',
                'message': 'You have already applied to this job',
                'application_id': existing_application.id,
                'status': existing_application.status
            }), 409
        
        # Create application
        application = Application(
            job_id=job_id,
            applicant_id=user.id,
            cover_letter=data.get('cover_letter', '').strip(),
            resume_url=data.get('resume_url', '').strip(),
            additional_info=data.get('additional_info', '').strip(),
            status=ApplicationStatus.PENDING
        )
        
        db.session.add(application)
        db.session.commit()
        
        return jsonify({
            'message': 'Application submitted successfully',
            'application': application.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'error': 'Failed to submit application',
            'message': str(e)
        }), 500


@applications_bp.route('', methods=['GET'])
@jwt_required()
def get_my_applications():
    """
    Get current user's applications
    
    Query Parameters:
        - page: Page number (default: 1)
        - per_page: Items per page (default: 10)
        - status: Filter by application status
        - job_id: Filter by specific job
    
    Returns:
        Job Seekers see their own applications
        Employers see applications to their jobs
    """
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({
                'error': 'User not found',
                'message': 'The user associated with this token no longer exists'
            }), 404
        
        # Get query parameters
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        status = request.args.get('status', '').strip().lower()
        job_id = request.args.get('job_id', None, type=int)
        
        # Base query based on user role
        if user.role == UserRole.JOB_SEEKER:
            query = Application.query.filter_by(applicant_id=user.id)
        elif user.role == UserRole.EMPLOYER:
            # Employers see applications to their jobs
            query = Application.query.join(Job).filter(Job.employer_id == user.id)
        else:
            return jsonify({
                'error': 'Invalid role',
                'message': 'User has an invalid role'
            }), 400
        
        # Apply filters
        if status and status in [ApplicationStatus.PENDING, ApplicationStatus.ACCEPTED, 
                                  ApplicationStatus.REJECTED, ApplicationStatus.WITHDRAWN]:
            query = query.filter(Application.status == status)
        
        if job_id:
            query = query.filter(Application.job_id == job_id)
        
        # Order by creation date (newest first)
        query = query.order_by(Application.created_at.desc())
        
        # Paginate
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        applications = pagination.items
        
        return jsonify({
            'applications': [app.to_applicant_view() for app in applications],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total_items': pagination.total,
                'total_pages': pagination.pages,
                'has_next': pagination.has_next,
                'has_prev': pagination.has_prev
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            'error': 'Failed to fetch applications',
            'message': str(e)
        }), 500


@applications_bp.route('/<int:application_id>', methods=['GET'])
@jwt_required()
def get_application(application_id):
    """
    Get a specific application by ID
    
    URL Parameter:
        application_id: The ID of the application
    
    Returns:
        Job Seekers can only see their own applications
        Employers can see applications to their jobs
    """
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({
                'error': 'User not found',
                'message': 'The user associated with this token no longer exists'
            }), 404
        
        application = Application.query.get(application_id)
        
        if not application:
            return jsonify({
                'error': 'Application not found',
                'message': f'No application found with ID {application_id}'
            }), 404
        
        # Check access rights
        if user.role == UserRole.JOB_SEEKER:
            if application.applicant_id != user.id:
                return jsonify({
                    'error': 'Access denied',
                    'message': 'You can only view your own applications'
                }), 403
        elif user.role == UserRole.EMPLOYER:
            # Check if job belongs to employer
            if application.job.employer_id != user.id:
                return jsonify({
                    'error': 'Access denied',
                    'message': 'You can only view applications to your jobs'
                }), 403
        else:
            return jsonify({
                'error': 'Invalid role',
                'message': 'User has an invalid role'
            }), 400
        
        return jsonify({
            'application': application.to_dict()
        }), 200
        
    except Exception as e:
        return jsonify({
            'error': 'Failed to fetch application',
            'message': str(e)
        }), 500


@applications_bp.route('/<int:application_id>/withdraw', methods=['POST'])
@job_seeker_required
def withdraw_application(application_id):
    """
    Withdraw an application (Job Seeker only - owner of the application)
    
    URL Parameter:
        application_id: The ID of the application to withdraw
    
    Note: Can only withdraw applications with PENDING status
    """
    try:
        user_id = get_jwt_identity()
        
        application = Application.query.get(application_id)
        
        if not application:
            return jsonify({
                'error': 'Application not found',
                'message': f'No application found with ID {application_id}'
            }), 404
        
        # Check if user owns the application
        if application.applicant_id != user_id:
            return jsonify({
                'error': 'Access denied',
                'message': 'You can only withdraw your own applications'
            }), 403
        
        # Check if application can be withdrawn
        if application.status != ApplicationStatus.PENDING:
            return jsonify({
                'error': 'Cannot withdraw application',
                'message': f'Application status is {application.status}. Only pending applications can be withdrawn.'
            }), 400
        
        # Update status to withdrawn
        application.status = ApplicationStatus.WITHDRAWN
        db.session.commit()
        
        return jsonify({
            'message': 'Application withdrawn successfully',
            'application': application.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'error': 'Failed to withdraw application',
            'message': str(e)
        }), 500


@applications_bp.route('/<int:application_id>/status', methods=['PUT'])
@employer_required
@resource_owner_or_employer_required(Application, 'application_id')
def update_application_status(application_id):
    """
    Update application status (Employer only - owner of the job)
    
    URL Parameter:
        application_id: The ID of the application
    
    Expected JSON payload:
    {
        "status": "accepted" | "rejected"
    }
    """
    try:
        application = Application.query.get(application_id)
        
        if not application:
            return jsonify({
                'error': 'Application not found',
                'message': f'No application found with ID {application_id}'
            }), 404
        
        data = request.get_json()
        
        if not data or 'status' not in data:
            return jsonify({
                'error': 'Missing status',
                'message': 'Status is required'
            }), 400
        
        new_status = data['status'].lower()
        
        # Validate status
        valid_statuses = [ApplicationStatus.ACCEPTED, ApplicationStatus.REJECTED]
        if new_status not in valid_statuses:
            return jsonify({
                'error': 'Invalid status',
                'message': f'Status must be one of: {", ".join(valid_statuses)}'
            }), 400
        
        # Check if application can be updated
        if application.status != ApplicationStatus.PENDING:
            return jsonify({
                'error': 'Cannot update status',
                'message': f'Application status is already {application.status}'
            }), 400
        
        # Update status
        application.status = new_status
        db.session.commit()
        
        return jsonify({
            'message': 'Application status updated successfully',
            'application': application.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'error': 'Failed to update application status',
            'message': str(e)
        }), 500


@applications_bp.route('/<int:application_id>', methods=['DELETE'])
@job_seeker_required
def delete_application(application_id):
    """
    Delete an application (Job Seeker only - owner of the application)
    
    URL Parameter:
        application_id: The ID of the application
    
    Note: Can only delete withdrawn applications
    """
    try:
        user_id = get_jwt_identity()
        
        application = Application.query.get(application_id)
        
        if not application:
            return jsonify({
                'error': 'Application not found',
                'message': f'No application found with ID {application_id}'
            }), 404
        
        # Check if user owns the application
        if application.applicant_id != user_id:
            return jsonify({
                'error': 'Access denied',
                'message': 'You can only delete your own applications'
            }), 403
        
        # Can only delete withdrawn applications
        if application.status != ApplicationStatus.WITHDRAWN:
            return jsonify({
                'error': 'Cannot delete application',
                'message': 'Application must be withdrawn before deletion'
            }), 400
        
        # Delete application
        db.session.delete(application)
        db.session.commit()
        
        return jsonify({
            'message': 'Application deleted successfully'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'error': 'Failed to delete application',
            'message': str(e)
        }), 500


@applications_bp.route('/job/<int:job_id>/check', methods=['GET'])
@job_seeker_required
def check_application_status(job_id):
    """
    Check if current user has applied to a specific job
    
    URL Parameter:
        job_id: The ID of the job
    
    Returns:
        application status if applied, or null if not applied
    """
    try:
        user_id = get_jwt_identity()
        
        # Get the job
        job = Job.query.get(job_id)
        
        if not job:
            return jsonify({
                'error': 'Job not found',
                'message': f'No job found with ID {job_id}'
            }), 404
        
        # Check if user applied
        application = Application.query.filter_by(
            job_id=job_id, 
            applicant_id=user_id
        ).first()
        
        if application:
            return jsonify({
                'has_applied': True,
                'application': application.to_applicant_view()
            }), 200
        else:
            return jsonify({
                'has_applied': False
            }), 200
        
    except Exception as e:
        return jsonify({
            'error': 'Failed to check application status',
            'message': str(e)
        }), 500

