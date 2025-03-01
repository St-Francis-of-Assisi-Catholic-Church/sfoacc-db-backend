import logging
from sqlalchemy.orm import Session
import pandas as pd
from datetime import datetime
import uuid
from typing import Dict, List, Any, Optional

from app.models.parishioner import (
    Parishioner, Occupation, FamilyInfo, Child, 
    EmergencyContact, MedicalCondition, Sacrament, Skill, Language,
    Gender, MaritalStatus, ParentalStatus, VerificationStatus, MembershipStatus, SacramentType
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ParishionerImportService:
    def __init__(self, db: Session):
        self.db = db
        
    def parse_date(self, date_str) -> Optional[datetime.date]:
        """Parse date string to datetime.date object"""
        if pd.isna(date_str) or not date_str:
            return None
        try:
            # Try different date formats
            for fmt in ["%d/%m/%Y", "%m/%d/%Y", "%Y-%m-%d"]:
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
        return str(text).strip()
    
    
    def clean_numeric_id(self, value) -> Optional[str]:
        """Clean numeric ID to ensure it's an integer string without decimal"""
        if pd.isna(value) or value is None:
            return None
        
        # Convert to string and strip whitespace
        value_str = str(value).strip()
        
        # If it's a decimal value , convert to integer
        if '.' in value_str:
            try:
                value_int = int(float(value_str))
                return str(value_int)
            except ValueError:
                return value_str
                
        return value_str
    
    
    def clean_phone_number(self, phone) -> Optional[str]:
        """Clean phone number to ensure 10-digit format"""
        if pd.isna(phone) or phone is None:
            return None
            
        # Convert to string and remove all non-digit characters
        phone_digits = ''.join(filter(str.isdigit, str(phone)))
        
        return phone_digits
    


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
        elif "widowed" in status_str:
            return MaritalStatus.WIDOWED
        elif "widow" in status_str:
            return MaritalStatus.WIDOWED
        elif "divorce" in status_str:
            return MaritalStatus.DIVORCED
        else:
            return MaritalStatus.SINGLE

    def map_parental_status(self, status_str) -> ParentalStatus:
        """Map parental status string to ParentalStatus enum"""
        if pd.isna(status_str) or not status_str:
            return ParentalStatus.UNKNOWN
        
        status_str = str(status_str).lower().strip()
        if "alive" in status_str:
            return ParentalStatus.ALIVE
        elif "deceased" in status_str:
            return ParentalStatus.DECEASED
        else:
            return ParentalStatus.UNKNOWN

    def generate_church_id(self, first_name: str, last_name: str, date_of_birth: datetime.date, old_church_id: str = None) -> str:
        """
        Generate a unique church ID based on:
        - First name initial
        - Last name initial
        - Day of birth (2 digits)
        - Month of birth (2 digits)
        - Old church ID (padded to 4 digits)
        
        Example: Kofi Nkrumah, born on May 2, 2000, with old ID of 8 
                 would get: KN0205-0008
        """
        # Get first initials
        first_initial = first_name[0].upper() if first_name else 'X'
        last_initial = last_name[0].upper() if last_name else 'X'
        
        # Get date components, padded with leading zeros
        day = f"{date_of_birth.day:02d}" if date_of_birth else "00"
        month = f"{date_of_birth.month:02d}" if date_of_birth else "00"
        
        # Format old church ID (padded to 4 digits) or use a random number if none exists
        if old_church_id and old_church_id.strip() and old_church_id.strip().isdigit():
            old_id = f"{int(old_church_id.strip()):04d}"
        else:
            # if no old church id, return null
            return
        # else:
        #     # Generate a random 4-digit number if no old ID is available
        #     import random
        #     old_id = f"{random.randint(1, 9999):04d}"
            
        # Combine all parts into the final ID
        return f"{first_initial}{last_initial}{day}{month}-{old_id}"

    def process_sacraments(self, parishioner_id: int, sacraments_str: str):
        """Process sacraments string and create sacrament records"""
        if pd.isna(sacraments_str) or not sacraments_str:
            return
            
        # Split by semicolon or comma
        sacraments_list = [s.strip() for s in str(sacraments_str).replace(',', ';').split(';') if s.strip()]
        
        for sacrament_str in sacraments_list:
            sacrament_type = None
            sacrament_str = sacrament_str.upper()
            
            if "BAPTISM" in sacrament_str:
                sacrament_type = SacramentType.BAPTISM
            elif "COMMUNION" in sacrament_str:
                sacrament_type = SacramentType.FIRST_COMMUNION
            elif "CONFIRMATION" in sacrament_str:
                sacrament_type = SacramentType.CONFIRMATION
            elif "PENANCE" in sacrament_str:
                sacrament_type = SacramentType.PENANCE
            elif "ANOINTING" in sacrament_str:
                sacrament_type = SacramentType.ANOINTING
            elif "ORDERS" in sacrament_str:
                sacrament_type = SacramentType.HOLY_ORDERS
            elif "MATRIMONY" in sacrament_str or "MARRIAGE" in sacrament_str:
                sacrament_type = SacramentType.MATRIMONY
            
            if sacrament_type:
                sacrament = Sacrament(
                    parishioner_id=parishioner_id,
                    type=sacrament_type,
                    date=datetime.now().date(),  # Default to today since we don't have actual date
                    place="Not specified",  # Default value
                    minister="Not specified"  # Default value
                )
                self.db.add(sacrament)

    def process_row(self, row: pd.Series) -> Dict[str, Any]:
        """Process a single row of CSV data"""
        try:
            # Parse the date of birth (should be validated already)
            date_of_birth = self.parse_date(row.get("Date of Birth", ""))
            if date_of_birth is None:
                return {"success": False, "error": f"Invalid date format for Date of Birth: {row.get('Date of Birth', '')}"}
            
         
             # Check if a parishioner with the same old_church_id already exists
            old_church_id = self.clean_numeric_id(row.get("Unique/ Old Church ID", ""))
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
                
            # Create Parishioner
            parishioner = Parishioner(
                new_church_id=self.generate_church_id(
                    first_name=self.clean_text(row["First Name"]), 
                    last_name=self.clean_text(row["Last Name (Surname)"]),
                    date_of_birth=date_of_birth,
                    old_church_id=old_church_id
                ),
                old_church_id=old_church_id,
                first_name=self.clean_text(row["First Name"]),
                other_names=self.clean_text(row.get("Other Names", "")),
                last_name=self.clean_text(row["Last Name (Surname)"]),
                maiden_name=self.clean_text(row.get("Maiden Name", "")),
                gender=self.map_gender(row.get("Gender", "")),
                date_of_birth=date_of_birth,
                place_of_birth=self.clean_text(row.get("Place of Birth", "")),
                hometown=self.clean_text(row.get("Hometown", "")),
                region=self.clean_text(row.get("Region/State", "")),
                country=self.clean_text(row.get("Country", "")),
                marital_status=self.map_marital_status(row.get("Marital Status", "")),
                mobile_number=self.clean_phone_number(row.get("Mobile Number", "")),
                whatsapp_number=self.clean_phone_number(row.get("WhatsApp Number", "")),
                email_address=self.clean_text(row.get("Email Address", "")),
                membership_status=MembershipStatus.ACTIVE,
                verification_status=VerificationStatus.UNVERIFIED,

                place_of_worship=self.clean_text(row.get("Place of Worship", "")),
                current_residence=self.clean_text(row.get("Current place of Residence/Area", "")),
            )

            
            
            self.db.add(parishioner)
            self.db.flush()  # Get the ID without committing
            
            # Create Occupation
            if not pd.isna(row.get("Occupation/Profession (Indicate Self-Employed or Not Employed)", "")) or not pd.isna(row.get("Current Workplace / Employer", "")):
                occupation = Occupation(
                    parishioner_id=parishioner.id,
                    role=self.clean_text(row.get("Occupation/Profession (Indicate Self-Employed or Not Employed)", "")) or "Not specified",
                    employer=self.clean_text(row.get("Current Workplace / Employer", "")) or "Not specified"
                )
                self.db.add(occupation)
            
            # Create FamilyInfo
            family_info = FamilyInfo(
                parishioner_id=parishioner.id,
                spouse_name=self.clean_text(row.get("Spouse Name", "")),
                father_name=self.clean_text(row.get("FATHER'S NAME", "")),
                father_status=self.map_parental_status(row.get("Father's Life Status", "")),
                mother_name=self.clean_text(row.get("MOTHER'S NAME", "")),
                mother_status=self.map_parental_status(row.get("Mother's Life Status", ""))
            )
            self.db.add(family_info)
            self.db.flush()  # Get the ID without committing
            
            # Create Children if any
            if not pd.isna(row.get("Name of Kids (if any)", "")):
                kids_str = str(row.get("Name of Kids (if any)", ""))
                # Split by comma or newline
                kids_list = [k.strip() for k in kids_str.replace('\n', ',').split(',') if k.strip()]
                
                for kid_name in kids_list:
                    child = Child(
                        family_info_id=family_info.id,
                        name=kid_name
                    )
                    self.db.add(child)
            
            # Create Emergency Contact
            if not pd.isna(row.get("Emergency Contact Name", "")) and not pd.isna(row.get("Emergency Contact Number", "")):
                emergency = EmergencyContact(
                    parishioner_id=parishioner.id,
                    name=self.clean_text(row.get("Emergency Contact Name", "")),
                    relationship="Not specified",  # Not in CSV
                    primary_phone=self.clean_text(row.get("Emergency Contact Number", ""))
                )
                self.db.add(emergency)
            
            # Create Medical Condition if any
            if not pd.isna(row.get("If Yes, Please State", "")) or (not pd.isna(row.get("Any Medical Condition", "")) and "yes" in str(row.get("Any Medical Condition", "")).lower()):
                condition_text = self.clean_text(row.get("If Yes, Please State", "")) or "Medical condition not specified"
                medical = MedicalCondition(
                    parishioner_id=parishioner.id,
                    condition=condition_text
                )
                self.db.add(medical)
            
            # Create Skills if any
            if not pd.isna(row.get("Skills/Talents", "")):
                skills_str = str(row.get("Skills/Talents", ""))
                # Split by comma or newline
                skills_list = [s.strip() for s in skills_str.replace('\n', ',').split(',') if s.strip()]
                
                for skill_name in skills_list:
                    # Check if skill exists
                    skill = self.db.query(Skill).filter(Skill.name == skill_name).first()
                    if not skill:
                        skill = Skill(name=skill_name)
                        self.db.add(skill)
                        self.db.flush()
                    
                    # Add skill to parishioner
                    parishioner.skills_rel.append(skill)

            
            # Create Languages if any
            if not pd.isna(row.get("Languages Spoken", "")):
                languages_str = str(row.get("Languages Spoken", ""))
                # Split by comma or newline
                languages_list = [l.strip() for l in languages_str.replace('\n', ',').split(',') if l.strip()]
                
                for language_name in languages_list:
                    # Check if language exists
                    language = self.db.query(Language).filter(Language.name == language_name).first()
                    if not language:
                        language = Language(name=language_name)
                        self.db.add(language)
                        self.db.flush()
                    
                    # Add language to parishioner
                    parishioner.languages_rel.append(language)


            
            # Process sacraments
            self.process_sacraments(parishioner.id, row.get("Church Sacrements", ""))
            
            self.db.commit()
            return {"success": True, "parishioner_id": parishioner.id}
            
        except Exception as e:
            self.db.rollback()
            return {"success": False, "error": str(e)}

    def import_csv(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Import data from CSV DataFrame"""
        result = {
            "total": len(df),
            "success": 0,
            "failed": 0,
            "errors": []
        }
        
        for index, row in df.iterrows():
            # Check if the row is empty (all values are NaN)
            if row.isna().all():
                # Skip empty rows
                continue
                
            row_result = self.process_row(row)
            
            if row_result["success"]:
                result["success"] += 1
            else:
                result["failed"] += 1
                error_detail = f"Error processing row {index+1}: {row_result['error']}"
                result["errors"].append(error_detail)
        
        return result