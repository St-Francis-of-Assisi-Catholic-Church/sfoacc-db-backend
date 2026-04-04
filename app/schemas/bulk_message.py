from datetime import datetime
from typing import List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class BulkMessageIn(BaseModel):
    parishioner_ids: List[UUID]
    channel: Literal["email", "sms", "both"] = "both"
    template: str = "main_welcome_message"
    custom_message: Optional[str] = None
    subject: Optional[str] = None
    event_name: Optional[str] = None
    event_date: Optional[str] = None
    event_time: Optional[str] = None

    @model_validator(mode="after")
    def _auto_template(self):
        if self.custom_message and self.template == "main_welcome_message":
            self.template = "custom_message"
        return self


class SingleMessageIn(BaseModel):
    channel: Literal["email", "sms", "both"] = "both"
    template: str = "main_welcome_message"
    custom_message: Optional[str] = None
    subject: Optional[str] = None
    event_name: Optional[str] = None
    event_date: Optional[str] = None
    event_time: Optional[str] = None

    @model_validator(mode="after")
    def _auto_template(self):
        if self.custom_message and self.template == "main_welcome_message":
            self.template = "custom_message"
        return self


class ScheduleMessageIn(BulkMessageIn):
    send_at: datetime = Field(..., description="UTC datetime when the message should be sent")


class ScheduleSingleMessageIn(SingleMessageIn):
    send_at: datetime = Field(..., description="UTC datetime when the message should be sent")


class MessageTemplateCreate(BaseModel):
    id: str = Field(..., pattern=r"^[a-z0-9_]+$", description="Lowercase slug, e.g. 'event_reminder'")
    name: str
    content: str
    description: Optional[str] = None


class MessageTemplateUpdate(BaseModel):
    name: Optional[str] = None
    content: Optional[str] = None
    description: Optional[str] = None


class MessageTemplateRead(BaseModel):
    id: str
    name: str
    content: str
    description: Optional[str]
    is_system: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
