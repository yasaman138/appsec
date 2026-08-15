from pydantic_settings import BaseSettings, SettingsConfigDict


class ApiSettings(BaseSettings):
    APP_NAME: str = "Core Resource API Service"
    APP_ENV: str = "development"
    DEBUG: bool = False
    PORT: int = 8002
    HOST: str = "0.0.0.0"

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./api.db"

    # Redis Cache
    REDIS_URL: str = "redis://localhost:6379/0"
    CACHE_DEFAULT_TTL_SECONDS: int = 300  # 5 minutes
    CACHE_ENABLED: bool = True

    # JWT Configuration (Must match Auth Service key/algorithm)
    JWT_SECRET_KEY: str = "appsec-super-secret-key-change-in-production-2026"
    JWT_ALGORITHM: str = "HS256"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = ApiSettings()
