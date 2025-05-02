from typing import List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field, validator

from app.services.sms.service import sms_service

class BulkMessageIn(BaseModel):
    parishioner_ids: List[UUID]
    channel: Literal["email", "sms", "both"] = "both"
    custom_message: Optional[str] = None
    template: str = "main_welcome_message"

    subject: Optional[str] = None #for email subject when using custom message
    # Event details for custom messages
    event_name: Optional[str] = None
    event_date: Optional[str] = None
    event_time: Optional[str] = None

    class Config:
        schema_extra = {
            "example": {
                "parishioner_ids": ["123e4567-e89b-12d3-a456-426614174000"],
                "channel": "sms",
                "custom_message": "Dear {parishioner_name}, you are reminded about our {event_name} at {event_time} on {event_date}.",
                "template": "custom_message",
                "subject": "Important Reminder: Parish Event",
                "event_name": "Parish Council Meeting",
                "event_date": "Friday",
                "event_time": "2:00 PM"
            }
        }
