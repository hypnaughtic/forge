"""RAG pipeline configuration loaded from environment variables."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration for the RAG pipeline."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # llm-gateway configuration (REQUIRED)
    # All LLM generation calls go through the gateway
    llm_gateway_url: str = "http://localhost:8080"
    llm_gateway_api_key: str = ""

    # Generation model settings
    llm_model: str = "gpt-4"
    llm_temperature: float = 0.0
    llm_max_tokens: int = 2048

    # Embedding settings
    embedding_model: str = "text-embedding-3-small"
    embedding_dimension: int = 1536

    # Chunking settings
    chunk_size: int = 1000
    chunk_overlap: int = 200

    # Retrieval settings
    retrieval_top_k: int = 5


@lru_cache
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()


settings = get_settings()
