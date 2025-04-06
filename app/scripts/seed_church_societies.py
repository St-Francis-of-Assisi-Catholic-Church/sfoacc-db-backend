import logging
from datetime import datetime, time, date
from sqlalchemy.exc import IntegrityError
from app.core.database import db
from app.models.society import Society, MeetingFrequency

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def seed_societies():
    """Seed the societies table with initial data."""
    
    # Initial societies data
    societies_data = [
        {
            "name": "Catholic Charismatic Renewal (CCR)",
            "description": "A spiritual movement within the Catholic Church that emphasizes the gifts of the Holy Spirit and a personal relationship with Jesus through prayer and worship.",
            "date_inaugurated": date(1990, 3, 15),
            "meeting_frequency": MeetingFrequency.WEEKLY,
            "meeting_day": "Friday",
            "meeting_time": time(18, 30),
            "meeting_venue": "Parish Hall"
        },
        {
            "name": "Christian Daughters Association",
            "description": "An association that promotes spiritual growth and charitable activities among young Catholic women in the parish.",
            "date_inaugurated": date(1995, 5, 20),
            "meeting_frequency": MeetingFrequency.MONTHLY,
            "meeting_day": "First Saturday",
            "meeting_time": time(16, 0),
            "meeting_venue": "Conference Room B"
        },
        {
            "name": "Christian Mothers Association",
            "description": "A society of Catholic mothers dedicated to promoting family values, raising children in the faith, and supporting parish activities.",
            "date_inaugurated": date(1988, 9, 8),
            "meeting_frequency": MeetingFrequency.MONTHLY,
            "meeting_day": "Second Sunday",
            "meeting_time": time(14, 0),
            "meeting_venue": "Parish Hall"
        },
        {
            "name": "St. Cecilia Ewe Society",
            "description": "A cultural and spiritual society for Ewe-speaking Catholics that promotes faith, culture, and community support.",
            "date_inaugurated": date(1997, 11, 22),
            "meeting_frequency": MeetingFrequency.MONTHLY,
            "meeting_day": "Last Sunday",
            "meeting_time": time(15, 30),
            "meeting_venue": "Small Hall"
        },
        {
            "name": "Catholic Youth Organization (CYO)",
            "description": "An organization for young Catholics aimed at fostering spiritual growth, leadership skills, and community service.",
            "date_inaugurated": date(1992, 2, 10),
            "meeting_frequency": MeetingFrequency.WEEKLY,
            "meeting_day": "Saturday",
            "meeting_time": time(16, 0),
            "meeting_venue": "Youth Center"
        },
        {
            "name": "Knights and Ladies of Mashall",
            "description": "A Catholic fraternal organization dedicated to charitable works, spiritual development, and supporting the Church's mission.",
            "date_inaugurated": date(1985, 10, 4),
            "meeting_frequency": MeetingFrequency.MONTHLY,
            "meeting_day": "First Wednesday",
            "meeting_time": time(19, 0),
            "meeting_venue": "Knights Hall"
        },
        {
            "name": "Holy Family Akan Society",
            "description": "A cultural and spiritual society for Akan-speaking Catholics that promotes faith and preserves cultural traditions.",
            "date_inaugurated": date(1993, 12, 30),
            "meeting_frequency": MeetingFrequency.MONTHLY,
            "meeting_day": "Third Sunday",
            "meeting_time": time(14, 0),
            "meeting_venue": "Parish Center"
        },
        {
            "name": "Knights of Saint John's International and Ladies Auxiliary (KSJI)",
            "description": "A uniformed Catholic fraternal organization dedicated to charity, unity, and fraternity in service to the Church.",
            "date_inaugurated": date(1983, 6, 24),
            "meeting_frequency": MeetingFrequency.BIWEEKLY,
            "meeting_day": "Second and Fourth Saturday",
            "meeting_time": time(17, 0),
            "meeting_venue": "KSJI Hall"
        },
        {
            "name": "Knights and Ladies of the Alter (KNOLTA)",
            "description": "A society that trains and supports altar servers in the parish, promoting reverence and proper liturgical service.",
            "date_inaugurated": date(1998, 8, 15),
            "meeting_frequency": MeetingFrequency.WEEKLY,
            "meeting_day": "Sunday",
            "meeting_time": time(12, 0),
            "meeting_venue": "Sacristy"
        },
        {
            "name": "Catholic Students Union (CASU)",
            "description": "An association for Catholic students that provides spiritual formation, community, and support during academic life.",
            "date_inaugurated": date(1994, 9, 1),
            "meeting_frequency": MeetingFrequency.WEEKLY,
            "meeting_day": "Thursday",
            "meeting_time": time(19, 0),
            "meeting_venue": "Student Center"
        },
        {
            "name": "League of Tarcisians",
            "description": "A society for children and pre-teens that provides early religious education and preparation for active participation in Church life.",
            "date_inaugurated": date(1999, 5, 5),
            "meeting_frequency": MeetingFrequency.WEEKLY,
            "meeting_day": "Saturday",
            "meeting_time": time(10, 0),
            "meeting_venue": "Children's Room"
        },
        {
            "name": "Lectors Ministry",
            "description": "A ministry dedicated to proclaiming the Word of God during liturgical celebrations with clarity and reverence.",
            "date_inaugurated": date(1986, 1, 12),
            "meeting_frequency": MeetingFrequency.MONTHLY,
            "meeting_day": "First Friday",
            "meeting_time": time(18, 0),
            "meeting_venue": "Church"
        },
        {
            "name": "Legion of Mary",
            "description": "A lay apostolic association dedicated to the Blessed Virgin Mary, focusing on prayer and active participation in the Church's evangelization efforts.",
            "date_inaugurated": date(1980, 8, 22),
            "meeting_frequency": MeetingFrequency.WEEKLY,
            "meeting_day": "Tuesday",
            "meeting_time": time(17, 30),
            "meeting_venue": "Legion Room"
        },
        {
            "name": "Sacred Heart of Jesus Confraternity",
            "description": "A spiritual association promoting devotion to the Sacred Heart of Jesus through prayer, adoration, and works of mercy.",
            "date_inaugurated": date(1981, 6, 19),
            "meeting_frequency": MeetingFrequency.MONTHLY,
            "meeting_day": "First Friday",
            "meeting_time": time(19, 0),
            "meeting_venue": "Chapel"
        },
        {
            "name": "Nigeria Community",
            "description": "A cultural and pastoral community for Nigerian Catholics to celebrate their heritage while growing in faith and supporting one another.",
            "date_inaugurated": date(2001, 10, 1),
            "meeting_frequency": MeetingFrequency.MONTHLY,
            "meeting_day": "Last Saturday",
            "meeting_time": time(16, 30),
            "meeting_venue": "Community Hall"
        },
        {
            "name": "Usher Group",
            "description": "A ministry focused on creating a welcoming environment at parish liturgies and events, handling seating, collections, and order.",
            "date_inaugurated": date(1982, 3, 7),
            "meeting_frequency": MeetingFrequency.MONTHLY,
            "meeting_day": "Second Saturday",
            "meeting_time": time(9, 0),
            "meeting_venue": "Parish Office"
        },
        {
            "name": "St. Theresa of Child Jesus",
            "description": "A society dedicated to following the 'little way' of St. Theresa, promoting simple acts of love and service in daily life.",
            "date_inaugurated": date(1991, 10, 1),
            "meeting_frequency": MeetingFrequency.MONTHLY,
            "meeting_day": "First Monday",
            "meeting_time": time(18, 0),
            "meeting_venue": "Meeting Room 1"
        },
        {
            "name": "St. Francis of Assisi (SFACC) Media Team",
            "description": "A team responsible for parish communications, including website management, social media, and audio-visual support for liturgies and events.",
            "date_inaugurated": date(2005, 6, 10),
            "meeting_frequency": MeetingFrequency.BIWEEKLY,
            "meeting_day": "Wednesday",
            "meeting_time": time(19, 0),
            "meeting_venue": "Media Room"
        },
        {
            "name": "St Gabriel Ga-Dangme Guild",
            "description": "A cultural and spiritual society for Ga-Dangme-speaking Catholics that preserves traditions while fostering faith development.",
            "date_inaugurated": date(1996, 4, 12),
            "meeting_frequency": MeetingFrequency.MONTHLY,
            "meeting_day": "Fourth Sunday",
            "meeting_time": time(15, 0),
            "meeting_venue": "Small Hall"
        },
        {
            "name": "St. Francis of Assisi Main Choir",
            "description": "The primary choir that leads music ministry during Sunday Masses and special liturgical celebrations in the parish.",
            "date_inaugurated": date(1979, 12, 8),
            "meeting_frequency": MeetingFrequency.WEEKLY,
            "meeting_day": "Wednesday",
            "meeting_time": time(18, 30),
            "meeting_venue": "Choir Loft"
        },
        {
            "name": "Northern Union",
            "description": "A community for Catholics from northern regions, providing spiritual and cultural support while fostering unity within diversity.",
            "date_inaugurated": date(2003, 7, 15),
            "meeting_frequency": MeetingFrequency.MONTHLY,
            "meeting_day": "Third Saturday",
            "meeting_time": time(16, 0),
            "meeting_venue": "Community Hall"
        },
        {
            "name": "St. Vincent de Paul",
            "description": "A charitable society dedicated to serving the poor and vulnerable through direct assistance and advocacy for social justice.",
            "date_inaugurated": date(1984, 9, 27),
            "meeting_frequency": MeetingFrequency.BIWEEKLY,
            "meeting_day": "Monday",
            "meeting_time": time(18, 0),
            "meeting_venue": "Conference Room A"
        }
    ]
    
    with db.session() as session:
        # Check if table already has data
        existing_count = session.query(Society).count()
        
        if existing_count > 0:
            logger.info(f"Societies table already has {existing_count} records. Skipping seed.")
            return
        
        logger.info("Seeding societies table...")
        
        for society_data in societies_data:
            try:
                society = Society(**society_data)
                session.add(society)
                session.commit()
                logger.info(f"Added society: {society_data['name']}")
            except IntegrityError:
                session.rollback()
                logger.warning(f"Society '{society_data['name']}' already exists. Skipping.")
            except Exception as e:
                session.rollback()
                logger.error(f"Error adding society '{society_data['name']}': {str(e)}")
        
        logger.info("Societies seeding completed.")

if __name__ == "__main__":
    seed_societies()