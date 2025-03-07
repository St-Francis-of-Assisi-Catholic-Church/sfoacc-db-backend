from typing import Dict
from .base import BaseEmailTemplate, EmailTemplateContext
from .utils import create_info_box, sanitize_html
from app.core.config import settings

class VerificationMessageContext(EmailTemplateContext):
    """Context for verification message emails"""
    parishioner_name: str
    verification_link: str
    access_code: str

class VerificationMessageTemplate(BaseEmailTemplate):
    @classmethod
    def render(cls, context: VerificationMessageContext) -> Dict[str, str]:
        """Render verification message email template"""
        
        # Create access instructions box
        access_instructions = f"""
            <p>To view your complete details, you will need to enter your date of birth as the access code:</p>
            <p><strong>Access Code Format:</strong> DDMMYYYY (Day Month Year)</p>
            <p>For example, if you were born on January 15, 1980, you would enter: 15011980</p>
            <p>This ensures your information remains private and accessible only to you.</p>
        """
        info_box = create_info_box(access_instructions, "Accessing Your Information")
        
        content = f"""
            <h1>Verify Your Parishioner Details</h1>
            
            <p>Dear {sanitize_html(context.parishioner_name)},</p>
            
            <p>As part of our ongoing efforts to maintain accurate records, we kindly request 
            that you verify your information in our parish database.</p>
            
            {info_box}
            
            <p>Please review all your details carefully. If any information is incorrect or 
            has changed, please visit the church information desk to update your records.</p>
            
            {cls.create_button("View Your Details", context.verification_link)}
            
            <p>If you cannot access the button above, please copy and paste this link into your browser:</p>
            <p>{sanitize_html(context.verification_link)}</p>
            
            <p>This link will expire in 48 hours for security purposes.</p>
            
            <p>Thank you for helping us maintain accurate parish records.</p>
            
            <p>God bless you,<br>SFOACC Church Administration</p>
        """
        
        return {
            "subject": "Please Verify Your Parish Records",
            "html_content": cls.wrap_content(content)
        }