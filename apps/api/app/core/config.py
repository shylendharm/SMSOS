from pathlib import Path
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
_ENV_PATH = _PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_ENV_PATH) if _ENV_PATH.exists() else ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_ENV: str = "development"
    APP_SECRET_KEY: str = "change-me-in-production-secret-key-at-least-32-bytes"
    DATABASE_URL: str = "postgresql+asyncpg://postgres:12345678@localhost:5432/smsos_dev"

    @field_validator("DATABASE_URL", mode="after")
    @classmethod
    def normalize_database_url(cls, value: str, info) -> str:
        app_env = info.data.get("APP_ENV")
        if app_env == "testing" and "smsos_test" not in value:
            return value.replace("smsos_dev", "smsos_test")
        return value

    JWT_SECRET: str = "change-me-in-production-jwt-secret-key-at-least-32-bytes"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_MINUTES: int = 30

    TWILIO_ACCOUNT_SID: str = "ACXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
    TWILIO_AUTH_TOKEN: str = "your_auth_token_here"
    TWILIO_PHONE_NUMBER: str = "+14155238886"

    API_BASE_URL: str = "http://localhost:8000"
    FRONTEND_BASE_URL: str = "http://localhost:5173"
    LOG_LEVEL: str = "INFO"

    GEMINI_API_KEY: str | None = None
    GROQ_API_KEY: str | None = None
    XAI_API_KEY: str | None = None
    GROK_API_KEY: str | None = None
    OPENROUTER_API_KEY: str | None = None
    ORS_API_KEY: str | None = None
    OWNER_PHONE_NUMBER: str = ""


settings = Settings()