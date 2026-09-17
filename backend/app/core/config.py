from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/school_management"
    JWT_SECRET_KEY: str = "development-only-change-me"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    SMTP_HOST: str = "smtp.example.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = "noreply@example.com"
    SMTP_FROM_NAME: str = "EduPanel"

    SMS_PROVIDER: str = "netgsm"
    SMS_API_URL: str = ""
    SMS_USERNAME: str = ""
    SMS_PASSWORD: str = ""
    SMS_HEADER: str = ""

    WHATSAPP_PROVIDER: str = "meta"
    WHATSAPP_API_URL: str = "https://graph.facebook.com/v18.0"
    WHATSAPP_ACCESS_TOKEN: str = ""
    WHATSAPP_PHONE_NUMBER_ID: str = ""
    WHATSAPP_BUSINESS_ACCOUNT_ID: str = ""

    UPLOAD_DIR: str = "uploads"
    MAX_UPLOAD_SIZE_MB: int = 10
    ALLOWED_FILE_TYPES: str = "pdf,jpg,jpeg,png,docx"

    APP_ENV: str = "development"
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173,http://localhost"

    @model_validator(mode="after")
    def validate_security_settings(self) -> "Settings":
        environment = self.APP_ENV.strip().lower()
        if self.JWT_ALGORITHM not in {"HS256", "HS384", "HS512"}:
            raise ValueError("JWT_ALGORITHM must be an HMAC SHA-2 algorithm")
        if environment in {"production", "staging"}:
            insecure_secrets = {
                "change_me",
                "development-only-change-me",
                "replace-with-a-long-random-secret",
            }
            if len(self.JWT_SECRET_KEY) < 32 or self.JWT_SECRET_KEY in insecure_secrets:
                raise ValueError("JWT_SECRET_KEY must be a unique secret of at least 32 characters")
            if "*" in self.cors_origins_list:
                raise ValueError("Wildcard CORS origins are not allowed outside development")
        return self

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def allowed_file_types_list(self) -> list[str]:
        return [ft.strip().lower() for ft in self.ALLOWED_FILE_TYPES.split(",") if ft.strip()]

    @property
    def max_upload_size_bytes(self) -> int:
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()
