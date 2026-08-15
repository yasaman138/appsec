from pydantic_settings import BaseSettings, SettingsConfigDict


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

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = AuthSettings()
