from typing import Dict
from .utils import BaseEmailTemplate, EmailTemplateContext
from .utils import wrap_html_content, create_button

class PasswordResetTemplate(BaseEmailTemplate):
    @staticmethod
    def render(context: EmailTemplateContext) -> Dict[str, str]:
        reset_url = f"https://your-domain.com/reset-password?token={context.reset_token}"
        
        content = f"""
            <h1>Password Reset Request</h1>
            
            <p>Hello {context.full_name},</p>
            
            <p>We received a request to reset your password for your SFOACC DB Platform account. 
            If you didn't make this request, you can safely ignore this email.</p>
            
            <p>To reset your password, click the button below. This link will expire in 24 hours:</p>
            
            {create_button("Reset Your Password", reset_url)}
            
            <div class="info-box">
                <p><strong>Note:</strong> For security reasons, this link can only be used once. 
                If you need to reset your password again, please request a new reset link.</p>
            </div>
            
            <p>If you're having trouble clicking the button, copy and paste this URL into your browser:</p>
            <p style="word-break: break-all; font-size: 14px; color: #718096;">{reset_url}</p>
            
            <p>Best regards,<br>The SFOACC Team</p>
        """
        
        return {
            "subject": "Password Reset Request - SFOACC DB Platform",
            "html_content": wrap_html_content(content)
        }