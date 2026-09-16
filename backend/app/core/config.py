from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central app config. Values are loaded from environment variables / .env file."""

    # Postgres
    database_url: str = "postgresql://doclarity:doclarity@localhost:5432/doclarity"

    # Least-privilege role for executing LLM-generated SQL (Slice 4). Can
    # only SELECT - see db/init/01_readonly_role.sql. Defense in depth
    # alongside the app-level query validator in app/services/sql_guard.py.
    analytics_database_url: str = "postgresql://doclarity_readonly:doclarity_readonly@localhost:5432/doclarity"

    # Redis / Celery
    redis_url: str = "redis://localhost:6379/0"

    # LLM
    # "anthropic" (paid, real API key) or "ollama" (free, local/cloud via Ollama).
    llm_provider: str = "ollama"
    anthropic_api_key: str = ""
    llm_model: str = "claude-sonnet-5"

    # Embeddings - Anthropic has no embeddings API, so this is separate from
    # llm_provider and always goes through Ollama for now.
    embedding_provider: str = "ollama"

    ollama_base_url: str = "http://localhost:11434"
    ollama_chat_model: str = "llama3.2:3b"
    ollama_embed_model: str = "nomic-embed-text"

    # Auth (Slice 8). Change jwt_secret_key for any real deployment - this
    # default is only safe for local dev.
    jwt_secret_key: str = "dev-secret-change-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24

    # Storage: "local" (dev, disk under upload_dir) or "s3" (S3-compatible,
    # e.g. Cloudflare R2 - set s3_endpoint_url for R2/non-AWS providers).
    storage_backend: str = "local"
    upload_dir: str = "./uploaded_files"
    s3_bucket: str = ""
    s3_endpoint_url: str = ""
    s3_access_key_id: str = ""
    s3_secret_access_key: str = ""
    s3_region: str = "auto"

    # App
    environment: str = "development"
    # Comma-separated list of allowed CORS origins (frontend URL(s)).
    cors_origins: str = "http://localhost:3000"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
