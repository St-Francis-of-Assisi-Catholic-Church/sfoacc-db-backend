from pydantic import BaseModel
from typing import List, Optional

class LanguageBase(BaseModel):
    name: str
    description: Optional[str]

class LanguageCreate(LanguageBase):
    pass

class LanguageUpdate(LanguageBase):
    pass

class LanguageRead(LanguageBase):
    id: int

    class Config:
        from_attributes = True

