from datetime import datetime
from typing import Dict, Any, List
from app.models.parishioner import (
    Parishioner as ParishionerModel, Occupation, FamilyInfo,
    EmergencyContact, MedicalCondition, Skill, Child
)
from app.models.society import society_members
from app.models.common import VerificationStatus
from sqlalchemy import select
from app.core.database import db
from .page_template import verification_page_template

class VerificationPageGenerator:
    """Service to generate HTML verification pages for parishioners"""
    
    @staticmethod
    def _format_detail_item(label: str, value: Any) -> str:
        """Format a single detail item with label and value"""
        if value is None:
            value = "N/A"
        
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
    def generate_page(cls, parishioner: ParishionerModel, db_session=None, verification_id=None) -> Dict[str, str]:
        """
        Generate HTML verification page for a parishioner
        
        Args:
            parishioner: The parishioner model instance
            db_session: Optional SQLAlchemy session for querying association tables
            verification_id: Optional verification ID for the confirmation button
        
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
        occupation_items = []
        if parishioner.occupation_rel:
            occupation = parishioner.occupation_rel
            occupation_items = [
                {"label": "Role", "value": occupation.role},
                {"label": "Employer", "value": occupation.employer},
            ]
        else:
            # Just add N/A for occupation
            occupation_items = [{"label": "Occupation", "value": None}]
            
        occupation_info = cls._format_detail_section(occupation_items)
        
        # Get place of worship and church community names
        place_of_worship_name = None
        church_community_name = None
        
        if hasattr(parishioner, 'place_of_worship') and parishioner.place_of_worship:
            place_of_worship_name = parishioner.place_of_worship.name
        
        if hasattr(parishioner, 'church_community') and parishioner.church_community:
            church_community_name = parishioner.church_community.name
        
        # Church Information
        church_info = cls._format_detail_section([
            {"label": "Old Church ID", "value": parishioner.old_church_id},
            {"label": "New Church ID", "value": parishioner.new_church_id},
            {"label": "Place of Worship", "value": place_of_worship_name},
            {"label": "Church Community", "value": church_community_name},
            {"label": "Membership Status", "value": parishioner.membership_status.value if parishioner.membership_status else None},
            {"label": "Verification Status", "value": parishioner.verification_status.value if parishioner.verification_status else None},
        ])
        
        # Collect society membership details from the association table directly
        society_membership_details = {}
        if db_session and hasattr(parishioner, 'id'):
            try:
                # Query the society_members table for this parishioner
                stmt = select(society_members).where(society_members.c.parishioner_id == parishioner.id)
                result = db_session.execute(stmt).fetchall()
                
                # Store details indexed by society_id
                for row in result:
                    society_id = row.society_id
                    join_date = row.join_date if hasattr(row, 'join_date') else None
                    membership_status = row.membership_status.value if hasattr(row, 'membership_status') and row.membership_status else None
                    
                    society_membership_details[society_id] = {
                        'join_date': join_date,
                        'membership_status': membership_status
                    }
            except Exception as e:
                # If there's an error, just continue without the details
                pass
        
        # Societies Information - Display each society with association data
        societies_items = []
        if hasattr(parishioner, 'societies') and parishioner.societies:
            for society in parishioner.societies:
                # Get basic society information
                society_name = society.name
                
                # Try to get membership status and date joined from association details
                membership_status = "N/A"
                date_joined = "N/A"
                
                # Check if we have details for this society
                if hasattr(society, 'id') and society.id in society_membership_details:
                    details = society_membership_details[society.id]
                    
                    if details['membership_status']:
                        membership_status = details['membership_status']
                    
                    if details['join_date']:
                        date_joined = details['join_date']
                        if hasattr(date_joined, 'strftime'):
                            date_joined = date_joined.strftime("%d %B, %Y")
                
                # Format the society entry
                society_info = {}
                society_info["label"] = society_name
                society_info["value"] = f"Status: {membership_status} | Joined: {date_joined}"
                
                societies_items.append(society_info)
        
        if societies_items:
            societies_html = cls._format_detail_section(societies_items)
        else:
            societies_html = cls._format_detail_item("Societies", None)
        
        # Sacraments Information - Display each sacrament as a separate item with details
        sacraments_items = []
        if hasattr(parishioner, 'sacrament_records') and parishioner.sacrament_records:
            for sacrament in parishioner.sacrament_records:
                # Get the sacrament name
                sacrament_name = "Sacrament"
                if hasattr(sacrament, 'sacrament') and sacrament.sacrament:
                    if hasattr(sacrament.sacrament, 'name'):
                        sacrament_name = sacrament.sacrament.name
                
                # Get values with N/A as default
                date_received = "N/A"
                place = "N/A"
                minister = "N/A"
                notes = "N/A"
                
                # Override with actual values if available
                if sacrament.date_received:
                    date_received = sacrament.date_received
                    if hasattr(date_received, 'strftime'):
                        date_received = date_received.strftime("%d %B, %Y")
                
                if sacrament.place:
                    place = sacrament.place
                
                if sacrament.minister:
                    minister = sacrament.minister
                
                if sacrament.notes:
                    notes = sacrament.notes
                
                # Format the value string
                value = f"Date: {date_received} | Place: {place} | Minister: {minister} | Notes: {notes}"
                
                sacrament_info = {
                    "label": sacrament_name,
                    "value": value
                }
                
                sacraments_items.append(sacrament_info)
        
        if sacraments_items:
            sacraments_html = cls._format_detail_section(sacraments_items)
        else:
            sacraments_html = cls._format_detail_item("Sacraments", None)
        
        # Additional Information (Skills, Medical Conditions, Emergency Contacts)
        additional_items = []
        
        # Skills
        if parishioner.skills_rel:
            skills = [skill.name for skill in parishioner.skills_rel]
            additional_items.append({"label": "Skills", "value": ", ".join(skills)})
        else:
            additional_items.append({"label": "Skills", "value": None})
        
        # Languages
        if hasattr(parishioner, 'languages_rel') and parishioner.languages_rel:
            languages = [lang.name for lang in parishioner.languages_rel]
            additional_items.append({"label": "Languages", "value": ", ".join(languages)})
        else:
            additional_items.append({"label": "Languages", "value": None})
        
        # Medical Conditions
        if parishioner.medical_conditions_rel:
            conditions = [cond.condition for cond in parishioner.medical_conditions_rel]
            additional_items.append({"label": "Medical Conditions", "value": ", ".join(conditions)})
        else:
            additional_items.append({"label": "Medical Conditions", "value": None})
        
        # Emergency Contacts
        if parishioner.emergency_contacts_rel:
            emergency_contacts_html = ""
            for contact in parishioner.emergency_contacts_rel:
                contact_html = cls._format_detail_section([
                    {"label": "Name", "value": contact.name},
                    {"label": "Relationship", "value": contact.relationship},
                    {"label": "Primary Phone", "value": contact.primary_phone},
                    {"label": "Alternative Phone", "value": contact.alternative_phone},
                ])
                emergency_contacts_html += f"<div class='detail-group'><strong>Emergency Contact</strong><div class='detail-value'>{contact_html}</div></div>"
            
            additional_items.append({"label": "Emergency Contacts", "value": emergency_contacts_html})
        else:
            additional_items.append({"label": "Emergency Contacts", "value": None})
            
        additional_info = cls._format_detail_section(additional_items)
        
        # Create confirmation button HTML if verification_id is provided
        confirmation_html = ""
        if verification_id:
            confirmation_html = f"""
            <div class="confirmation-section">
                <form id="confirmationForm" action="/api/v1/parishioners/verify/confirm/{verification_id}" method="POST">
                    <button type="submit" id="confirmButton" class="confirm-button">
                        I confirm that all the above information is correct
                    </button>
                </form>
                <div id="confirmationMessage" class="confirmation-message" style="display: none;">
                    Thank you for confirming your information! Your verification is complete.
                </div>
            </div>

            <script>
                document.addEventListener('DOMContentLoaded', function() {{
                    const form = document.getElementById('confirmationForm');
                    const confirmButton = document.getElementById('confirmButton');
                    const confirmationMessage = document.getElementById('confirmationMessage');
                    
                    form.addEventListener('submit', function(e) {{
                        e.preventDefault();
                        
                        confirmButton.disabled = true;
                        confirmButton.textContent = 'Processing...';
                        
                        fetch(form.action, {{
                            method: 'POST',
                            headers: {{
                                'Content-Type': 'application/json',
                            }},
                        }})
                        .then(response => response.json())
                        .then(data => {{
                            form.style.display = 'none';
                            confirmationMessage.style.display = 'block';
                        }})
                        .catch(error => {{
                            confirmButton.disabled = false;
                            confirmButton.textContent = 'I confirm that all the above information is correct';
                            alert('An error occurred. Please try again or contact the church office.');
                        }});
                    }});
                }});
            </script>
            """
        
        # Replace placeholders in the template
        html = verification_page_template
        html = html.replace("{{PERSONAL_INFO}}", personal_info)
        html = html.replace("{{CONTACT_INFO}}", contact_info)
        html = html.replace("{{FAMILY_INFO}}", family_info)
        html = html.replace("{{OCCUPATION_INFO}}", occupation_info)
        html = html.replace("{{CHURCH_INFO}}", church_info)
        html = html.replace("{{SACRAMENTS_INFO}}", sacraments_html)
        html = html.replace("{{SOCIETIES_INFO}}", societies_html)
        html = html.replace("{{ADDITIONAL_INFO}}", additional_info)
        html = html.replace("{{CONFIRMATION_BUTTON}}", confirmation_html)  # Add confirmation button
        html = html.replace("{{ACCESS_CODE}}", access_code)
        html = html.replace("{{CURRENT_YEAR}}", str(datetime.now().year))
        
        return {
            "html": html,
            "access_code": access_code
        }