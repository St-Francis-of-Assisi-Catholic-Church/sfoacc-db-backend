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
            <h1>Welcome to the {settings.CHURCH_NAME} Admin Portal!</h1>

            <p>Hello {sanitize_html(context.full_name)},</p>

            <p>Your admin account has been created. Here are your login details:</p>

            {info_box}

            <p>For security reasons, please change your password upon first login.</p>

            {cls.create_button("Login to Your Account", login_url)}

            <p>Or copy this link into your browser: {login_url}</p>

            <p>If you need any assistance, contact your administrator.</p>

            <p>Best regards,<br>{settings.CHURCH_NAME}</p>
        """

        return {
            "subject": f"Your {settings.CHURCH_NAME} admin account is ready",
            "html_content": cls.wrap_content(content)
        }