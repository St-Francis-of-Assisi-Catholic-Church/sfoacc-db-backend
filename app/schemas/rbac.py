from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel


class PermissionRead(BaseModel):
    id: int
    code: str
    name: str
    description: Optional[str] = None
    module: str
    model_config = {"from_attributes": True}


class RoleCreate(BaseModel):
    name: str
    label: str
    description: Optional[str] = None


class RoleUpdate(BaseModel):
    label: Optional[str] = None
    description: Optional[str] = None


class RoleRead(BaseModel):
    id: int
    name: str
    label: str
    description: Optional[str] = None
    is_system: bool
    permissions: List[PermissionRead] = []
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}


class RolePermissionsUpdate(BaseModel):
    permission_ids: List[int]
