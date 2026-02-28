"""
Retrieval strategies for the RAG pipeline.

Supports similarity search, Maximum Marginal Relevance (MMR), and
configurable top-k retrieval.
"""

from enum import Enum
from typing import Any, Dict, List, Optional

from rag.embeddings import EmbeddingProvider
from rag.vectorstore import SearchResult, VectorStore


class RetrievalStrategy(str, Enum):
    """Available retrieval strategies."""
    SIMILARITY = "similarity"
    MMR = "mmr"


class Retriever:
    """Retrieves relevant document chunks from the vector store.

    Supports multiple retrieval strategies and metadata filtering.
    """

    def __init__(
        self,
        vector_store: VectorStore,
        embedding_provider: EmbeddingProvider,
        default_top_k: int = 5,
        default_strategy: RetrievalStrategy = RetrievalStrategy.SIMILARITY,
    ):
        self.vector_store = vector_store
        self.embedding_provider = embedding_provider
        self.default_top_k = default_top_k
        self.default_strategy = default_strategy

    def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
        strategy: Optional[RetrievalStrategy] = None,
        filter_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[SearchResult]:
        """Retrieve relevant documents for a query.

        Args:
            query: The user's question or search query.
            top_k: Number of results to return.
            strategy: Retrieval strategy to use.
            filter_metadata: Metadata filters to apply.

        Returns:
            List of search results ranked by relevance.
        """
        k = top_k or self.default_top_k
        strat = strategy or self.default_strategy

        # Generate query embedding
        query_embedding = self.embedding_provider.embed_text(query)

        if strat == RetrievalStrategy.SIMILARITY:
            return self._similarity_search(
                query_embedding, k, filter_metadata
            )
        elif strat == RetrievalStrategy.MMR:
            return self._mmr_search(
                query_embedding, k, filter_metadata
            )
        else:
            raise ValueError(f"Unknown retrieval strategy: {strat}")

    def _similarity_search(
        self,
        query_embedding: List[float],
        top_k: int,
        filter_metadata: Optional[Dict[str, Any]],
    ) -> List[SearchResult]:
        """Plain cosine similarity search."""
        return self.vector_store.search(
            query_embedding=query_embedding,
            top_k=top_k,
            filter_metadata=filter_metadata,
        )

    def _mmr_search(
        self,
        query_embedding: List[float],
        top_k: int,
        filter_metadata: Optional[Dict[str, Any]],
        lambda_mult: float = 0.5,
        fetch_k: int = 20,
    ) -> List[SearchResult]:
        """Maximum Marginal Relevance search.

        Balances relevance to the query with diversity among results,
        reducing redundancy in retrieved chunks.
        """
        # Fetch more candidates than needed
        candidates = self.vector_store.search(
            query_embedding=query_embedding,
            top_k=fetch_k,
            filter_metadata=filter_metadata,
        )

        if not candidates:
            return []

        # Greedy MMR selection
        selected: List[SearchResult] = []
        remaining = list(candidates)

        while len(selected) < top_k and remaining:
            best_score = -1.0
            best_idx = 0

            for i, candidate in enumerate(remaining):
                # Relevance to query
                relevance = candidate.score

                # Max similarity to already selected documents
                if selected:
                    max_sim = max(
                        self._cosine_sim(
                            candidate.document.embedding,
                            s.document.embedding,
                        )
                        for s in selected
                    )
                else:
                    max_sim = 0.0

                # MMR score: balance relevance and diversity
                mmr_score = lambda_mult * relevance - (1 - lambda_mult) * max_sim

                if mmr_score > best_score:
                    best_score = mmr_score
                    best_idx = i

            selected.append(remaining.pop(best_idx))

        return selected

    @staticmethod
    def _cosine_sim(a: List[float], b: List[float]) -> float:
        if len(a) != len(b) or not a:
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        na = sum(x * x for x in a) ** 0.5
        nb = sum(x * x for x in b) ** 0.5
        if na == 0 or nb == 0:
            return 0.0
        return dot / (na * nb)
