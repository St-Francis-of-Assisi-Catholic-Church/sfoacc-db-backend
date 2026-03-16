"""
Seeds the default parish and outstations as church_units.
Run: python -m app.scripts.seed_parish
"""
import logging
from app.core.database import db
from app.models.parish import ChurchUnit, ChurchUnitType

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def seed_parish():
    db.init_app()
    with db.session() as session:
        parish = session.query(ChurchUnit).filter(
            ChurchUnit.type == ChurchUnitType.PARISH
        ).first()
        if not parish:
            parish = ChurchUnit(
                type=ChurchUnitType.PARISH,
                name="St. Francis of Assisi Catholic Church",
                diocese="Catholic Diocese of Koforidua",
                address="Accra, Ghana",
                pastor_name="",
            )
            session.add(parish)
            session.flush()
            logger.info("Created parish: St. Francis of Assisi")

            nanakrom = ChurchUnit(
                type=ChurchUnitType.OUTSTATION,
                parent_id=parish.id,
                name="Nanakrom",
                is_active=True,
            )
            session.add(nanakrom)
            logger.info("Created default outstation: Nanakrom")
        else:
            logger.info("Parish already exists, skipping.")

        logger.info("Parish seeding complete.")


if __name__ == "__main__":
    seed_parish()
