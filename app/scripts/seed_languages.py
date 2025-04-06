import logging
from sqlalchemy.exc import IntegrityError
from app.core.database import db
from app.models.language import Language

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def seed_languages():
    "Seed  the languages table with some common languages spoken"

    # initial languages
    languages_data = [
        {
            "name": "Akan",
            "description": "A language belonging to the Niger-Congo language family, widely spoken in Ghana"
        },
        {
            "name": "Akuapem Twi",
            "description": "A dialect of the Akan language spoken in the Eastern Region of Ghana"
        },
        {
            "name": "Asante Twi",
            "description": "A dialect of the Akan language spoken in the Ashanti Region of Ghana"
        },
        {
            "name": "Buem",
            "description": "A language spoken in the Volta Region of Ghana"
        },
        {
            "name": "Buli",
            "description": "A language spoken in the Upper East Region of Ghana"
        },
        {
            "name": "Chorkosi",
            "description": "A language spoken in the northeastern part of Ghana"
        },
        {
            "name": "Daagare", 
            "description": "A language spoken in the Upper West Region of Ghana"
        },
        {
            "name": "Dagaare",
            "description": "A language spoken in the Upper West Region of Ghana"
        },
        {
            "name": "Dagbani",
            "description": "A language spoken in the Northern Region of Ghana"
        },
        {
            "name": "Dangme",
            "description": "A language spoken in the Greater Accra and Eastern Regions of Ghana"
        },
        {
            "name": "English",
            "description": "The official language of Ghana used in government, education, and business"
        },
        {
            "name": "Ewe",
            "description": "A language spoken in the Volta Region of Ghana and parts of Togo"
        },
        {
            "name": "Fante",
            "description": "A dialect of the Akan language spoken in the Central and Western Regions of Ghana"
        },
        {
            "name": "Frafra",
            "description": "A language spoken in the Upper East Region of Ghana"
        },
        {
            "name": "French",
            "description": "A foreign language taught in schools and used in international relations"
        },
        {
            "name": "Ga",
            "description": "A language spoken in the Greater Accra Region of Ghana"
        },
        {
            "name": "Ga-Adangbe",
            "description": "A language group that includes Ga and Adangme languages"
        },
        {
            "name": "Guan",
            "description": "A language spoken in parts of the Eastern, Volta, and Northern Regions of Ghana"
        },
        {
            "name": "Hausa",
            "description": "A trade language widely spoken in northern Ghana and across West Africa"
        },
        {
            "name": "Igbo",
            "description": "A language from Nigeria sometimes spoken by Nigerian immigrants in Ghana"
        },
        {
            "name": "Kasem",
            "description": "A language spoken in the Upper East Region of Ghana"
        },
        {
            "name": "Krachi",
            "description": "A language spoken in the Oti Region of Ghana"
        },
        {
            "name": "Krobo",
            "description": "A dialect of Dangme spoken in the Eastern Region of Ghana"
        },
        {
            "name": "Kusasi",
            "description": "A language spoken in the Upper East Region of Ghana"
        },
        {
            "name": "Leleme",
            "description": "A language spoken in the Volta Region of Ghana"
        },
        {
            "name": "Nawuri",
            "description": "A language spoken in the Savannah Region of Ghana"
        },
        {
            "name": "Nzema",
            "description": "A language spoken in the Western Region of Ghana and parts of Ivory Coast"
        },
        {
            "name": "Sehwi",
            "description": "A language spoken in the Western North Region of Ghana"
        },
        {
            "name": "Sekpele",
            "description": "A language spoken in the Volta Region of Ghana"
        },
        {
            "name": "Sissali",
            "description": "A language spoken in the Upper West Region of Ghana"
        },
        {
            "name": "Siwu",
            "description": "A language spoken in the Volta Region of Ghana"
        },
        {
            "name": "Twi",
            "description": "A major dialect of the Akan language and one of the most widely spoken languages in Ghana"
        },
        {
            "name": "Waali",
            "description": "A language spoken in the Upper West Region of Ghana"
        },
        {
            "name": "Yoruba",
            "description": "A language from Nigeria sometimes spoken by Nigerian immigrants in Ghana"
        }
    ]

    with db.session() as session:
        # check if table already has data
        existing_count = session.query(Language).count()

        if existing_count > 0:
            logger.info(f"Languages table already has {existing_count} records. Skipping seed")
            return
        
        logger.info("Seeding Languages table")

        for language_data in languages_data:
            try:
                language = Language(**language_data)
                session.add(language)
                session.commit()
                logger.info(f"Added language: {language_data['name']}")
            except IntegrityError:
                session.rollback()
                logger.warning(f"Language '{language_data['name']}' already exists. Skipping")
            except Exception as e:
                session.rollback()
                logger.error(f"Error adding sacrament '{language_data['name']}': {str(e)}")

        logger.info("Languages seeding completed successfully")

if __name__ == "__main__":
    seed_languages()


    
