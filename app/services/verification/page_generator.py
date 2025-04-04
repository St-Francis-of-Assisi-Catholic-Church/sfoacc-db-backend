from datetime import datetime
from typing import Dict, Any, List
from app.models.parishioner import ( Parishioner as
    ParishionerModel , Occupation, FamilyInfo,
    EmergencyContact, MedicalCondition, ParSacrament, Skill, Child
)
from .page_template import verification_page_template

class VerificationPageGenerator:
    """Service to generate HTML verification pages for parishioners"""
    
    @staticmethod
    def _format_detail_item(label: str, value: Any) -> str:
        """Format a single detail item with label and value"""
        if value is None:
            value = "Not provided"
        
        # Handle datetime objects
        if isinstance(value, datetime):
            value = value.strftime("%d %B, %Y")
            
        # Handle date objects
        if hasattr(value, 'strftime'):
            try:
                value = value.strftime("%d %B, %Y")
            except:
                pass
                
        return f"""
            <div class="detail-group">
                <div class="detail-label">{label}:</div>
                <div class="detail-value">{value}</div>
            </div>
        """
    
    @staticmethod
    def _format_detail_section(items: List[Dict[str, Any]]) -> str:
        """Format a section of detail items"""
        html = ""
        for item in items:
            html += VerificationPageGenerator._format_detail_item(item["label"], item["value"])
        return html
    
    @staticmethod
    def generate_access_code(parishioner: ParishionerModel) -> str:
        """Generate access code based on parishioner's date of birth in ddmmyyyy format"""
        if not parishioner.date_of_birth:
            # Fallback if no date of birth is available
            return "00000000"
        
        # Format as ddmmyyyy
        day = str(parishioner.date_of_birth.day).zfill(2)
        month = str(parishioner.date_of_birth.month).zfill(2)
        year = str(parishioner.date_of_birth.year)
        
        return f"{day}{month}{year}"
    
    @classmethod
    def generate_page(cls, parishioner: ParishionerModel) -> Dict[str, str]:
        """
        Generate HTML verification page for a parishioner
        
        Returns:
            Dict with 'html' containing the page HTML and 'access_code' with the generated code
        """
        # Generate access code for this parishioner
        access_code = cls.generate_access_code(parishioner)
        
        # Personal Information Section
        personal_info = cls._format_detail_section([
            {"label": "Full Name", "value": f"{parishioner.first_name} {parishioner.other_names or ''} {parishioner.last_name}".strip()},
            {"label": "Gender", "value": parishioner.gender.value if parishioner.gender else None},
            {"label": "Date of Birth", "value": parishioner.date_of_birth},
            {"label": "Place of Birth", "value": parishioner.place_of_birth},
            {"label": "Hometown", "value": parishioner.hometown},
            {"label": "Region", "value": parishioner.region},
            {"label": "Country", "value": parishioner.country},
            {"label": "Marital Status", "value": parishioner.marital_status.value if parishioner.marital_status else None},
        ])
        
        # Contact Information Section
        contact_info = cls._format_detail_section([
            {"label": "Mobile Number", "value": parishioner.mobile_number},
            {"label": "WhatsApp Number", "value": parishioner.whatsapp_number},
            {"label": "Email Address", "value": parishioner.email_address},
            {"label": "Current Residence", "value": parishioner.current_residence},
        ])
        
        # Family Information
        family_items = [
            {"label": "Marital Status", "value": parishioner.marital_status.value if parishioner.marital_status else None},
        ]
        
        if parishioner.family_info_rel:
            family = parishioner.family_info_rel
            family_items.extend([
                {"label": "Spouse Name", "value": family.spouse_name},
                {"label": "Spouse Status", "value": family.spouse_status},
                {"label": "Spouse Phone", "value": family.spouse_phone},
                {"label": "Father's Name", "value": family.father_name},
                {"label": "Father's Status", "value": family.father_status.value if family.father_status else None},
                {"label": "Mother's Name", "value": family.mother_name},
                {"label": "Mother's Status", "value": family.mother_status.value if family.mother_status else None},
            ])
            
            # Add children if any
            if family.children_rel:
                children_names = [child.name for child in family.children_rel]
                family_items.append({"label": "Children", "value": ", ".join(children_names)})
        
        family_info = cls._format_detail_section(family_items)
        
        # Occupation Information
        occupation_items = [{"label": "No occupation information", "value": None}]
        if parishioner.occupation_rel:
            occupation = parishioner.occupation_rel
            occupation_items = [
                {"label": "Role", "value": occupation.role},
                {"label": "Employer", "value": occupation.employer},
            ]
        occupation_info = cls._format_detail_section(occupation_items)
        
        # Church Information
        church_info = cls._format_detail_section([
            {"label": "Old Church ID", "value": parishioner.old_church_id},
            {"label": "New Church ID", "value": parishioner.new_church_id},
            {"label": "Place of Worship", "value": parishioner.place_of_worship},
            {"label": "Membership Status", "value": parishioner.membership_status.value if parishioner.membership_status else None},
            {"label": "Verification Status", "value": parishioner.verification_status.value if parishioner.verification_status else None},
        ])
        
        # Sacraments Information
        sacraments_html = ""
        if parishioner.par_sacraments_rel:
            for sacrament in parishioner.par_sacraments_rel:
                sacrament_html = cls._format_detail_section([
                    {"label": "Type", "value": sacrament.type.value if sacrament.type else None},
                    {"label": "Date", "value": sacrament.date},
                    {"label": "Place", "value": sacrament.place},
                    {"label": "Minister", "value": sacrament.minister},
                ])
                sacraments_html += f"<div class='detail-group'>{sacrament_html}</div>"
        
        if not sacraments_html:
            sacraments_html = cls._format_detail_item("Sacraments", "No sacrament records found")
        
        # Additional Information (Skills, Medical Conditions, Emergency Contacts)
        additional_items = []
        
        # Skills
        if parishioner.skills_rel:
            skills = [skill.name for skill in parishioner.skills_rel]
            additional_items.append({"label": "Skills", "value": ", ".join(skills)})
        
        # Languages
        if hasattr(parishioner, 'languages_rel') and parishioner.languages_rel:
            languages = [lang.name for lang in parishioner.languages_rel]
            additional_items.append({"label": "Languages", "value": ", ".join(languages)})
        
        # Medical Conditions
        if parishioner.medical_conditions_rel:
            conditions = [cond.condition for cond in parishioner.medical_conditions_rel]
            additional_items.append({"label": "Medical Conditions", "value": ", ".join(conditions)})
        
        # Emergency Contacts
        emergency_contacts_html = ""
        if parishioner.emergency_contacts_rel:
            for contact in parishioner.emergency_contacts_rel:
                contact_html = cls._format_detail_section([
                    {"label": "Name", "value": contact.name},
                    {"label": "Relationship", "value": contact.relationship},
                    {"label": "Primary Phone", "value": contact.primary_phone},
                    {"label": "Alternative Phone", "value": contact.alternative_phone},
                ])
                emergency_contacts_html += f"<div class='detail-group'><strong>Emergency Contact</strong><div class='detail-value'>{contact_html}</div></div>"
            
            additional_items.append({"label": "Emergency Contacts", "value": emergency_contacts_html})
        
        if not additional_items:
            additional_items.append({"label": "Additional Information", "value": "No additional information available"})
            
        additional_info = cls._format_detail_section(additional_items)
        
        # Replace placeholders in the template
        html = verification_page_template
        html = html.replace("{{PERSONAL_INFO}}", personal_info)
        html = html.replace("{{CONTACT_INFO}}", contact_info)
        html = html.replace("{{FAMILY_INFO}}", family_info)
        html = html.replace("{{OCCUPATION_INFO}}", occupation_info)
        html = html.replace("{{CHURCH_INFO}}", church_info)
        html = html.replace("{{SACRAMENTS_INFO}}", sacraments_html)
        html = html.replace("{{ADDITIONAL_INFO}}", additional_info)
        html = html.replace("{{ACCESS_CODE}}", access_code)
        html = html.replace("{{CURRENT_YEAR}}", str(datetime.now().year))
        
        return {
            "html": html,
            "access_code": access_code
        }