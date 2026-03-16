from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
import logging
from typing import Dict, Any, List, Optional

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
        
    async def send_custom_message(
        self,
        to_email: str,
        parishioner_name: str,
        custom_message: str,
        subject: str = "Message from Your Parish",
        **ctx: Any,
    ) -> bool:
        """Send a custom freeform message to a single recipient."""
        try:
            # Format any {variable} placeholders in the message
            context = {"parishioner_name": parishioner_name, **ctx}
            try:
                formatted = custom_message.format(**context)
            except KeyError:
                formatted = custom_message

            html_body = (
                f"<p>Dear {parishioner_name},</p>"
                f"<p>{formatted.replace(chr(10), '<br/>')}</p>"
                f"<p style='color:#888;font-size:12px'>— {settings.CHURCH_NAME}</p>"
            )
            message = MessageSchema(
                subject=subject,
                recipients=[to_email],
                body=html_body,
                subtype="html",
            )
            await self.fast_mail.send_message(message)
            logger.info(f"Custom email sent to {to_email}")
            return True
        except Exception as e:
            logger.error(f"Failed to send custom email to {to_email}: {str(e)}")
            return False

    async def send_from_template(
        self,
        template_name: str,
        to_emails: List[str],
        context: Dict[str, Any],
    ) -> bool:
        """Send a bulk-messaging template as email.

        Uses the SMS template content (formatted with *context*) as the email body,
        so both channels share the same template registry.
        """
        try:
            from app.services.sms.service import sms_service

            template = sms_service.get_template(template_name)
            if not template:
                logger.error(f"Email template '{template_name}' not found")
                return False

            try:
                body_text = template.content.format(**context)
            except KeyError as e:
                logger.error(f"Missing template variable: {e}")
                body_text = template.content

            parishioner_name = context.get("parishioner_name", "")
            html_body = (
                f"<p>Dear {parishioner_name},</p>"
                f"<p>{body_text}</p>"
                f"<p style='color:#888;font-size:12px'>— {settings.CHURCH_NAME}</p>"
            )
            subject = template.name
            message = MessageSchema(
                subject=subject,
                recipients=to_emails,
                body=html_body,
                subtype="html",
            )
            await self.fast_mail.send_message(message)
            logger.info(f"Template email '{template_name}' sent to {to_emails}")
            return True
        except Exception as e:
            logger.error(f"Failed to send template email '{template_name}': {str(e)}")
            return False

    async def send_account_creation_sms_fallback(
        self,
        phone: str,
        full_name: str,
        temp_password: str,
    ) -> None:
        """Placeholder — SMS is handled by sms_service directly."""
        pass

    async def send_otp_code(self, email: str, full_name: str, code: str) -> bool:
        """Send a login OTP code via email."""
        try:
            message = MessageSchema(
                subject="Your SFOACC Login Code",
                recipients=[email],
                body=(
                    f"<p>Hello {full_name},</p>"
                    f"<p>Your one-time login code is:</p>"
                    f"<h2 style='letter-spacing:8px;font-family:monospace'>{code}</h2>"
                    f"<p>This code expires in 10 minutes. Do not share it with anyone.</p>"
                    f"<p>If you did not request this, please contact your administrator.</p>"
                ),
                subtype="html",
            )
            await self.fast_mail.send_message(message)
            logger.info(f"OTP email sent to {email}")
            return True
        except Exception as e:
            logger.error(f"Failed to send OTP email to {email}: {str(e)}")
            return False


# Create a singleton instance
email_service = EmailService()
