"""Database initialization and management"""

import os
from sqlalchemy import text
from .models.base import engine, Base, SessionLocal
from .auth.service import AuthService
import logging

logger = logging.getLogger(__name__)

def init_database():
    """Initialize database tables and default data"""
    try:
        # Create all tables
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
        
        # Setup default roles and admin user
        setup_initial_data()
        
        return True
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        return False

def setup_initial_data():
    """Setup initial roles and admin user"""
    try:
        auth_service = AuthService()
        
        # Setup default roles
        auth_service.setup_default_roles()
        logger.info("Default roles created")
        
        # Only create admin if enabled by environment variable
        if os.getenv('CREATE_DEFAULT_ADMIN', 'false').lower() == 'true':
            admin_username = os.getenv('ADMIN_USERNAME', 'admin')
            admin_password = os.getenv('ADMIN_PASSWORD', 'admin123')
            admin_email = os.getenv('ADMIN_EMAIL', 'admin@sistemas-olivium.com')
            
            admin = auth_service.setup_default_admin(
                username=admin_username,
                password=admin_password,
                email=admin_email
            )
            logger.info(f"Default admin user created: {admin.username}")
            
    except Exception as e:
        logger.error(f"Failed to setup initial data: {e}")

def migrate_from_old_database():
    """Migrate data from old app.py database structure"""
    try:
        from .models.host import Host, HostHistory, HostStatus
        
        with SessionLocal() as db:
            # Check if we need to migrate
            existing_hosts = db.query(Host).first()
            if existing_hosts:
                logger.info("Database already contains hosts, skipping migration")
                return True
            
            # Try to read from old CSV structure
            import csv
            machines_file = "machines.csv"
            if os.path.exists(machines_file):
                with open(machines_file, "r", encoding="utf-8") as f:
                    reader = csv.reader(f)
                    next(reader, None)  # Skip header
                    
                    imported_count = 0
                    for row in reader:
                        if len(row) >= 2:
                            name = row[0].strip()
                            fallback_ip = row[1].strip()
                            
                            if name:
                                host = Host(
                                    hostname=name,
                                    fallback_ip=fallback_ip,
                                    enabled=True
                                )
                                db.add(host)
                                imported_count += 1
                    
                    db.commit()
                    logger.info(f"Migrated {imported_count} hosts from machines.csv")
                    
        return True
        
    except Exception as e:
        logger.error(f"Failed to migrate from old database: {e}")
        return False

def check_database_health():
    """Check database connection and basic functionality"""
    try:
        with SessionLocal() as db:
            # Test basic query
            result = db.execute(text("SELECT 1")).fetchone()
            if result and result[0] == 1:
                return True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
    
    return False