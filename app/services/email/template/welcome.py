from typing import Dict
from .base import BaseEmailTemplate, EmailTemplateContext
from .utils import create_info_box, sanitize_html
from app.core.config import settings

class WelcomeEmailTemplate(BaseEmailTemplate):
    @classmethod
    def render(cls, context: EmailTemplateContext) -> Dict[str, str]:
        """Render welcome email template"""
        login_url = f"{settings.FRONTEND_HOST}"
        
        # Create account details box
        account_details = f"""
            <p><strong>Username:</strong> {sanitize_html(context.email)}</p>
            <p><strong>Temporary Password:</strong> {sanitize_html(context.temp_password)}</p>
        """
        info_box = create_info_box(account_details, "Your Account Details")
        
        content = f"""
            <h1>Welcome to SFOACC DB Platform!</h1>
            
            <p>Hello {sanitize_html(context.full_name)},</p>
            
            <p>Welcome aboard! Your account has been successfully created. 
            Here are your login details:</p>
            
            {info_box}
            
            <p>For security reasons, please change your password upon first login.</p>
            
            {cls.create_button("Login to Your Account", login_url)}
    
            <p>or click this link {login_url} to access the application </p>
            
            <p>If you need any assistance, don't hesitate to contact our support team.</p>
            
            <p>Best regards,<br>The Church Database Project Team</p>
        """
        
        return {
            "subject": "Welcome to Our Platform! 🎉",
            "html_content": cls.wrap_content(content)
        }