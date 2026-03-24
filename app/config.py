from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    cors_origins: list[str] = ["http://localhost:3000"]
    debug: bool = False
    database_url: str = "postgresql+asyncpg://postgres:test@localhost:5432/uniflow_test"
    db_pool_size: int = 10
    db_max_overflow: int = 5

    # Rate limiting settings (requests per minute)
    auth_rate_limit: int = 20  # Per IP
    web_rate_limit: int = 120  # Per user
    edge_rate_limit: int = 60  # Per agent
    rate_limit_window: int = 60  # Window in seconds

    # JWT settings
    jwt_secret: str = "dev-secret-change-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60  # 1 hour
    refresh_token_expire_days: int = 90  # 90 days

    # OpenAsset API settings
    oa_api_base_url: str = "https://api.openasset.com"  # Placeholder
    oa_api_key: str = "dev-placeholder-key"  # Override in production
    oa_concurrency_limit: int = 10  # Max concurrent OA API calls
    oa_batch_size: int = 25  # Files per batch for pre-registration
    oa_retry_delays: list[int] = [2, 5, 15, 60]  # Exponential backoff delays (seconds)

    model_config = {"env_prefix": "UNIFLOW_"}


settings = Settings()
