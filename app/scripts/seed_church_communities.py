#!/usr/bin/env python3
import logging
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from app.core.database import db
from app.models.church_community import ChurchCommunity
from app.models.parishioner import Parishioner  # Import the Parishioner model

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def seed_church_communities(force=True):
    """
    Seed the church_communities table with initial data.
    
    Args:
        force (bool): If True, truncate the table and reseed even if data exists
    """
    
    # Initial church communities data
    communities_data = [
         {
            "name": "Lakeside Community",
            "description": "",
            "location": ""
        },
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
            "name": "Sraha Community",
            "description": "",
            "location": ""
        },
        {
            "name": "Highways / Aviation Community",
            "description": "",
            "location": ""
        },
        {
            "name": "Old Town Community",
            "description": "",
            "location": ""
        },
        {
            "name": "Ogbojo Community",
            "description": "",
            "location": ""
        },
        {
            "name": "Little Roses/Nanakrom Community",
            "description": "",
            "location": ""
        },
        {
            "name": "Peace B Community",
            "description": "",
            "location": ""
        },
        {
            "name": "Ashaley Botwe Community",
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
        
            if existing_count > 0 and not force:
                logger.info(f"Church communities table already has {existing_count} records. Skipping seed.")
                return
            
            if existing_count > 0 and force:
                logger.info("Force flag is set. Truncating and reseeding church communities table.")
                
                # First, set any references to church_community_id to NULL in parishioners table
                logger.info("Setting church_community_id to NULL in parishioners table...")
                session.execute(
                    text("UPDATE parishioners SET church_community_id = NULL WHERE church_community_id IS NOT NULL")
                )
                
                # Then delete all records from church_communities table
                logger.info("Deleting all records from church_communities table...")
                session.execute(text("DELETE FROM church_communities"))
                
                session.commit()
                logger.info("Table truncated successfully.")
            
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
    import argparse
    
    parser = argparse.ArgumentParser(description="Seed church communities table")
    parser.add_argument("--force", action="store_true", help="Force truncate and reseed even if data exists")
    
    args = parser.parse_args()
    
    seed_church_communities(force=args.force)