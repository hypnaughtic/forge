"""
Abstract vector store interface for storage-agnostic retrieval.

Provides a uniform API for storing and querying document embeddings
regardless of the underlying vector database.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Document:
    """A document chunk with its content, embedding, and metadata."""
    id: str
    content: str
    embedding: List[float] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SearchResult:
    """A search result with document and similarity score."""
    document: Document
    score: float


class VectorStore(ABC):
    """Abstract base class for vector store implementations."""

    @abstractmethod
    def add_documents(self, documents: List[Document]) -> None:
        """Store documents with their embeddings."""
        raise NotImplementedError

    @abstractmethod
    def search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[SearchResult]:
        """Search for similar documents by embedding vector."""
        raise NotImplementedError

    @abstractmethod
    def delete(self, document_ids: List[str]) -> None:
        """Delete documents by their IDs."""
        raise NotImplementedError


class InMemoryVectorStore(VectorStore):
    """Simple in-memory vector store for development and testing.

    Uses cosine similarity for search. Not suitable for production
    workloads — replace with Chroma, Pinecone, Weaviate, or pgvector.
    """

    def __init__(self):
        self._documents: Dict[str, Document] = {}

    def add_documents(self, documents: List[Document]) -> None:
        for doc in documents:
            self._documents[doc.id] = doc

    def search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[SearchResult]:
        results = []
        for doc in self._documents.values():
            # Apply metadata filter if provided
            if filter_metadata:
                if not all(
                    doc.metadata.get(k) == v
                    for k, v in filter_metadata.items()
                ):
                    continue

            score = self._cosine_similarity(query_embedding, doc.embedding)
            results.append(SearchResult(document=doc, score=score))

        # Sort by score descending and return top_k
        results.sort(key=lambda r: r.score, reverse=True)
        return results[:top_k]

    def delete(self, document_ids: List[str]) -> None:
        for doc_id in document_ids:
            self._documents.pop(doc_id, None)

    @staticmethod
    def _cosine_similarity(a: List[float], b: List[float]) -> float:
        if len(a) != len(b) or not a:
            return 0.0
        dot_product = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot_product / (norm_a * norm_b)
