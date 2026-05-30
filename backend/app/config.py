from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "DocuPilot"
    environment: str = "development"
    debug: bool = True

    public_base_url: str = "http://localhost:8000"

    database_url: str = (
        "postgresql+asyncpg://docupilot:docupilot@localhost:5433/docupilot"
    )

    redis_url: str = "redis://localhost:6379/0"

    admin_password: str = "change-me"
    admin_token_ttl_days: int = 7
    ip_hash_salt: str = "docupilot-dev-salt"

    auto_create_tables: bool = True
    widget_bundle_path: str | None = None

    gemini_api_key: str = ""
    gemini_chat_model: str = "gemini-2.5-flash"
    gemini_embedding_model: str = "gemini-embedding-001"
    embedding_dimensions: int = 768

    chunk_size_tokens: int = 500
    chunk_overlap_tokens: int = 50
    retrieval_top_k: int = 5

    cors_origins: list[str] = ["*"]


settings = Settings()
