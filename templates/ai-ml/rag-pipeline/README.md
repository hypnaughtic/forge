# RAG Pipeline Template (with llm-gateway)

## Overview

Retrieval-Augmented Generation (RAG) pipeline with abstract interfaces for
vector stores, embeddings, and retrieval strategies. All LLM generation
calls are routed through **llm-gateway** for centralized control.

## What This Template Provides

- **Abstract embedding interface** with pluggable implementations
- **Abstract vector store interface** for storage-agnostic retrieval
- **Configurable retrieval strategies** (similarity, MMR, hybrid)
- **Generation via llm-gateway** — never calls LLM providers directly
- **Full pipeline** orchestrating ingest, retrieval, and generation
- **Chunking utilities** for document preprocessing

## IMPORTANT: llm-gateway Routing

All LLM generation calls go through **llm-gateway**. The generator module
sends requests to your gateway endpoint, which handles model routing,
rate limiting, cost tracking, and API key management.

Do NOT import `ChatOpenAI`, `ChatAnthropic`, or any LangChain/LlamaIndex
provider classes for generation. Use the `GatewayGenerator` class instead.

## Prerequisites

- Python 3.11+
- Access to an llm-gateway instance
- A vector database (Chroma, Pinecone, Weaviate, pgvector, etc.)
- An embedding model endpoint (or use llm-gateway for embeddings)

## Quick Start

```bash
# Copy scaffold to your project
cp -r scaffold/ my-project/
cd my-project/

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your llm-gateway URL and vector DB settings

# Run the pipeline
python -m rag.pipeline
```

## Project Structure

```
rag/
  embeddings.py    # Abstract embedding interface
  vectorstore.py   # Abstract vector store interface
  retriever.py     # Retrieval strategies
  generator.py     # LLM generation via llm-gateway
  pipeline.py      # Full RAG pipeline orchestration
  config.py        # Configuration
```
