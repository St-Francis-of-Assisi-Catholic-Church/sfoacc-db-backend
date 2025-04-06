#!/usr/bin/env python3
import logging
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from app.core.database import db
from app.models.church_community import ChurchCommunity

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def seed_church_communities():
    """Seed the church_communities table with initial data."""
    
    # Initial church communities data
    communities_data = [
        {
            "name": "3rd Gate Community",
            "description": "",
            "location": ""
        },
        {
            "name": "Nmai Djorn Community",
            "description": "",
            "location": ""
        },
        {
            "name": "Salem Community",
            "description": "",
            "location": ""
        },
        {
            "name": "Highways / Aviation Community",
            "description": "",
            "location": ""
        },
        {
            "name": "New Town Community",
            "description": "",
            "location": ""
        },
        {
            "name": "Ogbo Community",
            "description": "",
            "location": ""
        },
        {
            "name": "Others/Custom",
            "description": "For communities not listed in the predefined options",
            "location": ""
        }
    ]
    
    with db.session() as session:
        try:
            existing_count = session.query(ChurchCommunity).count()
        
            if existing_count > 0:
                logger.info(f"Church communities table already has {existing_count} records. Skipping seed.")
                return
            # Seed the data
            logger.info("Seeding church communities table...")
            
            for community_data in communities_data:
                try:
                    community = ChurchCommunity(**community_data)
                    session.add(community)
                    session.commit()
                    logger.info(f"Added church community: {community_data['name']}")
                except IntegrityError:
                    session.rollback()
                    logger.warning(f"Church community '{community_data['name']}' already exists. Skipping.")
                except Exception as e:
                    session.rollback()
                    logger.error(f"Error adding church community '{community_data['name']}': {str(e)}")
            
            logger.info("Church communities seeding completed.")
        except Exception as e:
            session.rollback()
            logger.error(f"Error in seed_church_communities: {str(e)}")
            raise

if __name__ == "__main__":
    seed_church_communities()