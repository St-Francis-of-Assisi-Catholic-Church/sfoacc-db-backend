from typing import Generator
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.declarative import declarative_base
from app.core.config import settings
import logging
from contextlib import contextmanager

logger = logging.getLogger(__name__)

Base = declarative_base()


class Database:
    def __init__(self):
        self._engine = None
        self._session_factory = None

    def init_app(self):
        if not self._engine:
            self._engine = create_engine(
                str(settings.SQLALCHEMY_DATABASE_URI),
                pool_pre_ping=True,
                pool_size=settings.DB_POOL_SIZE,
                max_overflow=settings.DB_MAX_OVERFLOW,
                pool_timeout=settings.DB_POOL_TIMEOUT,
                pool_recycle=settings.DB_POOL_RECYCLE,
            )
            self._session_factory = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self._engine,
            )

    def get_db(self) -> Generator[Session, None, None]:
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
        if not self._session_factory:
            self.init_app()
        try:
            with self._engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except Exception as e:
            logger.error(f"Database connection check failed: {str(e)}")
            return False

    def init_db(self) -> None:
        if not self._session_factory:
            self.init_app()
        try:
            from app.models.user import User  # noqa
            from app.models.parishioner import Parishioner  # noqa
            Base.metadata.create_all(bind=self._engine)
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Database initialization failed: {str(e)}")
            raise

    @contextmanager
    def session(self):
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
        if not self._engine:
            self.init_app()
        return self._engine

    @property
    def session_factory(self):
        if not self._session_factory:
            self.init_app()
        return self._session_factory


db = Database()

__all__ = ["Base", "db"]
