#!/usr/bin/env python3
"""
Database Initialization Script
Creates all database tables and initializes sample data
"""
import os
import sys

# Add server directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import create_app, init_database
from models import db, User, UserRole
from werkzeug.security import generate_password_hash


def create_sample_data():
    """Create sample users for testing"""
    with app.app_context():
        # Check if sample data already exists
        existing_users = User.query.count()
        if existing_users > 0:
            print(f"Database already contains {existing_users} users. Skipping sample data creation.")
            return
        
        # Create sample employer
        employer = User(
            email='employer@company.com',
            role=UserRole.EMPLOYER,
            full_name='John Smith',
            company_name='Tech Solutions Inc.',
            phone='+1-555-0100'
        )
        employer.set_password('employer123')
        db.session.add(employer)
        
        # Create sample job seeker
        seeker = User(
            email='seeker@example.com',
            role=UserRole.JOB_SEEKER,
            full_name='Jane Doe',
            phone='+1-555-0200'
        )
        seeker.set_password('seeker123')
        db.session.add(seeker)
        
        # Create another employer
        employer2 = User(
            email='recruiter@startup.io',
            role=UserRole.EMPLOYER,
            full_name='Mike Johnson',
            company_name='Startup IO',
            phone='+1-555-0300'
        )
        employer2.set_password('employer123')
        db.session.add(employer2)
        
        # Create another job seeker
        seeker2 = User(
            email='developer@example.com',
            role=UserRole.JOB_SEEKER,
            full_name='Alex Wilson',
            phone='+1-555-0400'
        )
        seeker2.set_password('seeker123')
        db.session.add(seeker2)
        
        db.session.commit()
        print("Sample users created successfully!")
        print("\nSample Credentials:")
        print("-" * 50)
        print("Employer: employer@company.com / employer123")
        print("Job Seeker: seeker@example.com / seeker123")
        print("Employer 2: recruiter@startup.io / employer123")
        print("Job Seeker 2: developer@example.com / seeker123")
        print("-" * 50)


def create_test_jobs():
    """Create sample jobs for testing"""
    with app.app_context():
        from models import Job
        
        # Check if sample jobs already exist
        existing_jobs = Job.query.count()
        if existing_jobs > 0:
            print(f"Database already contains {existing_jobs} jobs. Skipping sample job creation.")
            return
        
        # Get employer
        employer = User.query.filter_by(email='employer@company.com').first()
        if not employer:
            print("No employer found. Please create sample users first.")
            return
        
        # Create sample jobs
        jobs = [
            Job(
                title='Senior Software Engineer',
                description='We are looking for a Senior Software Engineer to join our team. You will be responsible for designing and implementing scalable solutions.',
                requirements='- 5+ years of experience\n- Python or JavaScript expertise\n- PostgreSQL database experience\n- Cloud platform knowledge (AWS/GCP/Azure)',
                salary_range='$120,000 - $160,000',
                location='New York, NY',
                job_type='full-time',
                experience_level='senior',
                is_remote=False,
                employer_id=employer.id
            ),
            Job(
                title='Full Stack Developer',
                description='Join our dynamic team as a Full Stack Developer. You will work on both frontend and backend systems.',
                requirements='- 3+ years of experience\n- React.js and Node.js\n- RESTful API design\n- Git version control',
                salary_range='$90,000 - $130,000',
                location='Remote',
                job_type='full-time',
                experience_level='mid',
                is_remote=True,
                employer_id=employer.id
            ),
            Job(
                title='DevOps Engineer',
                description='We need a DevOps Engineer to help us build and maintain our infrastructure.',
                requirements='- Docker and Kubernetes\n- CI/CD pipelines\n- Linux administration\n- Scripting (Bash/Python)',
                salary_range='$100,000 - $140,000',
                location='San Francisco, CA',
                job_type='full-time',
                experience_level='mid',
                is_remote=False,
                employer_id=employer.id
            )
        ]
        
        for job in jobs:
            db.session.add(job)
        
        db.session.commit()
        print(f"Created {len(jobs)} sample jobs successfully!")


def reset_database():
    """Reset the database (drop and recreate all tables)"""
    with app.app_context():
        print("Dropping all database tables...")
        db.drop_all()
        print("Creating all database tables...")
        db.create_all()
        print("Database reset completed!")


def main():
    """Main function to run database initialization"""
    global app
    
    # Create app instance
    app = create_app()
    
    print("=" * 60)
    print("RecruitConnect Database Initialization")
    print("=" * 60)
    
    # Parse command line arguments
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == '--reset':
            confirm = input("This will DELETE all data. Continue? (yes/no): ")
            if confirm.lower() == 'yes':
                reset_database()
                create_sample_data()
                create_test_jobs()
            else:
                print("Operation cancelled.")
        elif command == '--sample-data':
            init_database(app)
            create_sample_data()
        elif command == '--sample-jobs':
            create_test_jobs()
        elif command == '--help':
            print("\nUsage: python init_db.py [command]")
            print("\nCommands:")
            print("  (none)      Initialize database and create all tables")
            print("  --reset     Drop and recreate all tables, then create sample data")
            print("  --sample-data  Create sample users")
            print("  --sample-jobs  Create sample jobs")
            print("  --help       Show this help message")
        else:
            print(f"Unknown command: {command}")
            print("Use --help for usage information")
    else:
        # Default: initialize database
        init_database(app)
        print("Database initialized successfully!")
        print("\nTo create sample data, run: python init_db.py --sample-data")
        print("To create sample jobs, run: python init_db.py --sample-jobs")
        print("To reset database, run: python init_db.py --reset")


if __name__ == '__main__':
    main()

