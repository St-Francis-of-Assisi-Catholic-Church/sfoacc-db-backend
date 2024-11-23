import os
import secrets
import warnings
from typing import Any, List, Optional, Union, Literal, Annotated

from pydantic import AnyUrl, BeforeValidator
from pydantic.types import SecretStr
from pydantic_settings import ( SettingsConfigDict, BaseSettings )
from pydantic_core import MultiHostUrl
from typing_extensions import Self


# def parse_cors(v: Any) -> list[str] | str:
#     if isinstance(v, str) and not v.startswith("["):
#         return [i.strip() for i in v.split(",")]
#     elif isinstance(v, list | str):
#         return v
#     raise ValueError(v)

def parse_cors(v: Any) -> Union[List[str], str]:
    if isinstance(v, str) and not v.startswith("["):
        return [i.strip() for i in v.split(",")]
    elif isinstance(v, (list, str)):
        return v
    raise ValueError(v)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding='utf-8',
        env_ignore_empty=True,
        extra="ignore",
        case_sensitive=True,
    )

    BACKEND_CORS_ORIGINS: Annotated[
        list[AnyUrl] | str, BeforeValidator(parse_cors)
    ] = []

    @computed_field  # type: ignore[prop-decorator]
    @property
    def all_cors_origins(self) -> list[str]:
        return [str(origin).rstrip("/") for origin in self.BACKEND_CORS_ORIGINS] + [
            self.FRONTEND_HOST
        ]

    # Project
    PROJECT_NAME: str

    # API Settings
    API_V1_STR: str = "/api/v1"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 days
    FRONTEND_HOST: str = "http://localhost:5173"
    ENVIRONMENT: Literal["local", "staging", "production"] = "local"


    # Database Settings
    POSTGRES_SERVER: str
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str

 
# Create settings instance
settings = Settings()