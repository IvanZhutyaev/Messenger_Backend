from pydantic_settings import BaseSettings, SettingsConfigDict
from datetime import timedelta


class Settings(BaseSettings):
    API_TITLE: str = "Cluster"
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"

    DATABASE_URL: str = "postgresql://cluster_user:password@db:5432/clusterdb"
    
    # JWT Settings
    JWT_SECRET_KEY: str = "your-secret-key-here-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True
    )


class RateLimitSettings:
    """Rate limiting settings."""
    DEFAULT_LIMIT: str = "100/minute"
    LOGIN_LIMIT: str = "5/minute"
    WS_LIMIT: str = "10/minute"


settings = Settings()
rate_limit_settings = RateLimitSettings()
