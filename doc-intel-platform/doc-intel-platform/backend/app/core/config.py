from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central app config. Values are loaded from environment variables / .env file."""

    # Postgres
    database_url: str = "postgresql://docintel:docintel@localhost:5432/docintel"

    # Redis / Celery
    redis_url: str = "redis://localhost:6379/0"

    # LLM
    anthropic_api_key: str = ""
    llm_model: str = "claude-sonnet-5"

    # Storage (local for dev; swap for S3 in production phase)
    upload_dir: str = "./uploaded_files"

    # App
    environment: str = "development"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
