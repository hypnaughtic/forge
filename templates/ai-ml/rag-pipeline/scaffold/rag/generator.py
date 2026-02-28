"""
Generation module that routes all LLM calls through llm-gateway.

CRITICAL: This module uses llm-gateway for all generation. Do NOT
import ChatOpenAI, ChatAnthropic, or any other LLM provider class.
The gateway handles model routing, rate limiting, and cost tracking.
"""

from typing import Any, Dict, List, Optional

import httpx

from rag.config import settings
from rag.vectorstore import SearchResult


# Default RAG prompt template
DEFAULT_RAG_PROMPT = """Answer the question based on the provided context.
If the context does not contain enough information to answer the question,
say so clearly. Do not make up information.

Context:
{context}

Question: {query}

Answer:"""


class GatewayGenerator:
    """LLM generator that routes all calls through llm-gateway.

    This class sends generation requests to llm-gateway instead of
    calling LLM providers directly. The gateway handles:
    - Model selection and routing
    - Rate limiting and cost tracking
    - API key management
    - Audit logging

    Usage:
        generator = GatewayGenerator()
        answer = generator.generate(
            query="What is RAG?",
            context="RAG stands for Retrieval-Augmented Generation..."
        )

    NEVER do this:
        from langchain_openai import ChatOpenAI  # WRONG
        llm = ChatOpenAI(model="gpt-4")          # WRONG
    """

    def __init__(
        self,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        gateway_url: Optional[str] = None,
        gateway_api_key: Optional[str] = None,
        prompt_template: str = DEFAULT_RAG_PROMPT,
    ):
        self.model = model or settings.llm_model
        self.temperature = temperature if temperature is not None else settings.llm_temperature
        self.max_tokens = max_tokens or settings.llm_max_tokens
        self.gateway_url = gateway_url or settings.llm_gateway_url
        self.gateway_api_key = gateway_api_key or settings.llm_gateway_api_key
        self.prompt_template = prompt_template

    def generate(self, query: str, context: str) -> str:
        """Generate an answer using retrieved context via llm-gateway.

        Args:
            query: The user's question.
            context: Retrieved document context to ground the answer.

        Returns:
            The generated answer string.
        """
        prompt = self.prompt_template.format(query=query, context=context)

        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "user", "content": prompt},
            ],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }

        with httpx.Client(timeout=120.0) as client:
            response = client.post(
                f"{self.gateway_url}/v1/chat/completions",
                json=payload,
                headers={
                    "Authorization": f"Bearer {self.gateway_api_key}",
                    "Content-Type": "application/json",
                },
            )
            response.raise_for_status()

        data = response.json()
        return data["choices"][0]["message"]["content"]

    def generate_from_results(
        self,
        query: str,
        results: List[SearchResult],
    ) -> str:
        """Generate an answer from search results.

        Formats search results into a context string and calls generate().

        Args:
            query: The user's question.
            results: Retrieved search results from the vector store.

        Returns:
            The generated answer string.
        """
        context_parts = []
        for i, result in enumerate(results, 1):
            source = result.document.metadata.get("source", "unknown")
            context_parts.append(
                f"[{i}] (source: {source}, score: {result.score:.3f})\n"
                f"{result.document.content}"
            )

        context = "\n\n".join(context_parts)
        return self.generate(query=query, context=context)
