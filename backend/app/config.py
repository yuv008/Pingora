"""
Application configuration using pydantic-settings
Loads configuration from environment variables
"""
from typing import List, Optional
from pydantic import field_validator, PostgresDsn, RedisDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="allow"
    )

    # Application
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    APP_NAME: str = "API Monitor Platform"
    API_V1_PREFIX: str = "/api/v1"

    # Server
    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://apimonitor:password@localhost:5432/apimonitor"
    DATABASE_URL_SYNC: str = "postgresql://apimonitor:password@localhost:5432/apimonitor"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Security
    SECRET_KEY: str = "your-secret-key-min-32-characters-long"
    JWT_SECRET_KEY: str = "your-jwt-secret-key-min-32-characters"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    BCRYPT_ROUNDS: int = 12

    # CORS
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:8000"
    ]

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: str | List[str]) -> List[str]:
        if isinstance(v, str):
            return [i.strip() for i in v.split(",")]
        return v

    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"
    CELERY_WORKER_CONCURRENCY: int = 4
    CELERY_TASK_TIME_LIMIT: int = 300

    # Email (SMTP)
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = "noreply@apimonitor.com"
    SMTP_FROM_NAME: str = "API Monitor"
    SMTP_TLS: bool = True
    SMTP_SSL: bool = False

    # Stripe
    STRIPE_API_KEY: str = ""
    STRIPE_PUBLISHABLE_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    STRIPE_PRICE_STARTER: str = ""
    STRIPE_PRICE_PRO: str = ""
    STRIPE_PRICE_BUSINESS: str = ""

    # Twilio (SMS)
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_FROM_NUMBER: str = ""

    # PagerDuty
    PAGERDUTY_API_KEY: str = ""

    # Sentry
    SENTRY_DSN: str = ""

    # Monitoring & Observability
    PROMETHEUS_PORT: int = 9090
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"

    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_FREE_TIER_RPM: int = 60
    RATE_LIMIT_STARTER_TIER_RPM: int = 120
    RATE_LIMIT_PRO_TIER_RPM: int = 300

    # Monitoring Defaults
    DEFAULT_CHECK_INTERVAL: int = 300
    DEFAULT_TIMEOUT: int = 30
    DEFAULT_RETRY_COUNT: int = 2
    MAX_CONCURRENT_CHECKS: int = 100
    MONITORING_REGIONS: List[str] = ["us-east-1", "us-west-1", "eu-west-1"]

    # Workspace Plan Limits
    FREE_MAX_MONITORS: int = 10
    FREE_MAX_TEAM_MEMBERS: int = 1
    FREE_CHECK_INTERVAL_MIN: int = 300
    FREE_DATA_RETENTION_DAYS: int = 30

    STARTER_MAX_MONITORS: int = 50
    STARTER_MAX_TEAM_MEMBERS: int = 5
    STARTER_CHECK_INTERVAL_MIN: int = 60
    STARTER_DATA_RETENTION_DAYS: int = 90

    PRO_MAX_MONITORS: int = 200
    PRO_MAX_TEAM_MEMBERS: int = 15
    PRO_CHECK_INTERVAL_MIN: int = 30
    PRO_DATA_RETENTION_DAYS: int = 365

    BUSINESS_MAX_MONITORS: int = 1000
    BUSINESS_MAX_TEAM_MEMBERS: int = 50
    BUSINESS_CHECK_INTERVAL_MIN: int = 10
    BUSINESS_DATA_RETENTION_DAYS: int = 730

    # Session Management
    SESSION_TIMEOUT_MINUTES: int = 60
    MAX_SESSIONS_PER_USER_FREE: int = 3
    MAX_SESSIONS_PER_USER_PAID: int = 10

    # WebSocket
    WS_HEARTBEAT_INTERVAL: int = 30
    WS_MAX_CONNECTIONS_PER_WORKSPACE: int = 100

    # Features
    FEATURE_3D_VISUALIZATIONS: bool = True
    FEATURE_ADVANCED_ANALYTICS: bool = True
    FEATURE_SSL_MONITORING: bool = True
    FEATURE_MULTI_REGION: bool = True
    FEATURE_WEBSOCKET_MONITORING: bool = True

    # File Upload
    UPLOAD_DIR: str = "/tmp/uploads"
    MAX_UPLOAD_SIZE: int = 10485760  # 10MB

    # AWS S3 (Optional)
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_S3_BUCKET: str = ""
    AWS_REGION: str = "us-east-1"

    # Testing
    TESTING: bool = False
    TEST_DATABASE_URL: str = ""


# Create global settings instance
settings = Settings()
