from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')
    app_api_key: str = 'local-demo-key-change-before-hosting'
    enterprise_api_key: str = 'local-enterprise-key-change-before-hosting'
    api_base_url: str = 'http://127.0.0.1:8000'
    embedding_mode: str = 'fastembed'
    qdrant_path: str = 'data/qdrant'
    enterprise_db_path: str = 'data/enterprise.sqlite3'
    model_cache_path: str = 'data/models'
    sample_documents_path: str = 'samples'
    embedding_threads: int = Field(default=1, ge=1, le=8)
    max_concurrent_queries: int = Field(default=4, ge=1, le=16)
    qdrant_url: str | None = None
    qdrant_api_key: str | None = None
    openai_api_key: str | None = None
    openai_model: str = 'gpt-4.1-mini'


@lru_cache
def settings():
    return Settings()
