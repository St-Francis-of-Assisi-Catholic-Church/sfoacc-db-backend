from app.core.config import settings
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import text

import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# engine = create_engine(settings.database_url)
engine = create_engine(
    str(settings.SQLALCHEMY_DATABASE_URI), 
    pool_pre_ping=True,
)

# Create sessionmaker
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


# Create declarative base for models
Base = declarative_base()

def get_db() -> Generator[Session, None, None]:
    """
    Database session dependency.
    
    Yields:
        Session: Database session
    
    Example:
        @app.get("/users")
        def get_users(db: Session = Depends(get_db)):
            return db.query(User).all()
    """
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"Database session error: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()

async def check_database_connection() -> bool:
    """
    Check if database connection is working.
    
    Returns:
        bool: True if connection is successful, False otherwise
    """
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        return True
    except Exception as e:
        logger.error(f"Database connection check failed: {str(e)}")
        return False
    

def init_db() -> None:
    """
    Initialize database with all models.
    Creates all tables if they don't exist.
    """
    try:
        # Import all models here
        from app.models.user import User  

        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {str(e)}")
        raise


class DatabaseSessionManager:
    """
    Context manager for database sessions.
    
    Example:
        with DatabaseSessionManager() as db:
            db.query(User).all()
    """
    def __init__(self):
        self.db = SessionLocal()

    def __enter__(self) -> Session:
        return self.db

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            logger.error(f"Error in database session: {str(exc_val)}")
            self.db.rollback()
        self.db.close()

def get_db_session():
    """
    Get a database session using context manager.
    """
    return DatabaseSessionManager()