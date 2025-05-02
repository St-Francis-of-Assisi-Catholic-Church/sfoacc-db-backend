import logging
from typing import Any, List
from fastapi import APIRouter, BackgroundTasks, HTTPException, status, Body
from pydantic import validator

from app.schemas.bulk_message import BulkMessageIn
from app.schemas.common import APIResponse
from app.services.sms.service import sms_service
from app.services.email.service2 import email_service
from app.models.parishioner import Parishioner
from app.api.deps import SessionDep
from app.core.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

# Convert SMS service templates to the format needed for the API
def get_message_templates():
    templates = []
    
    # Add all templates from the SMS service
    for template_id, template in sms_service.templates.items():
        templates.append({
            "id": template_id,
            "name": template.name,
            "content": template.content
        })
    
    # Add custom message template which isn't in the SMS service
    templates.append({
        "id": "custom_message",
        "name": "Custom Message",
        "content": None
    })
    
    return templates

@router.post("/send", response_model=APIResponse)
async def send_bulk_message(
    *,
    session: SessionDep,
    bulk_message_in: BulkMessageIn = Body(...),
    background_tasks: BackgroundTasks,
) -> Any:
    try:
        # Log what we received
        logger.info(f"Received bulk message request: {bulk_message_in}")
        
        # Validate template against defined templates
        message_templates = get_message_templates()
        template_ids = [template["id"] for template in message_templates]
        
        if bulk_message_in.template not in template_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid template: {bulk_message_in.template}. Must be one of: {', '.join(template_ids)}"
            )
        
        # Get message content based on template
        message_content = bulk_message_in.custom_message
        
        # For custom messages, ensure content is provided
        if bulk_message_in.template == "custom_message" and not message_content:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Custom message is required when using the custom_message template"
            )
            
        # Fetch parishioner details for sending messages
        parishioners = session.query(Parishioner).filter(
            Parishioner.id.in_(bulk_message_in.parishioner_ids)
        ).all()
        
        if not parishioners:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No parishioners found with the provided IDs"
            )
        
        # Log the message sending
        logger.info(f"Sending {bulk_message_in.channel} message to {len(parishioners)} parishioners")
        
        sent_count = 0
        
        # Process sending based on channel
        for parishioner in parishioners:
            full_name = f"{parishioner.first_name} {parishioner.last_name}"

            # Build context with all possible variables used in templates
            context = {
                "parishioner_name": full_name,
                "church_name": settings.CHURCH_NAME,
                "church_contact": settings.CHURCH_CONTACT,
                "new_church_id": getattr(parishioner, "new_church_id", "N/A"),
                # "verification_link": f"{settings.BASE_URL}/verify/{parishioner.id}",
                "event_name": bulk_message_in.event_name or "Parish Event",
                "event_date": bulk_message_in.event_date or "Sunday",
                "event_time": bulk_message_in.event_time or "10:00 AM"
            }
            
            # Send SMS if requested
            if bulk_message_in.channel in ["sms", "both"] and parishioner.mobile_number:
                if bulk_message_in.template == "custom_message":
                    # Format custom message with context variables
                    try:
                        formatted_message = message_content.format(**context)
                        background_tasks.add_task(
                            sms_service.send_sms,
                            phone_numbers=[parishioner.mobile_number],
                            message=formatted_message
                        )
                        sent_count += 1
                    except KeyError as e:
                        logger.error(f"Missing variable in custom message: {str(e)}")
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Missing variable in custom message: {str(e)}"
                        )
                else:
                    # using predefined templates
                    background_tasks.add_task(
                        sms_service.send_from_template,
                        template_name=bulk_message_in.template,
                        phone_numbers=[parishioner.mobile_number],
                        context=context
                    )
                sent_count += 1
            
        
            # Send email if requested
            if bulk_message_in.channel in ["email", "both"] and getattr(parishioner, "email_address", None):
                if bulk_message_in.template == "custom_message":
                    logger.info("custom emails--------")
                    # Send custom email using a wrapper function to handle async
                    async def send_custom_email_task(to_email, name, msg, subj, **ctx):
                        return await email_service.send_custom_message(
                            to_email=to_email,
                            parishioner_name=name,
                            custom_message=msg,
                            subject=subj,
                            **ctx
                        )
                    
                    background_tasks.add_task(
                        send_custom_email_task,
                        parishioner.email_address,
                        full_name,
                        bulk_message_in.custom_message,
                        bulk_message_in.subject or "Message from Your Parish",
                        **context
                    )
                    sent_count += 1
                else:
                    # Send template email using a wrapper function
                    async def send_template_email_task(template, emails, ctx):
                        return await email_service.send_from_template(
                            template_name=template,
                            to_emails=emails,
                            context=ctx
                        )
                    
                    background_tasks.add_task(
                        send_template_email_task,
                        bulk_message_in.template,
                        [parishioner.email_address],
                        context
                    )
                    sent_count += 1
                    
        return APIResponse(
            message=f"Successfully queued messages to {sent_count} parishioners",
            data={"sent_count": sent_count}
        )
   
    except Exception as e:
        logger.error(f"Error sending bulk message: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error sending message: {str(e)}"
        )

@router.get("/templates", response_model=APIResponse)
async def get_all_bulk_message_templates() -> Any:
    try:
        message_templates = get_message_templates()
        return APIResponse(
            message="Templates retrieved successfully",
            data= {
                "message_templates": message_templates,
                "available_variables": [
                    {"name": "parishioner_name", "description": "Full name of the parishioner"},
                    {"name": "church_name", "description": "Name of the church from settings"},
                    {"name": "church_contact", "description": "Contact information for the church"},
                    {"name": "new_church_id", "description": "Parishioner's church ID if available"},
                    {"name": "verification_link", "description": "Link for verifying parishioner information"},
                    {"name": "event_name", "description": "Name of the event (provided in request)"},
                    {"name": "event_date", "description": "Date of the event (provided in request)"},
                    {"name": "event_time", "description": "Time of the event (provided in request)"}
                ]
            }

        )
 
    except Exception as e:
        logger.error(f"Error retrieving templates: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving templates: {str(e)}"
        )