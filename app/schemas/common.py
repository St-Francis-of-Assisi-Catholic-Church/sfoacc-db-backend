from typing import Any
from pydantic import BaseModel


class APIResponse(BaseModel):
    message: str
    data: Any | None