"""
Abstract embedding interface with pluggable implementations.

Provides a uniform API for generating embeddings regardless of the
underlying provider (OpenAI, Sentence Transformers, Cohere, etc.).
"""

from abc import ABC, abstractmethod
from typing import List

import httpx

from rag.config import settings


class EmbeddingProvider(ABC):
    """Abstract base class for embedding providers."""

    @abstractmethod
    def embed_text(self, text: str) -> List[float]:
        """Generate an embedding vector for a single text."""
        raise NotImplementedError

    @abstractmethod
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embedding vectors for a batch of texts."""
        raise NotImplementedError

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Return the dimensionality of the embedding vectors."""
        raise NotImplementedError


class GatewayEmbeddingProvider(EmbeddingProvider):
    """Embedding provider that routes through llm-gateway.

    Uses the gateway's embedding endpoint to generate vectors,
    ensuring centralized tracking and rate limiting.
    """

    def __init__(
        self,
        model: str = "",
        gateway_url: str = "",
        gateway_api_key: str = "",
    ):
        self.model = model or settings.embedding_model
        self.gateway_url = gateway_url or settings.llm_gateway_url
        self.gateway_api_key = gateway_api_key or settings.llm_gateway_api_key
        self._dimension = settings.embedding_dimension

    @property
    def dimension(self) -> int:
        return self._dimension

    def embed_text(self, text: str) -> List[float]:
        """Generate an embedding for a single text via llm-gateway."""
        results = self.embed_batch([text])
        return results[0]

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a batch of texts via llm-gateway."""
        with httpx.Client(timeout=60.0) as client:
            response = client.post(
                f"{self.gateway_url}/v1/embeddings",
                json={
                    "model": self.model,
                    "input": texts,
                },
                headers={
                    "Authorization": f"Bearer {self.gateway_api_key}",
                    "Content-Type": "application/json",
                },
            )
            response.raise_for_status()

        data = response.json()
        # Sort by index to ensure order matches input
        sorted_embeddings = sorted(data["data"], key=lambda x: x["index"])
        return [item["embedding"] for item in sorted_embeddings]
