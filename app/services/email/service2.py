import logging
from typing import Dict, Optional, List, Any
from fastapi_mail import ConnectionConfig, FastMail, MessageSchema
from pydantic import BaseModel, EmailStr
from datetime import datetime
from app.core.config import settings
from app.services.email.template.styles import EmailStyles


# Set up logger
logger = logging.getLogger("email_service")

class EmailTemplate(BaseModel):
    name: str
    subject: str
    content_generator: Any  # Function that generates HTML content

class EmailService:
    def __init__(self):
        self.mail_config = ConnectionConfig(
            MAIL_USERNAME=settings.SMTP_USER,
            MAIL_PASSWORD=settings.SMTP_PASSWORD,
            MAIL_FROM=settings.EMAILS_FROM_EMAIL,
            MAIL_PORT=465,  # Using Gmail's SSL port
            MAIL_SERVER="smtp.gmail.com",
            MAIL_STARTTLS=False,  # Not needed with SSL
            MAIL_SSL_TLS=True,  # Using SSL
            USE_CREDENTIALS=True,
            VALIDATE_CERTS=True
        )

        self.fast_mail = FastMail(self.mail_config)
        self._verify_settings()
        self.templates = self._initialize_templates()
        logger.info("Email Service initialized with FastMail server: %s", self.mail_config.MAIL_SERVER)

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
            
    def _wrap_content(self, content: str) -> str:
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

                        <p>Warm regards,<br> The Church Database Platform Team</p>
                    </div>
                    <div class="footer">
                        <p>&copy; {current_year} SFOACC DB Platform. All rights reserved.</p>
                    </div>
                </div>
            </body>
            </html>
        """
    
    def _create_button(self, text: str, url: str) -> str:
        """Creates a styled button"""
        return f'<a href="{url}" class="button">{text}</a>'
    
    def _create_info_box(self, content: str, title: str = "") -> str:
        """Creates an info box with optional title"""
        title_html = f"<h3>{title}</h3>" if title else ""
        return f"""
            <div class="info-box">
                {title_html}
                {content}
            </div>
        """
    
    def _initialize_templates(self) -> Dict[str, EmailTemplate]:
        """Initialize email templates."""
        return {
            # Main welcome message
            "main_welcome_message": EmailTemplate(
                name="Welcome Message",
                subject="Welcome to {church_name}",
                content_generator=self._generate_welcome_content
            ),
            
            # Church ID generation message
            "church_id_generation_message": EmailTemplate(
                name="ID Generation Message",
                subject="Your Church ID Has Been Generated",
                content_generator=self._generate_id_generation_content
            ),
            
            # Parishioner onboarding welcome
            "parishioner_onboarding_welcome_message": EmailTemplate(
                name="Onboarding Welcome",
                subject="Welcome to {church_name}",
                content_generator=self._generate_onboarding_welcome_content
            ),
            
            # Record verification message
            "record_verification_message": EmailTemplate(
                name="Record Verification",
                subject="Please Verify Your Church Information",
                content_generator=self._generate_verification_content
            ),
            
            # Confirm record verification message
            "record_verification_confirmation_message": EmailTemplate(
                name="Verification Confirmation",
                subject="Your Information Has Been Verified",
                content_generator=self._generate_verification_confirmation_content
            ),
            
            # Event reminder
            "event_reminder": EmailTemplate(
                name="Event Reminder",
                subject="{event_name} Reminder",
                content_generator=self._generate_event_reminder_content
            ),
            "custom_message": EmailTemplate(
                name="Custom Message",
                subject="{subject}",  # The subject will be provided in the context
                content_generator=self._generate_custom_content
            )
        }
    
    # Content generators for different templates
    def _generate_welcome_content(self, context: Dict[str, str]) -> str:
        login_url = f"{settings.FRONTEND_HOST}"
        
        content = f"""
            <h1>Welcome to {context.get('church_name', 'our church')}!</h1>
            
            <p>Hello {context.get('parishioner_name', '')},</p>
            
            <p>Welcome to our community! We're blessed to have you join us.</p>
            
            <p>If you need any assistance, please contact us at {context.get('church_contact', '')}.</p>
            
            <p>God bless you!</p>
        """
        
        return content
    
    def _generate_id_generation_content(self, context: Dict[str, str]) -> str:
        church_id = context.get('new_church_id', '')
        
        # Create account details box
        id_details = f"""
            <p><strong>Church ID:</strong> {church_id}</p>
        """
        info_box = self._create_info_box(id_details, "Your Church ID Details")
        
        content = f"""
            <h1>Your Church ID Has Been Generated</h1>
            
            <p>Hello {context.get('parishioner_name', '')},</p>
            
            <p>We're pleased to inform you that your church ID has been generated successfully.</p>
            
            {info_box}
            
            <p>Please keep this information for your records.</p>
            
            <p>If you have any questions, please contact us at {context.get('church_contact', '')}.</p>
            
            <p>God bless you!</p>
        """
        
        return content
    
    def _generate_onboarding_welcome_content(self, context: Dict[str, str]) -> str:
        content = f"""
            <h1>Welcome to {context.get('church_name', 'our church')}!</h1>
            
            <p>Dear {context.get('parishioner_name', '')},</p>
            
            <p>Welcome to our community! Your church records are being created, and we will 
            update you once the process is complete.</p>
            
            <p>If you have any questions or need assistance, please contact us at 
            {context.get('church_contact', '')}.</p>
            
            <p>God bless you!</p>
        """
        
        return content
    
    def _generate_verification_content(self, context: Dict[str, str]) -> str:
        verification_link = context.get('verification_link', '#')
        access_code = context.get('access_code', '')
        
        # Create verification details box
        verification_details = f"""
            <p><strong>Access Code:</strong> Your date of birth in the format DDMMYYYY</p>
            <p><strong>Note:</strong> This link expires in 48 hours</p>
        """
        info_box = self._create_info_box(verification_details, "Verification Details")
        
        content = f"""
            <h1>Please Verify Your Information</h1>
            
            <p>Hi {context.get('parishioner_name', '')},</p>
            
            <p>We need to verify your information in our church records. Please click 
            the button below to complete the verification process:</p>
            
            {self._create_button("Verify My Information", verification_link)}
            
            <p>Or use this link: <a href="{verification_link}">{verification_link}</a></p>
            
            {info_box}
            
            <p>If you didn't request this verification, please ignore this email or contact 
            your parish office.</p>
            
            <p>God bless you!</p>
        """
        
        return content
    
    def _generate_verification_confirmation_content(self, context: Dict[str, str]) -> str:
        content = f"""
            <h1>Your Information Has Been Verified</h1>
            
            <p>Hi {context.get('parishioner_name', '')},</p>
            
            <p>Thank you for verifying your church records. Your information has been 
            successfully confirmed in our system.</p>
            
            <p>If you have any questions or need to update your information in the future, 
            please contact us at {context.get('church_contact', '')}.</p>
            
            <p>God bless you!</p>
        """
        
        return content
    
    def _generate_event_reminder_content(self, context: Dict[str, str]) -> str:
        event_details = f"""
            <p><strong>Event:</strong> {context.get('event_name', '')}</p>
            <p><strong>Date:</strong> {context.get('event_date', '')}</p>
            <p><strong>Time:</strong> {context.get('event_time', '')}</p>
        """
        info_box = self._create_info_box(event_details, "Event Details")
        
        content = f"""
            <h1>{context.get('event_name', 'Event')} Reminder</h1>
            
            <p>Dear {context.get('parishioner_name', '')},</p>
            
            <p>This is a reminder about the upcoming event:</p>
            
            {info_box}
            
            <p>We look forward to seeing you there!</p>
            
            <p>God bless you!</p>
        """
        
        return content

    def _generate_custom_content(self, context: Dict[str, str]) -> str:
        # Use the custom message template directly from the context
        custom_message = context.get('custom_message', '')
        
        # Format the custom message with variables from context
        try:
            formatted_message = custom_message.format(**context)
        except KeyError as e:
            logger.warning(f"Missing variable in custom message: {e}")
            formatted_message = custom_message  # Use unformatted if formatting fails
        
        # Return the formatted message with proper HTML structure
        content = f"""
            <h1>{context.get('subject', 'Important Message from Your Parish')}</h1>
            
            <p>Dear {context.get('parishioner_name', '')},</p>
            
            <div class="custom-message">
                {formatted_message}
            </div>
            
            <p>God bless you!</p>
        """
        
        return content

    async def send_email(self, 
                 to_emails: List[str], 
                 subject: str,
                 html_content: str) -> Dict[str, Any]:
        """Send email to one or more recipients."""
        if not to_emails:
            return {"success": False, "message": "No recipients provided"}
        
        try:
            logger.info(f"Sending email to {len(to_emails)} recipients")
            
            # Wrap content with the common template
            wrapped_html = self._wrap_content(html_content)
            
            # Create message
            message = MessageSchema(
                subject=subject,
                recipients=to_emails,
                body=wrapped_html,
                subtype="html"  # Use string instead of enum
            )
            
            # Send email
            await self.fast_mail.send_message(message)
            
            logger.info("Email sent successfully")
            return {
                "success": True, 
                "message": "Email sent successfully",
                "recipients_count": len(to_emails)
            }
        except Exception as e:
            logger.error(f"Email sending failed: {str(e)}")
            return {
                "success": False,
                "message": f"Email sending failed: {str(e)}",
                "error": str(e)
            }
    
    def get_template(self, template_name: str) -> Optional[EmailTemplate]:
        """Get email template by name."""
        return self.templates.get(template_name)
    
    async def send_from_template(self, 
                          template_name: str, 
                          to_emails: List[str], 
                          context: Dict[str, str]) -> Dict[str, Any]:
        """Send email using a predefined template with context variables."""
        template = self.get_template(template_name)
        if not template:
            logger.error(f"Template not found: {template_name}")
            return {"success": False, "message": f"Template '{template_name}' not found"}
        
        try:
            # Format subject with context variables
            subject = template.subject.format(**context)
            
            # Generate HTML content using the template's content generator
            html_content = template.content_generator(context)
            
            return await self.send_email(to_emails, subject, html_content)
        except KeyError as e:
            logger.error(f"Missing context variable: {str(e)}")
            return {"success": False, "message": f"Missing context variable: {str(e)}"}
    
    # Helper method to create standard context
    def _create_base_context(self, parishioner_name: str) -> Dict[str, str]:
        return {
            "parishioner_name": parishioner_name,
            "church_name": settings.CHURCH_NAME,
            "church_contact": settings.CHURCH_CONTACT
        }
    
    # Simplified template methods using the base context - all async now
    async def send_verification_message(self, 
                                email: str, 
                                parishioner_name: str,
                                verification_link: str,
                                access_code: str = "") -> Dict[str, Any]:
        """Send verification email to a parishioner."""
        try:
            context = self._create_base_context(parishioner_name)
            context["verification_link"] = verification_link
            context["access_code"] = access_code
            result = await self.send_from_template("record_verification_message", [email], context)
            return result
        except Exception as e:
            logger.error(f"Failed to send verification message email to {email}: {str(e)}")
            return {"success": False, "message": f"Failed to send email: {str(e)}"}
    
    async def send_main_welcome_message(self, 
                                email: str, 
                                parishioner_name: str) -> Dict[str, Any]:
        """Send welcome email to a new parishioner."""
        try:
            context = self._create_base_context(parishioner_name)
            result = await self.send_from_template("main_welcome_message", [email], context)
            return result
        except Exception as e:
            logger.error(f"Failed to send welcome email to {email}: {str(e)}")
            return {"success": False, "message": f"Failed to send email: {str(e)}"}
    
    async def send_parishioner_onboarding_welcome_message(self, 
                                                  email: str, 
                                                  parishioner_name: str) -> Dict[str, Any]:
        """Send onboarding welcome email to a new parishioner."""
        try:
            context = self._create_base_context(parishioner_name)
            result = await self.send_from_template("parishioner_onboarding_welcome_message", [email], context)
            return result
        except Exception as e:
            logger.error(f"Failed to send onboarding email to {email}: {str(e)}")
            return {"success": False, "message": f"Failed to send email: {str(e)}"}
    
    async def send_church_id_generation_message(self, 
                                       email: str, 
                                       parishioner_name: str,
                                       new_church_id: str) -> Dict[str, Any]:
        """Send church ID generation confirmation email."""
        try:
            context = self._create_base_context(parishioner_name)
            context["new_church_id"] = new_church_id
            result = await self.send_from_template("church_id_generation_message", [email], context)
            return result
        except Exception as e:
            logger.error(f"Failed to send church ID email to {email}: {str(e)}")
            return {"success": False, "message": f"Failed to send email: {str(e)}"}
    
    async def send_record_verification_confirmation_message(self, 
                                                   email: str, 
                                                   parishioner_name: str) -> Dict[str, Any]:
        """Send verification confirmation email."""
        try:
            context = self._create_base_context(parishioner_name)
            result = await self.send_from_template("record_verification_confirmation_message", [email], context)
            return result
        except Exception as e:
            logger.error(f"Failed to send verification confirmation email to {email}: {str(e)}")
            return {"success": False, "message": f"Failed to send email: {str(e)}"}
    
    async def send_event_reminder(self, 
                          email: str, 
                          parishioner_name: str,
                          event_name: str, 
                          event_date: str,
                          event_time: str) -> Dict[str, Any]:
        """Send event reminder email."""
        try:
            context = self._create_base_context(parishioner_name)
            context.update({
                "event_name": event_name,
                "event_date": event_date,
                "event_time": event_time
            })
            result = await self.send_from_template("event_reminder", [email], context)
            return result
        except Exception as e:
            logger.error(f"Failed to send event reminder email to {email}: {str(e)}")
            return {"success": False, "message": f"Failed to send email: {str(e)}"}
    
    async def send_custom_message(self,
                       to_email: str,
                       parishioner_name: str,
                       custom_message: str,
                       subject: str = "Important Message from Your Parish",
                       **extra_context) -> Dict[str, Any]:
        """Send a custom email with dynamic variables."""
        try:
            # # Log more details for debugging
            # logger.info(f"Sending custom email to {to_email}")
            # logger.info(f"Subject: {subject}")
            # logger.info(f"Message content length: {len(custom_message)}")
            
            # # Create base context
            # context = self._create_base_context(parishioner_name)
            
            # # Add custom message and subject to context
            # context["custom_message"] = custom_message
            # context["subject"] = subject
            
            # Add any extra context variables
            # context.update(extra_context)
            
            # result = await self.send_from_template("custom_message", [to_email], context)
            # return result
            logger.info(f"Sending direct custom email to {to_email}")
        
            # Format the content directly
            formatted_html = f"""
                <h1>{subject}</h1>
                
                <p>Dear {parishioner_name},</p>
                
                <div class="custom-message">
                    {custom_message}
                </div>
                
                <p>God bless you!</p>
            """
            
            # Send without using templates
            result = await self.send_email([to_email], subject, formatted_html)
            logger.info(f"Direct custom email result: {result}")
            return result
        except Exception as e:
            logger.error(f"Failed to send custom message email to {to_email}: {str(e)}")
            return {"success": False, "message": f"Failed to send email: {str(e)}"}

# Create a singleton instance
email_service = EmailService()