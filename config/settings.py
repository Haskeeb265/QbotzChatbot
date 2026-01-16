from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional, Literal


class Settings(BaseSettings):
    # Database Configuration
    DATABASE_URL: str  # postgresql://qbotz_user:12345!@localhost:5466/qbotz_db
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20

    # PgVector Configuration
    VECTOR_DIMENSION: int = 768

    # GROQ Configuration
    GROQ_API_KEY: str
    GROQ_MODEL: str = "deepseek-r1-distill-qwen-32b"
    GROQ_RATE_LIMIT: int = 30

    # Embedding Configuration
    EMBEDDING_MODEL: str = "all-mpnet-base-v2"
    EMBEDDING_DIMENSION: int = 768
    EMBEDDING_BATCH_SIZE: int = 32

    # SAP Configuration
    SAP_BASE_URL: str
    SAP_USERNAME: str
    SAP_PASSWORD: str
    SAP_CLIENT: str = "140"

    # SyncJob Configuration
    SAP_SYNC_INTERVAL_HOURS: int = 6
    SAP_SYNC_LOOKBACK_DAYS: int = 90

    # Observability
    LOG_LEVEL: str = "INFO"  # DEBUG, INFO, WARNING, ERROR
    ENABLE_QUERY_LOGGING: bool = True  # Log all SQL queries (Set it false when in prod)

    # Cache Configuration
    CACHE_TTL_SECONDS: int = 300

    # Hybrid Search Configuration
    HYBRID_SQL_WEIGHT: float = 0.6  # Weight for SQL results in hybrid merge
    HYBRID_VECTOR_WEIGHT: float = 0.4  # Weight for vector results in hybrid merge
    HYBRID_MAX_RESULTS: int = 20  # Maximum results to return from hybrid search
    HYBRID_DEDUP_ENABLED: bool = True  # Enable deduplication by sales_order

    # Application
    APP_NAME: str = "Qbotz-Chatbot"
    ENVIRONMENT: Literal["development", "staging", "production"] = "development"

    # Pydantic V2 Configuration
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )


settings = Settings()
