# RAG Pipeline — Architectural Patterns

This document explains the patterns used in this template and **why** each
one was chosen. The llm-gateway routing for generation is critical — read
that section first.

---

## 1. llm-gateway for Generation (CRITICAL)

**What:** All LLM generation calls (answer synthesis, summarization,
reranking prompts) are routed through llm-gateway. The `GatewayGenerator`
class sends HTTP requests to the gateway endpoint instead of calling LLM
provider APIs directly.

**Why this pattern:**

- **Centralized control** — Rate limiting, cost tracking, API key
  management, and model routing are handled by the gateway, not by
  application code.
- **Provider independence** — Switch between GPT-4, Claude, Llama, or
  any model by changing gateway configuration. No code changes needed.
- **Audit and compliance** — Every generation request is logged by the
  gateway, providing a complete audit trail of LLM usage.
- **Cost management** — The gateway tracks token usage and costs across
  all applications, enabling budgeting and alerting.

**How it works:**

```python
# WRONG — bypasses llm-gateway:
from langchain_openai import ChatOpenAI
llm = ChatOpenAI(model="gpt-4")

# CORRECT — routes through llm-gateway:
from rag.generator import GatewayGenerator
generator = GatewayGenerator()
answer = generator.generate(query="...", context="...")
```

---

## 2. Chunking Strategies

**What:** Documents are split into chunks before embedding. The pipeline
supports multiple strategies: fixed-size, recursive text splitting,
semantic chunking, and sentence-based splitting.

**Why this pattern:**

- **Retrieval quality** — Chunk size directly affects retrieval relevance.
  Too large and the chunk contains irrelevant noise. Too small and context
  is lost.
- **Embedding model limits** — Most embedding models have token limits
  (512-8192 tokens). Chunks must fit within these limits.
- **Strategy flexibility** — Different document types benefit from different
  strategies. Code files need different chunking than prose documents.

**Recommended defaults:**
- Chunk size: 512-1024 tokens for general text
- Overlap: 10-20% of chunk size to preserve context across boundaries
- Use recursive splitting for heterogeneous documents

---

## 3. Embedding Abstraction

**What:** The `EmbeddingProvider` abstract class defines a uniform interface
for generating embeddings. Concrete implementations wrap specific providers
(OpenAI, Sentence Transformers, Cohere, or llm-gateway embeddings).

**Why this pattern:**

- **Provider flexibility** — Switch embedding models without changing
  retrieval or indexing code.
- **Testing** — Use a mock embedding provider that returns deterministic
  vectors for unit tests.
- **Cost optimization** — Start with a cheap/local model, upgrade to a
  premium model when needed. The interface stays the same.

---

## 4. Vector Store Abstraction

**What:** The `VectorStore` abstract class defines operations for storing
and querying document embeddings. Concrete implementations wrap specific
databases (Chroma, Pinecone, Weaviate, pgvector).

**Why this pattern:**

- **Database independence** — Evaluate different vector databases without
  rewriting retrieval logic.
- **Hybrid search** — The interface supports both vector similarity and
  metadata filtering, enabling hybrid retrieval strategies.
- **Scaling path** — Start with an in-memory store (Chroma) for
  development, move to a managed service (Pinecone) for production.

---

## 5. Retrieval Strategies

**What:** The retriever supports multiple strategies: plain similarity
search, Maximum Marginal Relevance (MMR), and hybrid (vector + keyword).

**Why this pattern:**

- **Similarity search** — Fast and simple. Best for well-defined queries
  with clear semantic matches.
- **MMR (Maximum Marginal Relevance)** — Balances relevance with diversity.
  Prevents returning five near-duplicate chunks when the user needs breadth.
- **Hybrid retrieval** — Combines dense vector search with sparse keyword
  matching (BM25). Catches exact-match terms that embedding models might
  miss (product IDs, error codes, names).

The strategy is configurable per query, allowing the pipeline to adapt
to different query types.

---

## 6. Pipeline Orchestration

**What:** The `RAGPipeline` class orchestrates the full flow: receive query,
retrieve relevant chunks, format context, generate answer via llm-gateway.

**Why this pattern:**

- **Single entry point** — Callers interact with one class, not with
  individual components.
- **Configuration over code** — Pipeline behavior (chunk count, retrieval
  strategy, model selection) is controlled via configuration, not code
  changes.
- **Observability** — The pipeline logs each stage (retrieval time, chunk
  count, generation time), making performance issues easy to diagnose.
