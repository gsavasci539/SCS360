from functools import lru_cache
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/school_management"
    JWT_SECRET_KEY: str = "development-only-change-me"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 120
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    SMTP_HOST: str = "smtp.example.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = "noreply@example.com"
    SMTP_FROM_NAME: str = "SCS360"
    NOTIFICATION_DELIVERY_ENABLED: bool = False
    NOTIFICATION_TIMEOUT_SECONDS: float = 20.0
    NOTIFICATION_WEBHOOK_SECRET: str = ""
    IYZICO_API_KEY: str = ""
    IYZICO_SECRET_KEY: str = ""
    IYZICO_BASE_URL: str = "https://sandbox-api.iyzipay.com"
    IYZICO_CALLBACK_URL: str = ""
    IYZICO_PAYMENT_ENABLED: bool = False
    IYZICO_ORGANIZATION_ID: str = ""
    # Independent key for school merchant snapshots; never the SaaS/JWT secret.
    SCHOOL_PAYMENT_ENCRYPTION_KEY: str = ""
    SCHOOL_PAYMENT_CALLBACK_URL: str = ""
    SCHOOL_PAYMENT_PORTAL_URL: str = ""
    # Platform subscriptions must not charge through a school's tuition account.
    SAAS_IYZICO_API_KEY: str = ""
    SAAS_IYZICO_SECRET_KEY: str = ""
    SAAS_IYZICO_BASE_URL: str = "https://sandbox-api.iyzipay.com"
    SAAS_IYZICO_CALLBACK_URL: str = ""
    SAAS_PORTAL_URL: str = ""
    SAAS_CHECKOUT_ENCRYPTION_KEY: str = ""
    SAAS_PAYMENT_ENABLED: bool = False
    SAAS_PAYMENT_INSTRUCTIONS: str = ""
    SAAS_SUPPORT_EMAIL: str = ""
    PASSWORD_RESET_URL: str = "http://localhost:5173/reset-password"

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
    PRIVATE_UPLOAD_DIR: str = "private_uploads"
    MAX_UPLOAD_SIZE_MB: int = 10
    ALLOWED_FILE_TYPES: str = "pdf,jpg,jpeg,png,docx"

    APP_ENV: str = "development"
    BUSINESS_TIMEZONE: str = "Europe/Istanbul"
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173,http://localhost"

    # LLM Configuration for Chatbot
    # Default: Ollama (free local LLM)
    CHATBOT_LLM_PROVIDER: str = "ollama"  # "ollama", "openai", or "mock"
    OLLAMA_MODEL: str = "llama3.2"
    OLLAMA_BASE_URL: str = "http://localhost:11434/v1"
    # Intent detection falls back to local keyword matching after this limit.
    CHATBOT_LLM_TIMEOUT_SECONDS: float = 12.0
    
    # OpenAI (optional, requires API key)
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"
    OPENAI_BASE_URL: str | None = None

    @model_validator(mode="after")
    def validate_security_settings(self) -> "Settings":
        environment = self.APP_ENV.strip().lower()
        try:
            ZoneInfo(self.BUSINESS_TIMEZONE)
        except ZoneInfoNotFoundError as exc:
            raise ValueError("BUSINESS_TIMEZONE must be a valid IANA timezone") from exc
        if self.CHATBOT_LLM_PROVIDER not in {"ollama", "openai", "mock"}:
            raise ValueError("CHATBOT_LLM_PROVIDER must be ollama, openai or mock")
        if not 0 < self.CHATBOT_LLM_TIMEOUT_SECONDS <= 30:
            raise ValueError("CHATBOT_LLM_TIMEOUT_SECONDS must be between 0 and 30")
        if self.CHATBOT_LLM_PROVIDER == "openai" and not self.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is required for the OpenAI provider")
        if self.JWT_ALGORITHM not in {"HS256", "HS384", "HS512"}:
            raise ValueError("JWT_ALGORITHM must be an HMAC SHA-2 algorithm")
        if environment in {"production", "staging"}:
            if self.CHATBOT_LLM_PROVIDER == "mock":
                raise ValueError("Mock chatbot provider is not allowed in production or staging")
            insecure_secrets = {
                "change_me",
                "development-only-change-me",
                "replace-with-a-long-random-secret",
            }
            if len(self.JWT_SECRET_KEY) < 32 or self.JWT_SECRET_KEY in insecure_secrets:
                raise ValueError("JWT_SECRET_KEY must be a unique secret of at least 32 characters")
            if "*" in self.cors_origins_list:
                raise ValueError("Wildcard CORS origins are not allowed outside development")
            if self.NOTIFICATION_DELIVERY_ENABLED and not self.PASSWORD_RESET_URL.startswith("https://"):
                raise ValueError("PASSWORD_RESET_URL must use HTTPS in production or staging")
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
