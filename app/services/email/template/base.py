from typing import Dict, Optional
from pydantic import BaseModel, EmailStr
from datetime import datetime
from .styles import EmailStyles

class EmailTemplateContext(BaseModel):
    """Base context for all email templates"""
    email: EmailStr
    full_name: str
    temp_password: Optional[str] = None
    reset_token: Optional[str] = None
    verification_token: Optional[str] = None

class BaseEmailTemplate:
    """Base class for all email templates"""
    
    @staticmethod
    def wrap_content(content: str) -> str:
        """Wraps content with common header/footer"""
        current_year = datetime.now().year
        
        return f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <style>
                    {EmailStyles.get_base_styles()}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                         <img src="https://res.cloudinary.com/jondexter/image/upload/v1735725861/sfoacc-logo_ncynib.png" alt="SFOACC Logo">
                    </div>
                    <div class="content">
                        {content}
                    </div>
                    <div class="footer">
                        <p>&copy; {current_year} SFOACC DB Platform. All rights reserved.</p>
                    </div>
                </div>
            </body>
            </html>
        """

    @classmethod
    def render(cls, context: EmailTemplateContext) -> Dict[str, str]:
        """Render the email template"""
        raise NotImplementedError("Subclasses must implement render()")

    @staticmethod
    def create_button(text: str, url: str) -> str:
        """Creates a styled button"""
        return f'<a href="{url}" class="button">{text}</a>'