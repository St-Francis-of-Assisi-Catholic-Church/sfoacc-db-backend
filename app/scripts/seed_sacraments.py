import logging
from sqlalchemy.exc import IntegrityError
from app.core.database import db
from app.models.sacrament import Sacrament

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def seed_sacraments():
    """Seed the sacrament_definitions table with initial data."""
    
    # Initial sacrament data
    sacraments_data = [
        {
            "name": "Baptism",
            "description": "The first sacrament of initiation, which cleanses a person of original sin and welcomes them into the Church as a child of God.",
            "once_only": True
        },
        {
            "name": "First Communion",
            "description": "Also known as First Holy Communion or Eucharist, this sacrament commemorates the Last Supper, where Catholics receive the Body and Blood of Christ in the form of bread and wine.",
            "once_only": True
        },
        {
            "name": "Confirmation",
            "description": "A sacrament of initiation where a baptized person receives the gifts of the Holy Spirit, strengthening their faith and commitment to the Church.",
            "once_only": True
        },
        {
            "name": "Penance",
            "description": "Also called Confession or Reconciliation, this sacrament allows Catholics to confess their sins, receive absolution from a priest, and be reconciled with God.",
            "once_only": False
        },
        {
            "name": "Anointing of the Sick",
            "description": "A sacrament of healing given to those who are seriously ill or near death, providing spiritual strength, comfort, and sometimes physical healing.",
            "once_only": False
        },
        {
            "name": "Holy Orders",
            "description": "The sacrament through which men are ordained as deacons, priests, or bishops to serve the Church in a special way.",
            "once_only": True
        },
        {
            "name": "Holy Matrimony",
            "description": "The sacrament of marriage, where a man and woman enter into a sacred covenant with God and each other, forming a lifelong union.",
            "once_only": False
        }
    ]
    
    with db.session() as session:
        # Check if table already has data
        existing_count = session.query(Sacrament).count()
        
        if existing_count > 0:
            logger.info(f"Sacraments table already has {existing_count} records. Skipping seed.")
            return
        
        logger.info("Seeding sacraments table...")
        
        for sacrament_data in sacraments_data:
            try:
                sacrament = Sacrament(**sacrament_data)
                session.add(sacrament)
                session.commit()
                logger.info(f"Added sacrament: {sacrament_data['name']}")
            except IntegrityError:
                session.rollback()
                logger.warning(f"Sacrament '{sacrament_data['name']}' already exists. Skipping.")
            except Exception as e:
                session.rollback()
                logger.error(f"Error adding sacrament '{sacrament_data['name']}': {str(e)}")
        
        logger.info("Sacraments seeding completed.")

if __name__ == "__main__":
    seed_sacraments()