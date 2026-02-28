"""Agent configuration loaded from environment variables."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration for the LangGraph agent."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # llm-gateway configuration (REQUIRED)
    # All LLM calls go through the gateway — never directly to a provider
    llm_gateway_url: str = "http://localhost:8080"
    llm_gateway_api_key: str = ""

    # Model settings (the gateway routes to the actual provider)
    llm_model: str = "gpt-4"
    llm_temperature: float = 0.0
    llm_max_tokens: int = 4096

    # Agent settings
    agent_max_iterations: int = 10
    agent_verbose: bool = True


@lru_cache
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()


settings = get_settings()
