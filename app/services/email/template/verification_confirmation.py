from typing import Dict
from .base import BaseEmailTemplate, EmailTemplateContext
from .utils import create_info_box, sanitize_html
from app.core.config import settings

class VerificationConfirmationContext(EmailTemplateContext):
    """Context for verification confirmation emails"""
    parishioner_name: str

class VerificationConfirmationTemplate(BaseEmailTemplate):
    @classmethod
    def render(cls, context: VerificationConfirmationContext) -> Dict[str, str]:
        """Render verification confirmation email template"""
        church_url = f"{settings.FRONTEND_HOST}"
        
        # Create confirmation details box
        confirmation_details = f"""
            <p>Your church records have been successfully verified.</p>
            <p>Verification Status: <strong>VERIFIED</strong></p>
            <p>Date: {cls._get_formatted_date()}</p>
        """
        info_box = create_info_box(confirmation_details, "Verification Confirmation")
        
        content = f"""
            <h1>Church Records Verification Confirmed</h1>
            
            <p>Dear {sanitize_html(context.parishioner_name)},</p>
            
            <p>Thank you for confirming your church records. Your information has been 
            successfully verified in our system.</p>
            
            {info_box}
            
            <p>Having up-to-date and verified information helps us serve you better 
            and ensures effective communication within our church community.</p>
            
            <p>If you need to update any of your information in the future, 
            please contact the church office or visit us at the info desk after Mass on Sundays.</p>
            
            <p>God bless you,<br>SFOACC Church Administration</p>
        """
        
        return {
            "subject": "Church Records Verification Confirmed",
            "html_content": cls.wrap_content(content)
        }
        
    @staticmethod
    def _get_formatted_date():
        """Get current date formatted for display"""
        from datetime import datetime
        return datetime.now().strftime("%d %B, %Y")