import logging
from sqlalchemy import func, or_
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
import pandas as pd
from datetime import datetime
import re
from typing import Dict, List, Any, Optional
from difflib import get_close_matches

from app.models.church_community import ChurchCommunity
from app.models.language import Language
from app.models.parishioner import (
    LifeStatus, Parishioner, Occupation, FamilyInfo, Child, 
    EmergencyContact, MedicalCondition, ParishionerSacrament, Skill,
    Gender, MaritalStatus, VerificationStatus, MembershipStatus
)
from app.models.sacrament import Sacrament, SacramentType
from app.models.place_of_worship import PlaceOfWorship
from app.models.society import Society, society_members, MembershipStatus

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ParishionerImportService:
    def __init__(self, db: Session):
        self.db = db
    
    def normalize_for_duplicate_check(self, value: str) -> str:
        """Normalize text values for consistent duplicate checking"""
        if not value:
            return ""
        return str(value).strip().lower()

    def normalize_multiitem_list(self, input_str: str) -> str:
        """
        Normalizes a multi-item string list by replacing various delimiters
        (like ', and ', ' and ', ',') with a semicolon (;).

        Args:
            input_str (str): The original string containing multiple items.

        Returns:
            str: A string where all item separators are semicolons.
        """
        if not input_str:
            return ""
        input_str = str(input_str)
        input_str = input_str.replace(', and ', ';')
        input_str = input_str.replace(' and ', ';')
        input_str = input_str.replace(',', ';')
        return input_str

    
    def check_for_duplicate(self, first_name: str, last_name: str, 
                          other_names: str = None, date_of_birth: datetime.date = None,
                          gender: Gender = None, place_of_birth: str = None) -> Optional[Parishioner]:
        """
        Check if a parishioner with the same combination of key fields already exists.
        Uses case-insensitive comparison and handles NULL values properly.
        
        Composite key: first_name, last_name, other_names, date_of_birth, gender, place_of_birth
        
        Returns:
            Parishioner: The existing parishioner if found, None otherwise
        """
        if not first_name or not last_name:
            return None
            
        # Normalize the search values
        search_first_name = self.normalize_for_duplicate_check(first_name)
        search_last_name = self.normalize_for_duplicate_check(last_name)
        search_other_names = self.normalize_for_duplicate_check(other_names)
        search_place_of_birth = self.normalize_for_duplicate_check(place_of_birth)
        
        # Build the query with case-insensitive comparison
        query = self.db.query(Parishioner).filter(
            func.lower(func.trim(Parishioner.first_name)) == search_first_name,
            func.lower(func.trim(Parishioner.last_name)) == search_last_name
        )
        
        # Handle other_names (can be NULL or empty)
        if search_other_names:
            query = query.filter(
                func.lower(func.trim(func.coalesce(Parishioner.other_names, ''))) == search_other_names
            )
        else:
            query = query.filter(
                or_(
                    Parishioner.other_names.is_(None),
                    func.trim(Parishioner.other_names) == ''
                )
            )
        
        # Handle date_of_birth (can be NULL)
        if date_of_birth:
            query = query.filter(Parishioner.date_of_birth == date_of_birth)
        else:
            query = query.filter(Parishioner.date_of_birth.is_(None))
        
        # Handle gender (should not be NULL for new records, but handle gracefully)
        if gender:
            query = query.filter(Parishioner.gender == gender)
        else:
            query = query.filter(Parishioner.gender == Gender.OTHER)
        
        # Handle place_of_birth (can be NULL or empty)
        if search_place_of_birth:
            query = query.filter(
                func.lower(func.trim(func.coalesce(Parishioner.place_of_birth, ''))) == search_place_of_birth
            )
        else:
            query = query.filter(
                or_(
                    Parishioner.place_of_birth.is_(None),
                    func.trim(Parishioner.place_of_birth) == ''
                )
            )
        
        return query.first()
    
    def format_duplicate_info(self, parishioner: Parishioner) -> str:
        """Format duplicate parishioner information for error messages"""
        info_parts = [f"Name: {parishioner.first_name} {parishioner.last_name}"]
        
        if parishioner.other_names:
            info_parts.append(f"Other Names: {parishioner.other_names}")
        if parishioner.date_of_birth:
            info_parts.append(f"DOB: {parishioner.date_of_birth}")
        if parishioner.gender:
            info_parts.append(f"Gender: {parishioner.gender.value}")
        if parishioner.place_of_birth:
            info_parts.append(f"Place of Birth: {parishioner.place_of_birth}")
        if parishioner.new_church_id:
            info_parts.append(f"Church ID: {parishioner.new_church_id}")
            
        return " | ".join(info_parts)
        
    def find_closest_match(self, name: str, model_class, field_name: str = 'name', cutoff: float = 0.6) -> Optional[Any]:
        """
        Find the closest matching entity by name in the database
        
        Args:
            name: The name to search for
            model_class: The SQLAlchemy model class to search in
            field_name: The field to match against (default: 'name')
            cutoff: The minimum similarity score (0-1) to consider a match
            
        Returns:
            The matching entity or None if no close match found
        """
        if not name:
            return None
            
        # Clean and normalize the input name
        search_name = name.lower().strip()
        
        # Get all entities from the database
        entities = self.db.query(model_class).all()
        
        # If no entities exist, return None
        if not entities:
            return None
            
        # Create a list of entity names
        entity_names = []
        entity_dict = {}
        
        for entity in entities:
            # Make sure the entity has the required attribute
            if hasattr(entity, field_name):
                entity_field_value = getattr(entity, field_name).lower().strip()
                entity_names.append(entity_field_value)
                entity_dict[entity_field_value] = entity
        
        # Find the closest match using difflib
        matches = get_close_matches(search_name, entity_names, n=1, cutoff=cutoff)
        
        if matches:
            closest_name = matches[0]
            logger.info(f"Found closest match for '{search_name}': '{closest_name}'")
            return entity_dict[closest_name]
        
        return None
    
    def parse_date(self, date_str) -> Optional[datetime.date]:
        """Parse date string to datetime.date object"""
        if pd.isna(date_str) or not date_str:
            return None
        try:
            # First try the required format YYYY-MM-DD
            try:
                return datetime.strptime(str(date_str).strip(), "%Y-%m-%d").date()
            except ValueError:
                # Try alternative formats if the primary format fails
                for fmt in ["%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y"]:
                    try:
                        return datetime.strptime(str(date_str).strip(), fmt).date()
                    except ValueError:
                        continue
            # If all formats failed, return None
            return None
        except:
            return None

    def clean_text(self, text) -> Optional[str]:
        """Clean and normalize text"""
        if pd.isna(text) or text is None:
            return None
        # Convert to title case (properly capitalized)
        return str(text).strip().title()
    
    def clean_numeric_id(self, value) -> Optional[str]:
        """Clean numeric ID to ensure it's an integer string without decimal"""
        if pd.isna(value) or value is None:
            return None
        
        # Convert to string and strip whitespace
        value_str = str(value).strip()
        
        # If it's a decimal value, convert to integer
        if '.' in value_str:
            try:
                value_int = int(float(value_str))
                return str(value_int)
            except ValueError:
                return value_str
                
        return value_str
    
    def clean_phone_number(self, phone) -> Optional[str]:
        """Clean phone number to ensure proper format"""
        if pd.isna(phone) or phone is None:
            return None
            
        # Convert to string and remove all non-digit characters
        phone_digits = ''.join(filter(str.isdigit, str(phone)))
        
        # Validate and format phone number
        if len(phone_digits) >= 9:  # Assume valid if at least 9 digits
            return phone_digits
        
        return None  # Invalid phone number

    def map_gender(self, gender_str) -> Gender:
        """Map gender string to Gender enum"""
        gender_map = {
            "male": Gender.MALE,
            "m": Gender.MALE,
            "female": Gender.FEMALE,
            "f": Gender.FEMALE,
        }
        if pd.isna(gender_str) or not gender_str:
            return Gender.OTHER
        
        gender_str = str(gender_str).lower().strip()
        return gender_map.get(gender_str, Gender.OTHER)

    def map_marital_status(self, status_str) -> MaritalStatus:
        """Map marital status string to MaritalStatus enum"""
        if pd.isna(status_str) or not status_str:
            return MaritalStatus.SINGLE
            
        status_str = str(status_str).lower().strip()
        if "single" in status_str:
            return MaritalStatus.SINGLE
        elif "married" in status_str:
            return MaritalStatus.MARRIED
        elif "widowed" in status_str or "widow" in status_str:
            return MaritalStatus.WIDOWED
        elif "divorce" in status_str:
            return MaritalStatus.DIVORCED
        else:
            return MaritalStatus.SINGLE

    def map_parental_status(self, status_str) -> LifeStatus:
        """Map parental status string to LifeStatus enum"""
        if pd.isna(status_str) or not status_str:
            return LifeStatus.UNKNOWN
        
        status_str = str(status_str).lower().strip()
        if "alive" in status_str:
            return LifeStatus.ALIVE
        elif "deceased" in status_str:
            return LifeStatus.DECEASED
        else:
            return LifeStatus.UNKNOWN

    def generate_church_id(self, first_name: str, last_name: str, date_of_birth: datetime.date, old_church_id: str = None) -> str:
        """
        Generate a unique church ID based on:
        - First name initial
        - Last name initial
        - Day of birth (2 digits)
        - Month of birth (2 digits)
        - Old church ID (padded to 5 digits)

        Example: Kofi Nkrumah, born on May 2, 2000, with old ID of 8
                 would get: KN0205-00008

        If no old_church_id is provided, return None (don't generate a new ID)
        """
        # If no old_church_id, don't generate new ID
        if not old_church_id:
            return None
        
        # if no date of birth, dont generate new ID
        if not date_of_birth:
            return None
            
        # Get first initials
        first_initial = first_name[0].upper() if first_name else 'X'
        last_initial = last_name[0].upper() if last_name else 'X'
        
        # Get date components, padded with leading zeros
        day = f"{date_of_birth.day:02d}" if date_of_birth else "00"
        month = f"{date_of_birth.month:02d}" if date_of_birth else "00"
        
        # Format old church ID (padded to 4 digits)
        if old_church_id and old_church_id.strip() and re.search(r'\d', old_church_id.strip()):
            # Extract digits from old_church_id
            digits = ''.join(filter(str.isdigit, old_church_id.strip()))
            old_id = f"{int(digits):05d}" if digits else None
            
            # Combine all parts into the final ID
            return f"{first_initial}{last_initial}{day}{month}-{old_id}" if old_id else None
        
        return None

    def map_sacrament_type(self, sacrament_str: str) -> Optional[str]:
        """Map sacrament string to SacramentType name"""
        sacrament_str = sacrament_str.upper().strip()
        
        if "BAPTISM" in sacrament_str:
            return SacramentType.BAPTISM
        elif "COMMUNION" in sacrament_str or "FIRST COMMUNION" in sacrament_str:
            return SacramentType.FIRST_COMMUNION
        elif "CONFIRMATION" in sacrament_str:
            return SacramentType.CONFIRMATION
        elif "PENANCE" in sacrament_str or "CONFESSION" in sacrament_str:
            return SacramentType.PENANCE
        elif "ANOINTING" in sacrament_str:
            return SacramentType.ANOINTING
        elif "ORDERS" in sacrament_str:
            return SacramentType.HOLY_ORDERS
        elif "MATRIMONY" in sacrament_str or "MARRIAGE" in sacrament_str:
            return SacramentType.MATRIMONY
        else:
            return None

    def process_sacraments(self, parishioner_id: int, sacraments_str: str):
        """Process sacraments string and create sacrament records"""
        if pd.isna(sacraments_str) or not sacraments_str:
            return
        
        sacraments_str = self.normalize_multiitem_list(sacraments_str)

        # Split by semicolon
        sacraments_list = [s.strip() for s in str(sacraments_str).split(';') if s.strip()]
        
        for sacrament_str in sacraments_list:
            # Map to a sacrament type
            sacrament_type = self.map_sacrament_type(sacrament_str)
            
            if sacrament_type:
                # First try exact match by name
                sacrament = self.db.query(Sacrament).filter(
                    Sacrament.name == sacrament_type
                ).first()
                
                # If not found, try fuzzy matching
                if not sacrament:
                    sacrament = self.find_closest_match(sacrament_type, Sacrament, 'name')
                
                if sacrament:
                    # Create a record for this parishioner and sacrament - don't set the date
                    parishioner_sacrament = ParishionerSacrament(
                        parishioner_id=parishioner_id,
                        sacrament_id=sacrament.id,
                        place="Not specified",
                        minister="Not specified"
                    )
                    self.db.add(parishioner_sacrament)
                else:
                    logger.warning(f"Sacrament '{sacrament_type}' not found in database and no close match found")

    def process_societies(self, parishioner_id: int, societies_str: str):
        """Process societies string and create society relationships"""
        if societies_str is None or not societies_str.strip():
            return
            
        # Normalize the societies string
        societies_str = self.normalize_multiitem_list(societies_str)

        # Split by semicolon
        societies_list = [s.strip() for s in str(societies_str).split(';') if s.strip()]
        
        for society_name in societies_list:
            society_name = self.clean_text(society_name)
            
            if society_name:
                # Try to find the society by exact name first
                society = self.db.query(Society).filter(
                    Society.name == society_name
                ).first()
                
                # If not found, try fuzzy matching
                if not society:
                    # Get all societies from the database
                    all_societies = self.db.query(Society).all()
                    
                    if all_societies:
                        # Create a mapping of society names to society objects
                        society_names = []
                        society_dict = {}
                        
                        for soc in all_societies:
                            soc_name = soc.name.lower().strip()
                            society_names.append(soc_name)
                            society_dict[soc_name] = soc
                        
                        # Find the closest match
                        matches = get_close_matches(society_name.lower(), society_names, n=1, cutoff=0.6)
                        
                        if matches:
                            closest_name = matches[0]
                            society = society_dict[closest_name]
                            logger.info(f"Found closest match for society '{society_name}': '{society.name}'")
                
                if society:
                    # Add relationship between parishioner and society
                    parishioner = self.db.query(Parishioner).get(parishioner_id)
                    if parishioner:
                        # Check if the relationship already exists
                        existing_membership = self.db.execute(
                            society_members.select().where(
                                society_members.c.society_id == society.id,
                                society_members.c.parishioner_id == parishioner.id
                            )
                        ).fetchone()
                        
                        if not existing_membership:
                            # Add to society members - don't set join_date
                            self.db.execute(
                                society_members.insert().values(
                                    society_id=society.id,
                                    parishioner_id=parishioner.id,
                                    membership_status=MembershipStatus.ACTIVE
                                )
                            )
                            logger.info(f"Added parishioner {parishioner.id} to society '{society.name}'")
                else:
                    logger.warning(f"Society '{society_name}' not found in database and no close match found")

    def process_languages(self, parishioner_id: int, languages_str: str):
        """Process languages string with better delimiter handling"""
        if pd.isna(languages_str) or not languages_str:
            return
        
        # Handle various delimiters (comma, 'and', semicolon)
        languages_str = self.normalize_multiitem_list(languages_str)

        # Split by semicolon
        languages_list = [l.strip() for l in languages_str.split(';') if l.strip()]
        
        for language_name in languages_list:
            language_name = self.clean_text(language_name)
            if language_name:
                # Check if language exists
                language = self.db.query(Language).filter(Language.name == language_name).first()
                if not language:
                    language = Language(name=language_name)
                    self.db.add(language)
                    self.db.flush()
                
                # Add language to parishioner
                parishioner = self.db.query(Parishioner).get(parishioner_id)
                if parishioner and language not in parishioner.languages_rel:
                    parishioner.languages_rel.append(language)

    def process_skills(self, parishioner_id: int, skills_str: str):
        """Process skills string with better delimiter handling"""
        if pd.isna(skills_str) or not skills_str:
            return
        
        # Handle various delimiters (comma, 'and', semicolon)
        skills_str = self.normalize_multiitem_list(skills_str)

        # Split by semicolon
        skills_list = [s.strip() for s in skills_str.split(';') if s.strip()]
        
        for skill_name in skills_list:
            skill_name = self.clean_text(skill_name)
            if skill_name:
                # Check if skill exists
                skill = self.db.query(Skill).filter(Skill.name == skill_name).first()
                if not skill:
                    skill = Skill(name=skill_name)
                    self.db.add(skill)
                    self.db.flush()
                
                # Add skill to parishioner
                parishioner = self.db.query(Parishioner).get(parishioner_id)
                if parishioner and skill not in parishioner.skills_rel:
                    parishioner.skills_rel.append(skill)


    def process_row(self, row: pd.Series, row_number: int) -> Dict[str, Any]:
        """
        Process a single row of CSV data using sanitized column names
        """
        try:
            # Parse the date of birth (should be validated already)
            date_of_birth = self.parse_date(row.get("date_of_birth", ""))
            
            # Check required fields using sanitized names
            required_fields = {
                "last_name": row.get("last_name", ""),
                "first_name": row.get("first_name", ""),
                "gender": row.get("gender", "")
            }
            
            for field, value in required_fields.items():
                if pd.isna(value) or not str(value).strip():
                    return {"success": False, "error": f"Missing required field: {field}"}
                
            # Clean the key fields for duplicate checking
            first_name = self.clean_text(row["first_name"])
            last_name = self.clean_text(row["last_name"])
            other_names = self.clean_text(row.get("other_names", ""))
            date_of_birth = self.parse_date(row.get("date_of_birth", ""))
            gender = self.map_gender(row.get("gender", ""))
            place_of_birth = self.clean_text(row.get("place_of_birth", ""))
            
            # Check for duplicates BEFORE creating the parishioner
            existing_parishioner = self.check_for_duplicate(
                first_name=first_name,
                last_name=last_name,
                other_names=other_names,
                date_of_birth=date_of_birth,
                gender=gender,
                place_of_birth=place_of_birth
            )

            if existing_parishioner:
                duplicate_info = self.format_duplicate_info(existing_parishioner)
                return {
                    "success": False, 
                    "error": f"Duplicate parishioner found. Existing record: {duplicate_info}",
                    "duplicate": True
                }
        
            # Get old church ID
            old_church_id = self.clean_numeric_id(row.get("unique_id", ""))
            
            # Check if a parishioner with the same old_church_id already exists
            if old_church_id:
                existing_parishioner = self.db.query(Parishioner).filter(
                    Parishioner.old_church_id == old_church_id
                ).first()
                
                if existing_parishioner:
                    return {
                        "success": False, 
                        "error": f"A parishioner with the old_Church_ID {old_church_id} already exists",
                        "duplicate": True
                    }
                
            # Generate new church ID (only if old_church_id is provided)
            new_church_id = None
            if old_church_id:
                new_church_id = self.generate_church_id(
                    first_name=self.clean_text(row["first_name"]), 
                    last_name=self.clean_text(row["last_name"]),
                    date_of_birth=date_of_birth,
                    old_church_id=old_church_id
                )
            
            # Handle place of worship
            place_of_worship_id = None
            if "place_worship" in row and not pd.isna(row["place_worship"]):
                place_name = self.clean_text(row["place_worship"])
                if place_name:
                    # Try to find the place of worship by exact name first
                    place_of_worship = self.db.query(PlaceOfWorship).filter(
                        PlaceOfWorship.name == place_name
                    ).first()
                    
                    # If not found, try fuzzy matching
                    if not place_of_worship:
                        place_of_worship = self.find_closest_match(place_name, PlaceOfWorship)
                    
                    # If it exists, use its ID
                    if place_of_worship:
                        place_of_worship_id = place_of_worship.id
                        if place_of_worship.name != place_name:
                            logger.info(f"Found place of worship '{place_of_worship.name}' as closest match for '{place_name}'")
                    else:
                        # If it doesn't exist, log a warning
                        logger.warning(f"Place of worship '{place_name}' not found in database and no close match found")

            # Handle church community
            church_community_id = None
            if "church_community" in row and not pd.isna(row["church_community"]):
                community_name = self.clean_text(row["church_community"])
                if community_name:
                    # Try to find the church community by exact name first
                    church_community = self.db.query(ChurchCommunity).filter(
                        ChurchCommunity.name == community_name
                    ).first()
                    
                    # If not found, try fuzzy matching
                    if not church_community:
                        church_community = self.find_closest_match(community_name, ChurchCommunity)
                    
                    # If it exists, use its ID
                    if church_community:
                        church_community_id = church_community.id
                        if church_community.name != community_name:
                            logger.info(f"Found church community '{church_community.name}' as closest match for '{community_name}'")
                    else:
                        # If it doesn't exist, log a warning
                        logger.warning(f"Church community '{community_name}' not found in database and no close match found")
            
            # Create Parishioner using sanitized column names
            parishioner = Parishioner(
                new_church_id=new_church_id,
                old_church_id=old_church_id,
                first_name=self.clean_text(row["first_name"]),
                other_names=self.clean_text(row.get("other_names", "")),
                last_name=self.clean_text(row["last_name"]),
                maiden_name=self.clean_text(row.get("maiden_name", "")),
                gender=self.map_gender(row.get("gender", "")),
                date_of_birth=date_of_birth,
                place_of_birth=self.clean_text(row.get("place_of_birth", "")),
                hometown=self.clean_text(row.get("hometown", "")),
                region=self.clean_text(row.get("region_state", "")),
                country=self.clean_text(row.get("country", "")),
                marital_status=self.map_marital_status(row.get("marital_status", "")),
                mobile_number=self.clean_phone_number(row.get("mobile_number", "")),
                whatsapp_number=self.clean_phone_number(row.get("whatsapp_number", "")),
                email_address=self.clean_text(row.get("email_address", "")),
                membership_status=MembershipStatus.ACTIVE,
                verification_status=VerificationStatus.UNVERIFIED,
                current_residence=self.clean_text(row.get("current_residence", "")),
                place_of_worship_id=place_of_worship_id,
                church_community_id=church_community_id
            )

            # Try to add the parishioner
            try:
                self.db.add(parishioner)
                self.db.flush()  # This will trigger the unique constraint check and get the ID
                
                # Store the ID before any potential session issues
                parishioner_id = parishioner.id
                
                # Create Occupation
                if ("occupation" in row and not pd.isna(row["occupation"])) or \
                ("employer" in row and not pd.isna(row["employer"])):
                    occupation = Occupation(
                        parishioner_id=parishioner_id,
                        role=self.clean_text(row.get("occupation", "")) or "Not specified",
                        employer=self.clean_text(row.get("employer", "")) or "Not specified"
                    )
                    self.db.add(occupation)

                # Create FamilyInfo
                family_info = FamilyInfo(
                    parishioner_id=parishioner_id,
                    spouse_name=self.clean_text(row.get("spouse_name", "")),
                    father_name=self.clean_text(row.get("father_name", "")),
                    father_status=self.map_parental_status(row.get("father_status", "")),
                    mother_name=self.clean_text(row.get("mother_name", "")),
                    mother_status=self.map_parental_status(row.get("mother_status", ""))
                )
                self.db.add(family_info)
                self.db.flush()  # Get the ID without committing

                # Create Children if any
                if "kids_names" in row and not pd.isna(row["kids_names"]):
                    kids_str = str(row["kids_names"])
                    kids_str = self.normalize_multiitem_list(kids_str)
                    kids_list = [k.strip() for k in kids_str.split(';') if k.strip()]
                    
                    for kid_name in kids_list:
                        child = Child(
                            family_info_id=family_info.id,
                            name=self.clean_text(kid_name)
                        )
                        self.db.add(child)

                # Create Emergency Contact
                if ("emergency_contact_name" in row and not pd.isna(row["emergency_contact_name"])) and \
                ("emergency_contact_number" in row and not pd.isna(row["emergency_contact_number"])):
                    emergency = EmergencyContact(
                        parishioner_id=parishioner_id,
                        name=self.clean_text(row["emergency_contact_name"]),
                        relationship="Not specified",  # Not in CSV
                        primary_phone=self.clean_phone_number(row["emergency_contact_number"])
                    )
                    self.db.add(emergency)

                # Create Medical Condition if any
                medical_conditions = None
                # Check explicit "medical_conditions" field first
                if "medical_conditions" in row and not pd.isna(row["medical_conditions"]):
                    medical_conditions = self.clean_text(row["medical_conditions"])
                # If not found, check the Yes/No field
                elif ("any_medical_condition" in row and not pd.isna(row["any_medical_condition"]) and 
                    "yes" in str(row["any_medical_condition"]).lower()):
                    if "medical_conditions_detail" in row and not pd.isna(row["medical_conditions_detail"]):
                        medical_conditions = self.clean_text(row["medical_conditions_detail"])
                    else:
                        medical_conditions = "Medical condition specified but details not provided"
                
                # Add the medical condition if found
                if medical_conditions:
                    medical = MedicalCondition(
                        parishioner_id=parishioner_id,
                        condition=medical_conditions
                    )
                    self.db.add(medical)

                # Create Skills if any
                if "skills_talents" in row and not pd.isna(row["skills_talents"]):
                    skills_str = str(row["skills_talents"])
                    skills_str = self.normalize_multiitem_list(skills_str)
                    skills_list = [s.strip() for s in skills_str.split(';') if s.strip()]
                    
                    for skill_name in skills_list:
                        skill_name = self.clean_text(skill_name)
                        # Check if skill exists
                        skill = self.db.query(Skill).filter(Skill.name == skill_name).first()
                        if not skill:
                            skill = Skill(name=skill_name)
                            self.db.add(skill)
                            self.db.flush()
                        
                        # Add skill to parishioner
                        parishioner.skills_rel.append(skill)
                
                # Create Languages if any
                if "languages_spoken" in row and not pd.isna(row["languages_spoken"]):
                    languages_str = str(row["languages_spoken"])
                    languages_str = self.normalize_multiitem_list(languages_str)
                    languages_list = [l.strip() for l in languages_str.split(';') if l.strip()]
                    
                    for language_name in languages_list:
                        language_name = self.clean_text(language_name)
                        # Check if language exists
                        language = self.db.query(Language).filter(Language.name == language_name).first()
                        if not language:
                            language = Language(name=language_name)
                            self.db.add(language)
                            self.db.flush()
                        
                        # Add language to parishioner
                        parishioner.languages_rel.append(language)
                
                # Process church societies if available
                if "church_groups" in row and not pd.isna(row["church_groups"]):
                    self.process_societies(parishioner_id, row["church_groups"])
                
                # Process sacraments
                if "church_sacraments" in row and not pd.isna(row["church_sacraments"]):
                    self.process_sacraments(parishioner_id, row["church_sacraments"])

                # Commit the transaction
                self.db.commit()
                logger.info(f"Successfully created parishioner: {first_name} {last_name} (Row {row_number})")
                return {"success": True, "parishioner_id": parishioner_id}
                
            except IntegrityError as e:
                self.db.rollback()
                error_msg = str(e).lower()
                
                if "unique_parishioner" in error_msg or "duplicate" in error_msg:
                    return {
                        "success": False, 
                        "error": "Duplicate parishioner detected at database level. A parishioner with the same combination of identifying information already exists.",
                        "duplicate": True
                    }
                else:
                    logger.error(f"Database integrity error: {str(e)}")
                    return {"success": False, "error": f"Database error: {str(e)}"}
                
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error processing row: {str(e)}", exc_info=True)
            return {"success": False, "error": str(e)}


    def import_csv(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Import data from CSV DataFrame"""
        result = {
            "total": len(df),
            "success": 0,
            "failed": 0,
            "errors": [],
            "duplicates": 0,
            "duplicate_details": []
        }

        logger.info(f"Starting import of {len(df)} records")
        
        for index, row in df.iterrows():
            # Skip completely empty rows
            if row.isna().all():
                result["total"] -= 1
                continue
                
            row_number = index + 2  # +2 because Excel/CSV rows start at 1 and we have headers

            try:
                # Process the row
                row_result = self.process_row(row, row_number)
                
                if row_result["success"]:
                    result["success"] += 1
                    if result["success"] % 100 == 0:  # Progress logging
                        logger.info(f"Processed {result['success']} records successfully...")
                else:
                    result["failed"] += 1
                    error_detail = f"Error processing row {row_number}: {row_result['error']}"
                    result["errors"].append(error_detail)

                    # Track duplicates separately
                    if row_result.get("duplicate", False):
                        result["duplicates"] += 1
                        result["duplicate_details"].append({
                            "row": row_number,
                            "name": f"{row.get('first_name', '')} {row.get('last_name', '')}",
                            "error": row_result['error']
                        })
                        
            except Exception as e:
                # Handle any unexpected errors
                try:
                    self.db.rollback()
                except:
                    pass  # Rollback might fail if session is already corrupted
                    
                result["failed"] += 1
                error_detail = f"Unexpected error for row {row_number}: {str(e)}"
                result["errors"].append(error_detail)
                logger.error(error_detail)
                
                # Continue with next row
                continue
        
        # Log the final results
        logger.info(f"Import completed: {result['success']} successful, {result['failed']} failed, {result['duplicates']} duplicates")
        
        return result

