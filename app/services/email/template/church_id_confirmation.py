from typing import Dict
from .base import BaseEmailTemplate, EmailTemplateContext
from .utils import create_info_box, sanitize_html
from app.core.config import settings

class ChurchIDEmailContext(EmailTemplateContext):
    """Context for church ID confirmation emails"""
    parishioner_name: str
    old_church_id: str
    new_church_id: str
    system_id: str

class ChurchIDConfirmationTemplate(BaseEmailTemplate):
    @classmethod
    def render(cls, context: ChurchIDEmailContext) -> Dict[str, str]:
        """Render church ID confirmation email template"""
        login_url = f"{settings.FRONTEND_HOST}"
        
        # Create church ID details box
        id_details = f"""
            <p><strong>system ID:</strong> {sanitize_html(context.system_id)}</p>
             <p><strong>old Church ID:</strong> {sanitize_html(context.old_church_id)}</p>
            <p><strong>New Church ID:</strong> {sanitize_html(context.new_church_id)}</p>

        """
        info_box = create_info_box(id_details, "Your Church ID Details")
        
        content = f"""
            <h1>Your Church ID Has Been Generated</h1>
            
            <p>Dear {sanitize_html(context.parishioner_name)},</p>
            
            <p>We're pleased to inform you that your church ID has been successfully generated in our database system.
            Here are your church ID details:</p>
            
            {info_box}
            
            <p>This ID will be used for all official church activities and communications. 
            Please keep this information for your records.</p>
            
            {cls.create_button("Access Your Account", login_url)}
            
            <p>If you believe there's an error with your church ID or need any assistance, 
            please contact the church administration office.</p>
            
            <p>God bless you,<br>SFOACC Church Administration</p>
        """
        
        return {
            "subject": "Your SFOACC Church ID Has Been Generated",
            "html_content": cls.wrap_content(content)
        }