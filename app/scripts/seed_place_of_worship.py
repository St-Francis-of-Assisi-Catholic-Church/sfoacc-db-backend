#!/usr/bin/env python3
import logging
from sqlalchemy.exc import IntegrityError
from app.core.database import db
from app.models.place_of_worship import PlaceOfWorship

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def seed_places_of_worship():
    """Seed the places_of_worship table with initial data."""
    
    # Initial places of worship data
    places_data = [
        {
            "name": "St. Francis of Assisi",
            "description": "A Catholic church known for its vibrant community and solemn liturgical celebrations.",
            "location": "Ashaley Botwe, Accra",
            "address": "",
            "mass_schedule": ""
        },
        {
            "name": "St. Andrews",
            "description": "A welcoming place of worship serving the Catholic faithful in Nanakrom and its surroundings.",
            "location": "Nanakrom, Lakeside, Accra",
            "address": "",
            "mass_schedule": ""
        }
    ]
    
    with db.session() as session:
        try:
            # Check if table already has data
            existing_count = session.query(PlaceOfWorship).count()
            
            if existing_count > 0:
                logger.info(f"Places of worship table already has {existing_count} records. Skipping seed.")
                return
            
            logger.info("Seeding places of worship table...")
            
            for place_data in places_data:
                try:
                    place = PlaceOfWorship(**place_data)
                    session.add(place)
                    session.commit()
                    logger.info(f"Added place of worship: {place_data['name']}")
                except IntegrityError:
                    session.rollback()
                    logger.warning(f"Place of worship '{place_data['name']}' already exists. Skipping.")
                except Exception as e:
                    session.rollback()
                    logger.error(f"Error adding place of worship '{place_data['name']}': {str(e)}")
            
            logger.info("Places of worship seeding completed.")
        except Exception as e:
            logger.error(f"Error in seed_places_of_worship: {str(e)}")
            raise

if __name__ == "__main__":
    seed_places_of_worship()