from typing import Annotated, Any, List, Literal, Optional, Union
from pydantic import AnyUrl, BeforeValidator, EmailStr, PostgresDsn, model_validator
from pydantic_core import MultiHostUrl
from pydantic_settings import BaseSettings, SettingsConfigDict

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
        case_sensitive=True,
        extra="ignore",
        env_ignore_empty=True
    )

    # API Settings
    API_V1_STR: str = "/api/v1"
    VERSION: str = "1.0.0"
    PROJECT_NAME: str

    # Single source of truth for the server address.
    # Set to your IP (e.g. 194.146.13.3) or domain (e.g. api.sfoacc.org).
    # BACKEND_HOST and BACKEND_CORS_ORIGINS are derived from this automatically.
    DOMAIN: str

    BACKEND_HOST: Optional[str] = None
    FRONTEND_HOST: str

    # SMS & Contact
    ARKESEL_API_KEY: str
    SMS_SENDER_NAME: str
    CHURCH_NAME: str
    CHURCH_CONTACT: str

    ENVIRONMENT: Literal["local", "staging", "production"] = "local"

    # Security
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 8  # 8 hours

    # Upload limits
    MAX_UPLOAD_SIZE_MB: int = 10

    # Database pool settings
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 40
    DB_POOL_TIMEOUT: int = 60
    DB_POOL_RECYCLE: int = 1800

    # CORS — derived from DOMAIN if not explicitly set
    BACKEND_CORS_ORIGINS: Annotated[
        Union[List[AnyUrl], str], BeforeValidator(parse_cors)
    ] = []

    @model_validator(mode='after')
    def derive_from_domain(self) -> 'Settings':
        scheme = "https" if self.ENVIRONMENT == "production" and "." in self.DOMAIN else "http"
        if not self.BACKEND_HOST:
            self.BACKEND_HOST = f"{scheme}://{self.DOMAIN}:8000"
        if not self.BACKEND_CORS_ORIGINS:
            self.BACKEND_CORS_ORIGINS = [
                f"http://{self.DOMAIN}",
                f"https://{self.DOMAIN}",
                f"http://{self.DOMAIN}:8000",
                f"https://{self.DOMAIN}:8000",
                # localhost for local development
                "http://localhost",
                "http://localhost:3000",
                "http://localhost:5173",
                "http://localhost:8080",
                "http://127.0.0.1",
                "http://127.0.0.1:3000",
                "http://127.0.0.1:5173",
                "http://localhost:4200",
                "http://127.0.0.1:4200",
            ]
        return self

    @property
    def all_cors_origins(self) -> List[str]:
        return [str(origin).rstrip("/") for origin in self.BACKEND_CORS_ORIGINS] + [
            self.FRONTEND_HOST
        ]

    # Database
    POSTGRES_SERVER: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_PORT: int

    # Email Settings
    SMTP_TLS: bool = True
    SMTP_SSL: bool = False
    SMTP_PORT: Optional[int] = None
    SMTP_HOST: Optional[str] = None
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    EMAILS_FROM_EMAIL: Optional[EmailStr] = None

    # First Admin User
    FIRST_SUPERUSER: EmailStr
    FIRST_SUPERUSER_PASSWORD: str
    FIRST_SUPERUSER_PHONE: str = ""   # digits + country code, e.g. 233543460633
    SUPER_ADMIN_EMAIL: str = "database.sfoacc@gmail.com"

    @property
    def database_url(self) -> str:
        """
        Assemble database URL from settings
        """
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        # return  str(self.SQLALCHEMY_DATABASE_URI)
    

    
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> PostgresDsn:
        return MultiHostUrl.build(
            scheme="postgresql+psycopg",
            username=self.POSTGRES_USER,
            password=self.POSTGRES_PASSWORD,
            host=self.POSTGRES_SERVER,
            port=self.POSTGRES_PORT,
            path=self.POSTGRES_DB,
        )

settings = Settings()