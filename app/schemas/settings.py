from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class SettingUpdate(BaseModel):
    value: Optional[str] = None


class SettingRead(BaseModel):
    id: int
    key: str
    value: Optional[str]
    label: Optional[str]
    description: Optional[str]
    updated_at: datetime
    model_config = {"from_attributes": True}


class SettingsBulkUpdate(BaseModel):
    settings: dict  # {key: value}
