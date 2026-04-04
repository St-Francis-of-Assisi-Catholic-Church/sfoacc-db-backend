import logging
from alembic.config import Config
from alembic import command
from pathlib import Path
from sqlalchemy import text

from app.core.database import db

# Import all models so Base.metadata.create_all picks them up
from app.models.parish import ChurchUnit, MassSchedule  # noqa: F401
from app.models.rbac import Role, Permission  # noqa: F401
from app.models.settings import ParishSettings  # noqa: F401

logger = logging.getLogger(__name__)


def init_database():
    """Apply all pending Alembic migrations and verify DB connectivity."""
    try:
        alembic_cfg = Config(str(Path(__file__).parent.parent.parent / "alembic.ini"))

        # Check if any migration scripts exist
        versions_dir = Path(__file__).parent.parent.parent / "alembic" / "versions"
        migration_files = [
            f for f in versions_dir.glob("*.py")
            if not f.name.startswith("__")
        ]

        if not migration_files:
            logger.info("No migrations found — generating initial migration...")
            command.revision(alembic_cfg, autogenerate=True, message="initial migration")
            logger.info("Initial migration generated.")

        logger.info("Applying migrations...")
        command.upgrade(alembic_cfg, "head")

        with db.session() as session:
            session.execute(text("SELECT 1"))

        logger.info("Database initialised successfully.")
        return True

    except Exception as e:
        logger.error(f"Database initialisation failed: {e}")
        return False


if __name__ == "__main__":
    init_database()
