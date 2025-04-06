from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
import logging

from pydantic import BaseModel, EmailStr
from app.core.config import settings
from app.services.email.template import WelcomeEmailTemplate, EmailTemplateContext
from app.services.email.template.church_id_confirmation import ChurchIDConfirmationTemplate, ChurchIDEmailContext
from app.services.email.template.verification_confirmation import VerificationConfirmationContext, VerificationConfirmationTemplate
from app.services.email.template.verify_parishioner_details import VerificationMessageContext, VerificationMessageTemplate

# Set up logging
logger = logging.getLogger(__name__)


class EmailService:
    def __init__(self):
        self.mail_config = ConnectionConfig(
            MAIL_USERNAME=settings.SMTP_USER,
            MAIL_PASSWORD=settings.SMTP_PASSWORD,
            MAIL_FROM=settings.EMAILS_FROM_EMAIL,
            MAIL_PORT=465,  # Using Gmail's SSL port instead of TLS
            MAIL_SERVER="smtp.gmail.com",
            MAIL_STARTTLS=False,  # Not needed with SSL
            MAIL_SSL_TLS=True,  # Using SSL instead of STARTTLS
            USE_CREDENTIALS=True,
            VALIDATE_CERTS=True
        )

        self.fast_mail = FastMail(self.mail_config)
        self._verify_settings()

    def _verify_settings(self) -> None:
        """Verify that all required SMTP settings are configured."""
        required_settings = {
            'SMTP_USER': settings.SMTP_USER,
            'SMTP_PASSWORD': 'CONFIGURED' if settings.SMTP_PASSWORD else None,
            'EMAILS_FROM_EMAIL': settings.EMAILS_FROM_EMAIL
        }
        
        missing_settings = [k for k, v in required_settings.items() if not v]
        if missing_settings:
            logger.error(f"Missing required email settings: {', '.join(missing_settings)}")

    
    async def send_welcome_email(
        self,
        email: str,
        full_name: str,
        temp_password: str
    ) -> bool:
        try:
            # Create context
            context = EmailTemplateContext(
                email=email,
                full_name=full_name,
                temp_password=temp_password
            )
            
            # Render template
            template = WelcomeEmailTemplate.render(context)
            
            # Create message
            message = MessageSchema(
                subject=template["subject"],
                recipients=[email],
                body=template["html_content"],
                subtype="html"
            )
            
            # Send email
            await self.fast_mail.send_message(message)
            logger.info(f"Welcome email sent to {email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send welcome email to {email}: {str(e)}")
            return False


    async def send_church_id_confirmation(
            self, 
            email: str, 
            parishioner_name: str, 
            system_id: str,
            old_church_id:str, 
            new_church_id: str
        ) -> bool:
        try:
            logger.info(f"sending conf to {email}")
            context = ChurchIDEmailContext(
            email=email,
            full_name=parishioner_name,  # Required by base class
            parishioner_name=parishioner_name,
            system_id=system_id,
            old_church_id=old_church_id,
            new_church_id=new_church_id,
            temp_password=None  # Required by base class but not used
            )
              # Render template
            template = ChurchIDConfirmationTemplate.render(context)
            
            # Create message
            message = MessageSchema(
                subject=template["subject"],
                recipients=[email],
                body=template["html_content"],
                subtype="html"
            )
            
            # Send email
            await self.fast_mail.send_message(message)
            logger.info(f"Church ID confirmation email sent to {email}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to send church ID confirmation email to {email}: {str(e)}")
            return False
        


    async def send_verification_message(
        self,
        email: str,
        parishioner_name: str,
        verification_link: str,
        access_code: str
    ) -> bool:
        try:
            # Create context
            context = VerificationMessageContext(
                email=email,
                full_name=parishioner_name,  # Required by base class
                parishioner_name=parishioner_name,
                verification_link=verification_link,
                access_code=access_code,
                temp_password=None  # Required by base class but not used
            )
            
            # Render template
            template = VerificationMessageTemplate.render(context)
            
            # Create message
            message = MessageSchema(
                subject=template["subject"],
                recipients=[email],
                body=template["html_content"],
                subtype="html"
            )
            
            # Send email
            await self.fast_mail.send_message(message)
            logger.info(f"Verification message email sent to {email}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to send verification message email to {email}: {str(e)}")
            return False


    async def send_verification_confirmation(
        self,
        email: str,
        parishioner_name: str
    ) -> bool:
        try:
            # Create context
            context = VerificationConfirmationContext(
                email=email,
                full_name=parishioner_name,  # Required by base class
                parishioner_name=parishioner_name,
                temp_password=None  # Required by base class but not used
            )
            
            # Render template
            template = VerificationConfirmationTemplate.render(context)
            
            # Create message
            message = MessageSchema(
                subject=template["subject"],
                recipients=[email],
                body=template["html_content"],
                subtype="html"
            )
            
            # Send email
            await self.fast_mail.send_message(message)
            logger.info(f"Verification confirmation email sent to {email}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to send verification confirmation email to {email}: {str(e)}")
            return False
        
# Create a singleton instance
email_service = EmailService()
