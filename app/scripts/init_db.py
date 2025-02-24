# app/scripts/db_ops.py
import logging
from alembic.config import Config
from alembic import command
from pathlib import Path

from sqlalchemy import text
from app.core.database import db, Base

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_database():
    """Initialize database with all migrations"""
    try:
        # Get alembic config
        alembic_cfg = Config(str(Path(__file__).parent.parent.parent / "alembic.ini"))
        
        # # Create initial migration
        command.revision(alembic_cfg, autogenerate=True, message="Initial migration")
        
        # # Run migrations
        command.upgrade(alembic_cfg, "head")

        with db.session() as session:
            session.execute(text("SELECT 1"))
            logger.info("Database connection successfull")

        # create all tables
        # Base.metadata.create_all(bind=db.engine)
        logger.info("Database initialized successfully")
        return True
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        return False

if __name__ == "__main__":
    init_database()