from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    cors_origins: list[str] = ["http://localhost:3000"]
    debug: bool = False

    model_config = {"env_prefix": "UNIFLOW_"}


settings = Settings()
