"""
Database Models for RecruitConnect Application
"""
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

# Enum-like class for user roles
class UserRole:
    EMPLOYER = 'employer'
    JOB_SEEKER = 'job_seeker'

class ApplicationStatus:
    PENDING = 'pending'
    ACCEPTED = 'accepted'
    REJECTED = 'rejected'
    WITHDRAWN = 'withdrawn'


class User(db.Model):
    """User model for both Employers and Job Seekers"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default=UserRole.JOB_SEEKER)
    full_name = db.Column(db.String(100), nullable=True)
    company_name = db.Column(db.String(100), nullable=True)  # For employers
    phone = db.Column(db.String(20), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    jobs = db.relationship('Job', backref='employer', lazy='dynamic', 
                          foreign_keys='Job.employer_id')
    applications = db.relationship('Application', backref='applicant', 
                                   lazy='dynamic', foreign_keys='Application.applicant_id')
    
    def __repr__(self):
        return f'<User {self.email} ({self.role})>'
    
    def set_password(self, password):
        """Set password hash from plain password"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check if the provided password matches the stored hash"""
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self):
        """Convert user to dictionary (without password)"""
        return {
            'id': self.id,
            'email': self.email,
            'role': self.role,
            'full_name': self.full_name,
            'company_name': self.company_name,
            'phone': self.phone,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    @property
    def is_employer(self):
        """Check if user is an employer"""
        return self.role == UserRole.EMPLOYER
    
    @property
    def is_job_seeker(self):
        """Check if user is a job seeker"""
        return self.role == UserRole.JOB_SEEKER


class Job(db.Model):
    """Job posting model"""
    __tablename__ = 'jobs'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    requirements = db.Column(db.Text, nullable=True)
    salary_range = db.Column(db.String(100), nullable=True)
    location = db.Column(db.String(200), nullable=True)
    job_type = db.Column(db.String(50), nullable=True)  # full-time, part-time, contract, etc.
    experience_level = db.Column(db.String(50), nullable=True)  # entry, mid, senior
    is_remote = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Foreign key to employer
    employer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    
    # Relationship to applications
    applications = db.relationship('Application', backref='job', lazy='dynamic',
                                   foreign_keys='Application.job_id')
    
    def __repr__(self):
        return f'<Job {self.title}>'
    
    def to_dict(self):
        """Convert job to dictionary"""
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'requirements': self.requirements,
            'salary_range': self.salary_range,
            'location': self.location,
            'job_type': self.job_type,
            'experience_level': self.experience_level,
            'is_remote': self.is_remote,
            'is_active': self.is_active,
            'employer_id': self.employer_id,
            'employer_name': self.employer.company_name if self.employer else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'application_count': self.applications.count()
        }
    
    def to_summary(self):
        """Convert job to summary dictionary (lighter version)"""
        return {
            'id': self.id,
            'title': self.title,
            'company_name': self.employer.company_name if self.employer else None,
            'location': self.location,
            'job_type': self.job_type,
            'salary_range': self.salary_range,
            'is_remote': self.is_remote,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class Application(db.Model):
    """Application model for job applications"""
    __tablename__ = 'applications'
    
    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey('jobs.id'), nullable=False, index=True)
    applicant_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    status = db.Column(db.String(20), default=ApplicationStatus.PENDING)
    cover_letter = db.Column(db.Text, nullable=True)
    resume_url = db.Column(db.String(500), nullable=True)
    additional_info = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    job = db.relationship('Job', backref=db.backref('app_job_applications', lazy='dynamic'))
    applicant = db.relationship('User', backref=db.backref('user_applications', lazy='dynamic'))
    
    def __repr__(self):
        return f'<Application {self.id} for Job {self.job_id}>'
    
    def to_dict(self):
        """Convert application to dictionary"""
        return {
            'id': self.id,
            'job_id': self.job_id,
            'job_title': self.job.title if self.job else None,
            'applicant_id': self.applicant_id,
            'applicant_name': self.applicant.full_name if self.applicant else None,
            'applicant_email': self.applicant.email if self.applicant else None,
            'status': self.status,
            'cover_letter': self.cover_letter,
            'resume_url': self.resume_url,
            'additional_info': self.additional_info,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def to_applicant_view(self):
        """Convert application to dictionary for applicant view"""
        return {
            'id': self.id,
            'job_id': self.job_id,
            'job_title': self.job.title if self.job else None,
            'employer_name': self.job.employer.company_name if self.job and self.job.employer else None,
            'status': self.status,
            'applied_at': self.created_at.isoformat() if self.created_at else None
        }

