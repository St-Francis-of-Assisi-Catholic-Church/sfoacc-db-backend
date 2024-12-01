import logging
from sqlalchemy import text
from app.core.database import db
from app.models.user import User, UserRole
from app.core.security import get_password_hash
from app.core.config import settings

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
                logger.info(f"Superuser {settings.FIRST_SUPERUSER} already exists")
                return True

            # Create new superuser
            superuser = User(
                email=settings.FIRST_SUPERUSER,
                full_name="Super Admin",
                hashed_password=get_password_hash(settings.FIRST_SUPERUSER_PASSWORD),
                role=UserRole.SUPER_ADMIN,
                is_active=True
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
                logger.info(f"Verified superuser: {superuser.email} (role: {superuser.role})")
                return True
            
            logger.error("Superuser verification failed: User not found")
            return False

    except Exception as e:
        logger.error(f"Failed to verify superuser: {e}")
        return False

if __name__ == "__main__":
    logger.info("Starting superuser creation process...")
    
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