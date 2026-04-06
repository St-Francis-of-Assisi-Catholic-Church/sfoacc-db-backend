import logging
import httpx
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from app.core.config import settings

# Set up logger
logger = logging.getLogger("sms_service")

_SMS_TIMEOUT = httpx.Timeout(10.0, connect=5.0)

class SMSTemplate(BaseModel):
    name: str
    content: str

class SMSService:
    def __init__(self):
        self.base_url = "https://sms.arkesel.com/api/v2/sms/send"
        self.headers = {
            "api-key": settings.ARKESEL_API_KEY,
            "Content-Type": "application/json"
        }
        self.client = httpx.Client(timeout=_SMS_TIMEOUT)
        self.templates = self._initialize_templates()
        logger.info("SMS Service initialized")
    
    
    def _initialize_templates(self) -> Dict[str, SMSTemplate]:
        """Initialize SMS templates."""
        return {
            # new admin user account creation
            "user_account_created": SMSTemplate(
                name="Admin Account Created",
                content=(
                    "Hi {full_name}, your {church_name} admin account has been created. "
                    "Username: {email}. Temp password: {temp_password}. "
                    "Login at {login_url} and change your password immediately."
                )
            ),

            # welcome message; when parishioners are created, same as for new users
            "main_welcome_message": SMSTemplate(
                name="Welcome Message",
                content="Hi {parishioner_name}, Welcome to {church_name}! We're blessed to have you join our community. For any inquiries, please contact us at {church_contact}."
            ),

            # church Id generation message
            "church_id_generation_message": SMSTemplate(
                name="New Church ID Generation Message",
                content="Hi {parishioner_name}, your new church ID : {new_church_id} has been generated successfully. Please keep this information for your records. Thank you!"
            ),

            # Parishioner onboarding welcome
            "parishioner_onboarding_welcome_message": SMSTemplate(
                name="Parishioner Onboarding Message",
                content="Dear {parishioner_name}, welcome to {church_name}! Your church records are being created. We will update you once the process is done. For any inquiries, please contact us at {church_contact}."
            ),

            # Parishioner record verification message
            "record_verification_message": SMSTemplate(
                name="Parishioner Record Verification",
                content="Hi {parishioner_name}, verify your church records: {verification_link}\nCode: your date of birth (DDMMYYYY). Expires in 48hrs."
            ),

            # confirm record verification message
            "record_verification_confirmation_message": SMSTemplate(
                name="Parishioner Record Verification Confirmation",
                content="Hi {parishioner_name}, thank you for verifying your church records. Your information has been successfully confirmed in our system. Thank you!"
            ),

            # event
            "event_reminder": SMSTemplate(
                name="event_reminder",
                content="Dear {parishioner_name}, this is a reminder about {event_name} on {event_date} at {event_time}. We look forward to seeing you there."
            ),
            
           
        }
    
    def format_phone_number(self, phone: str) -> str:
        """Format phone numbers to country code format (e.g., 233XXXXXXXXX)."""
        # Remove any spaces, dashes, or plus signs
        clean_number = ''.join(c for c in phone if c.isdigit())
        
        # Handle different formats
        if clean_number.startswith('0'):  # Local format: 0XXXXXXXXX
            # Assuming Ghana as default country code (233)
            return f"233{clean_number[1:]}"
        elif len(clean_number) == 9:  # Without country code or leading zero
            # Assuming Ghana as default country code (233)
            return f"233{clean_number}"
        elif clean_number.startswith('233'):  # Already in correct format
            return clean_number
        else:
            # Return as is if we can't determine the format
            return clean_number
    
    def send_sms(self, 
                phone_numbers: List[str], 
                message: str, 
                sender_name: Optional[str] = None) -> Dict[str, Any]:
        """Send SMS to one or more recipients."""
        if not phone_numbers:
            return {"success": False, "message": "No recipients provided"}
        
        # Format all phone numbers
        formatted_numbers = [self.format_phone_number(phone) for phone in phone_numbers]
        logger.info("Sending SMS to %d recipients", len(formatted_numbers))
        logger.info("Recipient numbers: %s", formatted_numbers)


        # Prepare payload
        payload = {
            "sender": sender_name or settings.SMS_SENDER_NAME,
            "message": message,
            "recipients": formatted_numbers
        }
        
        # Add use_case for Nigerian numbers if required
        nigerian_numbers = [num for num in formatted_numbers if num.startswith('234')]
        if nigerian_numbers:
            payload["use_case"] = "promotional"
        
        try:
            response = self.client.post(self.base_url, headers=self.headers, json=payload)
            if not response.is_success:
                logger.error(
                    "SMS API error %d: %s | payload: %s",
                    response.status_code, response.text, payload
                )
                return {
                    "success": False,
                    "message": f"SMS API returned {response.status_code}",
                    "error": response.text,
                }
            logger.info("SMS sent to %d recipients", len(formatted_numbers))
            return {
                "success": True,
                "data": response.json(),
                "recipients_count": len(formatted_numbers)
            }
        except httpx.HTTPError as e:
            logger.error("SMS sending failed: %s", str(e))
            return {
                "success": False,
                "message": f"SMS sending failed: {str(e)}",
                "error": str(e)
            }
    
    def get_template(self, template_name: str) -> Optional[SMSTemplate]:
        """Get SMS template by name."""
        return self.templates.get(template_name)
    
    def send_from_template(self, 
                          template_name: str, 
                          phone_numbers: List[str], 
                          context: Dict[str, str],
                          sender_name: Optional[str] = None) -> Dict[str, Any]:
        """Send SMS using a predefined template with context variables."""
        template = self.get_template(template_name)
        if not template:
            return {"success": False, "message": f"Template '{template_name}' not found"}
        
        # Format the message with context variables
        try:
            message = template.content.format(**context)
            return self.send_sms(phone_numbers, message, sender_name)
        except KeyError as e:
            return {"success": False, "message": f"Missing context variable: {str(e)}"}
        
    # Helper method to create standard context
    def _create_base_context(self, parishioner_name: str) -> Dict[str, str]:
        return {
            "parishioner_name": parishioner_name,
            "church_name": settings.PROJECT_NAME,
            "church_contact": settings.CHURCH_CONTACT
        }
    
    def send_user_account_created(self, phone: str, full_name: str, email: str, temp_password: str) -> Dict[str, Any]:
        """Send account creation SMS to a new admin user."""
        context = self._create_base_context(full_name)
        context.update({
            "full_name": full_name,
            "email": email,
            "temp_password": temp_password,
            "login_url": settings.FRONTEND_HOST,
            "church_name": settings.PROJECT_NAME,
        })
        return self.send_from_template("user_account_created", [phone], context)

    def send_verification_message(self,
                                 phone: str,
                                 parishioner_name: str,
                                 verification_link: str,
                                 access_code: str = "") -> Dict[str, Any]:
        """Send verification SMS to a parishioner."""
        context = self._create_base_context(parishioner_name)
        context["verification_link"] = verification_link
        context["access_code"] = access_code
        return self.send_from_template("record_verification_message", [phone], context)
    
    def send_main_welcome_message(self,
                            phone: str,
                            parishioner_name: str) -> Dict[str, Any]:
        """Send welcome SMS to a new parishioner."""
        context = self._create_base_context(parishioner_name)
        return self.send_from_template("main_welcome_message", [phone], context)
    

    def send_parishioner_onboarding_welcome_message(self,
                            phone: str,
                            parishioner_name: str) -> Dict[str, Any]:
        """Send welcome SMS to a new parishioner."""
        context = self._create_base_context(parishioner_name)
        return self.send_from_template("parishioner_onboarding_welcome_message", [phone], context)
    
    def send_church_id_generation_message(self,
                                         parishioner_name: str,
                                         phone: str,
                                         new_church_id: str

                                        ) -> Dict[str, Any]:
        """Send church id generation SMS to a parishioner."""
        context = self._create_base_context(parishioner_name)
        context["new_church_id"] = new_church_id
        return self.send_from_template("church_id_generation_message", [phone], context)
    
    def send_record_verification_confirmation_message(self, parishioner_name: str, phone: str,) -> Dict[str, Any]:
        context = self._create_base_context(parishioner_name)
        return self.send_from_template("record_verification_confirmation_message",[phone], context)
    
    def send_event_reminder(self, phone: str, parishioner_name: str, 
                          event_name: str, event_date: str, 
                          event_time: str) -> Dict[str, Any]:
        context = self._create_base_context(parishioner_name)
        context.update({
            "event_name": event_name,
            "event_date": event_date,
            "event_time": event_time
        })
        return self.send_from_template("event_reminder", [phone], context)
         

# Create a singleton instance
sms_service = SMSService()