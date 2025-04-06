from typing import Generator
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.declarative import declarative_base
from app.core.config import settings
import logging
from contextlib import contextmanager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create Base class for SQLAlchemy models
Base = declarative_base()

class Database:
    def __init__(self):
        self._engine = None
        self._session_factory = None

    def init_app(self):
        """Initialize database connection"""
        if not self._engine:
            self._engine = create_engine(
                str(settings.SQLALCHEMY_DATABASE_URI),
                pool_pre_ping=True,
                pool_size=5,
                max_overflow=10,
                pool_timeout=30
            )

            self._session_factory = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self._engine
            )
    # def __init__(self):
    #     self._engine = create_engine(
    #         str(settings.SQLALCHEMY_DATABASE_URI),
    #         pool_pre_ping=True,
    #         pool_size=5,
    #         max_overflow=10,
    #         pool_timeout=30
    #     )

    #     self._session_factory = sessionmaker(
    #         autocommit=False,
    #         autoflush=False,
    #         bind=self._engine
    #     )

    def get_db(self) -> Generator[Session, None, None]:
        """Database session dependency."""
        if not self._session_factory:
            self.init_app()

        db = self._session_factory()
        try:
            yield db
        except Exception as e:
            logger.error(f"Database session error: {str(e)}")
            db.rollback()
            raise
        finally:
            db.close()

    async def check_connection(self) -> bool:
        """Check database connection."""
        if not self._session_factory:
            self.init_app()

        try:
            db = self._session_factory()
            db.execute(text("SELECT 1"))
            db.close()
            return True
        except Exception as e:
            logger.error(f"Database connection check failed: {str(e)}")
            return False

    def init_db(self) -> None:
        """Initialize database with all models."""
        if not self._session_factory:
            self.init_app()

        try:
            # Import all models here
            from app.models.user import User  # noqa
            from app.models.parishioner import Parishioner

            Base.metadata.create_all(bind=self._engine)
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Database initialization failed: {str(e)}")
            raise

    @contextmanager
    def session(self):
        """Context manager for database sessions."""
        if not self._session_factory:
            self.init_app()


        session = self._session_factory()
        
        try:
            yield session
            session.commit()
        except Exception as e:
            logger.error(f"Session error: {str(e)}")
            session.rollback()
            raise
        finally:
            session.close()


    def dispose(self):
        """Dispose of the current engine and session factory."""
        if self._engine:
            logger.info("Disposing database connection...")
            try:
                self._engine.dispose()
                self._engine = None
                self._session_factory = None
                logger.info("Database connection disposed successfully")
            except Exception as e:
                logger.error(f"Error disposing database connection: {str(e)}")
                raise

    @property
    def engine(self):
        """Get the SQLAlchemy engine."""
        if not self._engine:
            self.init_app()
        return self._engine

    @property
    def session_factory(self):
        """Get the session factory."""
        if not self._session_factory:
            self.init_app()
        return self._session_factory

# Create global database instance
db = Database()

# Export Base and db
__all__ = ['Base', 'db']