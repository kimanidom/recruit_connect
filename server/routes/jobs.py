"""
Job Routes - Employer Job Posting Management
Only Employers can access these routes to create, update, and delete jobs
"""
from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import Job, User, UserRole, db, ApplicationStatus, Application
from decorators import employer_required, resource_owner_or_employer_required

# Create blueprint for job routes
jobs_bp = Blueprint('jobs', __name__, url_prefix='/api/jobs')


@jobs_bp.route('', methods=['GET'])
@jwt_required()
def get_all_jobs():
    """
    Get all jobs (accessible by all authenticated users)
    
    Query Parameters:
        - page: Page number (default: 1)
        - per_page: Items per page (default: 10)
        - search: Search in title and description
        - location: Filter by location
        - job_type: Filter by job type
        - is_remote: Filter by remote status (true/false)
        - employer_id: Filter by specific employer (for admin purposes)
    
    Returns:
        Paginated list of jobs
    """
    try:
        # Get pagination parameters
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        search = request.args.get('search', '').strip()
        location = request.args.get('location', '').strip()
        job_type = request.args.get('job_type', '').strip()
        is_remote = request.args.get('is_remote', None)
        employer_id = request.args.get('employer_id', None, type=int)
        
        # Base query
        query = Job.query.filter_by(is_active=True)
        
        # Apply filters
        if search:
            search_term = f'%{search}%'
            query = query.filter(
                (Job.title.ilike(search_term)) | 
                (Job.description.ilike(search_term))
            )
        
        if location:
            query = query.filter(Job.location.ilike(f'%{location}%'))
        
        if job_type:
            query = query.filter(Job.job_type == job_type)
        
        if is_remote is not None:
            is_remote_bool = is_remote.lower() in ['true', '1', 'yes']
            query = query.filter(Job.is_remote == is_remote_bool)
        
        if employer_id:
            query = query.filter(Job.employer_id == employer_id)
        
        # Order by creation date (newest first)
        query = query.order_by(Job.created_at.desc())
        
        # Paginate
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        jobs = pagination.items
        
        return jsonify({
            'jobs': [job.to_summary() for job in jobs],
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
            'error': 'Failed to fetch jobs',
            'message': str(e)
        }), 500


@jobs_bp.route('/<int:job_id>', methods=['GET'])
@jwt_required()
def get_job(job_id):
    """
    Get a specific job by ID (accessible by all authenticated users)
    
    URL Parameter:
        job_id: The ID of the job
    
    Returns:
        Full job details
    """
    try:
        job = Job.query.get(job_id)
        
        if not job:
            return jsonify({
                'error': 'Job not found',
                'message': f'No job found with ID {job_id}'
            }), 404
        
        if not job.is_active:
            return jsonify({
                'error': 'Job not available',
                'message': 'This job posting has been deactivated'
            }), 404
        
        return jsonify({
            'job': job.to_dict()
        }), 200
        
    except Exception as e:
        return jsonify({
            'error': 'Failed to fetch job',
            'message': str(e)
        }), 500


@jobs_bp.route('', methods=['POST'])
@employer_required
def create_job():
    """
    Create a new job posting (Employer only)
    
    Expected JSON payload:
    {
        "title": "Software Engineer",
        "description": "Job description...",
        "requirements": "Required skills...",
        "salary_range": "$80,000 - $120,000",
        "location": "New York, NY",
        "job_type": "full-time",
        "experience_level": "mid",
        "is_remote": true
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
        
        # Validate required fields
        title = data.get('title', '').strip()
        description = data.get('description', '').strip()
        
        errors = []
        
        if not title:
            errors.append('Job title is required')
        elif len(title) < 5:
            errors.append('Job title must be at least 5 characters long')
        
        if not description:
            errors.append('Job description is required')
        
        if errors:
            return jsonify({
                'error': 'Validation failed',
                'messages': errors
            }), 400
        
        # Create new job
        job = Job(
            title=title,
            description=description,
            requirements=data.get('requirements', '').strip(),
            salary_range=data.get('salary_range', '').strip(),
            location=data.get('location', '').strip(),
            job_type=data.get('job_type', '').strip().lower(),
            experience_level=data.get('experience_level', '').strip().lower(),
            is_remote=data.get('is_remote', False),
            employer_id=user.id
        )
        
        db.session.add(job)
        db.session.commit()
        
        return jsonify({
            'message': 'Job posted successfully',
            'job': job.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'error': 'Failed to create job',
            'message': str(e)
        }), 500


@jobs_bp.route('/<int:job_id>', methods=['PUT'])
@employer_required
@resource_owner_or_employer_required(Job, 'job_id')
def update_job(job_id):
    """
    Update a job posting (Employer only - owner of the job)
    
    URL Parameter:
        job_id: The ID of the job to update
    
    Expected JSON payload (all fields optional):
    {
        "title": "Updated Job Title",
        "description": "Updated description...",
        "requirements": "Updated requirements...",
        "salary_range": "Updated salary",
        "location": "Updated location",
        "job_type": "full-time",
        "experience_level": "senior",
        "is_remote": true,
        "is_active": true
    }
    """
    try:
        job = Job.query.get(job_id)
        
        if not job:
            return jsonify({
                'error': 'Job not found',
                'message': f'No job found with ID {job_id}'
            }), 404
        
        data = request.get_json()
        
        if not data:
            return jsonify({
                'error': 'No data provided',
                'message': 'Request body must contain JSON data'
            }), 400
        
        # Update fields if provided
        if 'title' in data:
            title = data['title'].strip()
            if not title:
                return jsonify({
                    'error': 'Validation failed',
                    'messages': ['Job title cannot be empty']
                }), 400
            job.title = title
        
        if 'description' in data:
            description = data['description'].strip()
            if not description:
                return jsonify({
                    'error': 'Validation failed',
                    'messages': ['Job description cannot be empty']
                }), 400
            job.description = description
        
        if 'requirements' in data:
            job.requirements = data['requirements'].strip()
        
        if 'salary_range' in data:
            job.salary_range = data['salary_range'].strip()
        
        if 'location' in data:
            job.location = data['location'].strip()
        
        if 'job_type' in data:
            job.job_type = data['job_type'].strip().lower()
        
        if 'experience_level' in data:
            job.experience_level = data['experience_level'].strip().lower()
        
        if 'is_remote' in data:
            job.is_remote = bool(data['is_remote'])
        
        if 'is_active' in data:
            job.is_active = bool(data['is_active'])
        
        db.session.commit()
        
        return jsonify({
            'message': 'Job updated successfully',
            'job': job.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'error': 'Failed to update job',
            'message': str(e)
        }), 500


@jobs_bp.route('/<int:job_id>', methods=['DELETE'])
@employer_required
@resource_owner_or_employer_required(Job, 'job_id')
def delete_job(job_id):
    """
    Delete a job posting (Employer only - owner of the job)
    
    URL Parameter:
        job_id: The ID of the job to delete
    
    Note: Soft delete is preferred (setting is_active to False)
    """
    try:
        job = Job.query.get(job_id)
        
        if not job:
            return jsonify({
                'error': 'Job not found',
                'message': f'No job found with ID {job_id}'
            }), 404
        
        # Get query parameter for hard delete
        hard_delete = request.args.get('hard', 'false').lower() == 'true'
        
        if hard_delete:
            # Hard delete - remove from database
            db.session.delete(job)
            message = 'Job permanently deleted'
        else:
            # Soft delete - deactivate the job
            job.is_active = False
            message = 'Job deactivated (not deleted)'
        
        db.session.commit()
        
        return jsonify({
            'message': message,
            'job_id': job_id
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'error': 'Failed to delete job',
            'message': str(e)
        }), 500


@jobs_bp.route('/my-jobs', methods=['GET'])
@employer_required
def get_my_jobs():
    """
    Get all jobs posted by the current employer
    
    Query Parameters:
        - page: Page number (default: 1)
        - per_page: Items per page (default: 10)
        - include_inactive: Include inactive jobs (default: false)
    """
    try:
        user_id = get_jwt_identity()
        
        # Get query parameters
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        include_inactive = request.args.get('include_inactive', 'false').lower() == 'true'
        
        # Query jobs for this employer
        query = Job.query.filter_by(employer_id=user_id)
        
        if not include_inactive:
            query = query.filter_by(is_active=True)
        
        # Order by creation date (newest first)
        query = query.order_by(Job.created_at.desc())
        
        # Paginate
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        jobs = pagination.items
        
        return jsonify({
            'jobs': [job.to_dict() for job in jobs],
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
            'error': 'Failed to fetch jobs',
            'message': str(e)
        }), 500


@jobs_bp.route('/<int:job_id>/applications', methods=['GET'])
@employer_required
@resource_owner_or_employer_required(Job, 'job_id')
def get_job_applications(job_id):
    """
    Get all applications for a specific job (Employer only - owner of the job)
    
    URL Parameter:
        job_id: The ID of the job
    
    Query Parameters:
        - page: Page number (default: 1)
        - per_page: Items per page (default: 10)
        - status: Filter by application status
    """
    try:
        job = Job.query.get(job_id)
        
        if not job:
            return jsonify({
                'error': 'Job not found',
                'message': f'No job found with ID {job_id}'
            }), 404
        
        # Get query parameters
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        status = request.args.get('status', '').strip().lower()
        
        # Query applications for this job
        query = Application.query.filter_by(job_id=job_id)
        
        # Filter by status if provided
        if status and status in [ApplicationStatus.PENDING, ApplicationStatus.ACCEPTED, 
                                  ApplicationStatus.REJECTED, ApplicationStatus.WITHDRAWN]:
            query = query.filter_by(status=status)
        
        # Order by creation date (newest first)
        query = query.order_by(Application.created_at.desc())
        
        # Paginate
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        applications = pagination.items
        
        return jsonify({
            'applications': [app.to_dict() for app in applications],
            'job': job.to_summary(),
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

