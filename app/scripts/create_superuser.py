import logging
from sqlalchemy import text
from app.core.database import db
from app.models.user import User, UserStatus, LoginMethod
from app.models.rbac import Role
from app.core.security import get_password_hash
from app.core.config import settings
import os
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def verify_database_connection():
    """Check if database is accessible"""
    try:
        with db.session() as session:
            session.execute(text("SELECT 1"))
            return True
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return False

def create_tables():
    """Create database tables"""
    try:
        db.init_db()
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Failed to create tables: {e}")
        raise

def create_superuser():
    """Create a superuser from environment variables"""
    try:
        if not verify_database_connection():
            logger.error("Cannot create superuser: Database not accessible")
            return False

        with db.session() as session:
            # Check if superuser already exists
            existing_user = session.query(User).filter(
                User.email == settings.FIRST_SUPERUSER
            ).first()
            
            if existing_user:
                # Update phone if it wasn't set yet
                if not existing_user.phone and settings.FIRST_SUPERUSER_PHONE:
                    existing_user.phone = settings.FIRST_SUPERUSER_PHONE
                    session.commit()
                    logger.info(f"Updated phone for {settings.FIRST_SUPERUSER}")
                logger.info(f"Superuser {settings.FIRST_SUPERUSER} already exists")
                return True

            # Look up the super_admin role
            super_admin_role = session.query(Role).filter(Role.name == "super_admin").first()
            role_id = super_admin_role.id if super_admin_role else None

            phone = settings.FIRST_SUPERUSER_PHONE or None

            # Create new superuser
            superuser = User(
                email=settings.FIRST_SUPERUSER,
                full_name="Super Admin",
                phone=phone,
                login_method=LoginMethod.PASSWORD,
                hashed_password=get_password_hash(settings.FIRST_SUPERUSER_PASSWORD),
                role_id=role_id,
                status=UserStatus.ACTIVE,
            )
            
            session.add(superuser)
            session.commit()
            logger.info(f"Superuser {settings.FIRST_SUPERUSER} created successfully")
            return True

    except Exception as e:
        logger.error(f"Failed to create superuser: {e}")
        return False

def verify_superuser():
    """Verify that superuser was created"""
    try:
        with db.session() as session:
            superuser = session.query(User).filter(
                User.email == settings.FIRST_SUPERUSER
            ).first()
            
            if superuser:
                role_name = superuser.role_ref.name if superuser.role_ref else "no role"
                logger.info(f"Verified superuser: {superuser.email} ({settings.FIRST_SUPERUSER}) ({settings.FIRST_SUPERUSER_PASSWORD}) (role: {role_name})")
                return True
            
            logger.error("Superuser verification failed: User not found")
            return False

    except Exception as e:
        logger.error(f"Failed to verify superuser: {e}")
        return False

if __name__ == "__main__":
    logger.info("Starting superuser creation process...")
    logger.info(f"Using configuration: FIRST_SUPERUSER={settings.FIRST_SUPERUSER}")
    
    try:
        # Create tables if they don't exist
        create_tables()
        
        # Create superuser
        if create_superuser():
            # Verify creation
            if verify_superuser():
                logger.info("Superuser creation process completed successfully")
                exit(0)
        
        logger.error("Superuser creation process failed")
        exit(1)
        
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        exit(1)