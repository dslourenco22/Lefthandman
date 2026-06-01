"""Application configuration, loaded from environment variables."""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database. Defaults to a local SQLite file so the app runs without Postgres;
    # docker-compose overrides this with a Postgres DSN.
    DATABASE_URL: str = "sqlite:///./resume_ranker.db"

    # Auth
    SECRET_KEY: str = "CHANGE_ME_IN_PRODUCTION_use_a_long_random_string"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 8

    # NLP / embeddings
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    SPACY_MODEL: str = "en_core_web_sm"

    # Uploads
    MAX_UPLOAD_BYTES: int = 10 * 1024 * 1024  # 10 MB per file
    ALLOWED_EXTENSIONS: set[str] = {".pdf", ".docx", ".txt"}

    # First-run bootstrap admin (created if no users exist)
    BOOTSTRAP_ADMIN_EMAIL: str = "admin@omnicontrol.com"
    BOOTSTRAP_ADMIN_PASSWORD: str = "ChangeMe123!"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
