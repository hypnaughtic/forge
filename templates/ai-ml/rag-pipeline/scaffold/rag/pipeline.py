"""
Full RAG pipeline orchestrating ingest, retrieval, and generation.

All LLM generation is routed through llm-gateway via the GatewayGenerator.
"""

import logging
import time
import uuid
from typing import Any, Dict, List, Optional

from rag.config import settings
from rag.embeddings import EmbeddingProvider, GatewayEmbeddingProvider
from rag.generator import GatewayGenerator
from rag.retriever import Retriever, RetrievalStrategy
from rag.vectorstore import Document, InMemoryVectorStore, SearchResult, VectorStore

logger = logging.getLogger(__name__)


class RAGPipeline:
    """Orchestrates the full RAG flow: ingest, retrieve, generate.

    Usage:
        pipeline = RAGPipeline()

        # Ingest documents
        pipeline.ingest(["Document content 1", "Document content 2"])

        # Query
        answer = pipeline.query("What is RAG?")
    """

    def __init__(
        self,
        vector_store: Optional[VectorStore] = None,
        embedding_provider: Optional[EmbeddingProvider] = None,
        generator: Optional[GatewayGenerator] = None,
        chunk_size: int = 0,
        chunk_overlap: int = 0,
        top_k: int = 0,
        retrieval_strategy: Optional[RetrievalStrategy] = None,
    ):
        self.embedding_provider = embedding_provider or GatewayEmbeddingProvider()
        self.vector_store = vector_store or InMemoryVectorStore()
        self.generator = generator or GatewayGenerator()
        self.chunk_size = chunk_size or settings.chunk_size
        self.chunk_overlap = chunk_overlap or settings.chunk_overlap
        self.top_k = top_k or settings.retrieval_top_k

        self.retriever = Retriever(
            vector_store=self.vector_store,
            embedding_provider=self.embedding_provider,
            default_top_k=self.top_k,
            default_strategy=retrieval_strategy or RetrievalStrategy.SIMILARITY,
        )

    def ingest(
        self,
        texts: List[str],
        metadata: Optional[List[Dict[str, Any]]] = None,
    ) -> int:
        """Ingest documents into the vector store.

        Chunks the texts, generates embeddings, and stores them.

        Args:
            texts: List of document texts to ingest.
            metadata: Optional metadata for each document.

        Returns:
            Number of chunks stored.
        """
        start = time.time()
        all_chunks: List[Document] = []

        for i, text in enumerate(texts):
            doc_metadata = metadata[i] if metadata and i < len(metadata) else {}
            chunks = self._chunk_text(text)

            for j, chunk in enumerate(chunks):
                doc = Document(
                    id=str(uuid.uuid4()),
                    content=chunk,
                    metadata={
                        **doc_metadata,
                        "chunk_index": j,
                        "total_chunks": len(chunks),
                    },
                )
                all_chunks.append(doc)

        # Generate embeddings in batch
        contents = [doc.content for doc in all_chunks]
        embeddings = self.embedding_provider.embed_batch(contents)
        for doc, embedding in zip(all_chunks, embeddings):
            doc.embedding = embedding

        # Store in vector store
        self.vector_store.add_documents(all_chunks)

        elapsed = time.time() - start
        logger.info(
            f"Ingested {len(texts)} documents into {len(all_chunks)} chunks "
            f"in {elapsed:.2f}s"
        )
        return len(all_chunks)

    def query(
        self,
        question: str,
        top_k: Optional[int] = None,
        strategy: Optional[RetrievalStrategy] = None,
        filter_metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Run the full RAG pipeline: retrieve then generate.

        Args:
            question: The user's question.
            top_k: Number of chunks to retrieve.
            strategy: Retrieval strategy to use.
            filter_metadata: Metadata filters for retrieval.

        Returns:
            Generated answer grounded in retrieved context.
        """
        start = time.time()

        # Retrieve relevant chunks
        results = self.retriever.retrieve(
            query=question,
            top_k=top_k,
            strategy=strategy,
            filter_metadata=filter_metadata,
        )

        if not results:
            return "No relevant documents found to answer your question."

        # Generate answer via llm-gateway
        answer = self.generator.generate_from_results(
            query=question,
            results=results,
        )

        elapsed = time.time() - start
        logger.info(
            f"RAG query completed in {elapsed:.2f}s "
            f"(retrieved {len(results)} chunks)"
        )
        return answer

    def _chunk_text(self, text: str) -> List[str]:
        """Split text into overlapping chunks.

        Uses a simple character-based splitter. Replace with a more
        sophisticated strategy (recursive, semantic) for production use.
        """
        if len(text) <= self.chunk_size:
            return [text]

        chunks = []
        start = 0
        while start < len(text):
            end = start + self.chunk_size
            chunk = text[start:end]
            chunks.append(chunk)
            start = end - self.chunk_overlap

        return chunks


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    pipeline = RAGPipeline()

    # Example: ingest some documents
    docs = [
        "Retrieval-Augmented Generation (RAG) combines information retrieval "
        "with language model generation. It retrieves relevant documents from "
        "a knowledge base and uses them as context for generating answers.",
        "Vector databases store document embeddings as high-dimensional vectors "
        "and support fast similarity search. Popular options include Chroma, "
        "Pinecone, Weaviate, and pgvector.",
    ]
    pipeline.ingest(docs, metadata=[{"source": "intro"}, {"source": "vector-db"}])

    # Example: query
    answer = pipeline.query("What is RAG?")
    print(f"Answer: {answer}")
