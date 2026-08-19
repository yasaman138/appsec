from typing import Set
from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

KNOWN_INSECURE_SECRETS: Set[str] = {
    "secret",
    "changeme",
    "password",
    "admin",
    "12345678901234567890123456789012",
    "appsec-super-secret-key-change-in-production-2026",
}


class AuthSettings(BaseSettings):
    APP_NAME: str = "Auth Service"
    APP_ENV: str = "development"
    DEBUG: bool = False
    PORT: int = 8001
    HOST: str = "0.0.0.0"

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./auth.db"

    # JWT Configuration
    JWT_SECRET_KEY: str = "appsec-super-secret-key-change-in-production-2026"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Rate Limiting Configuration
    RATE_LIMITING_ENABLED: bool = True
    RATE_LIMIT_MAX_REQUESTS: int = 60
    RATE_LIMIT_WINDOW_SECONDS: int = 60

    # CORS Allowed Origins
    ALLOWED_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:8000",
        "http://localhost:8001",
        "http://localhost:8002",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8000",
        "http://127.0.0.1:8001",
        "http://127.0.0.1:8002",
    ]

    @field_validator("JWT_SECRET_KEY")
    @classmethod
    def validate_jwt_secret_entropy(cls, v: str) -> str:
        if not v or len(v.strip()) < 32:
            raise ValueError(
                "JWT_SECRET_KEY must be at least 32 characters long to ensure cryptographic entropy."
            )
        return v

    @model_validator(mode="after")
    def validate_production_hardening(self) -> "AuthSettings":
        if self.APP_ENV.lower() == "production":
            if self.JWT_SECRET_KEY in KNOWN_INSECURE_SECRETS or "change-in-production" in self.JWT_SECRET_KEY.lower():
                raise ValueError(
                    "Production safety violation: Default placeholder JWT_SECRET_KEY is strictly forbidden in production mode."
                )
        return self

    def get_masked_secret(self) -> str:
        if len(self.JWT_SECRET_KEY) <= 8:
            return "********"
        return f"{self.JWT_SECRET_KEY[:4]}...{self.JWT_SECRET_KEY[-4:]}"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = AuthSettings()
