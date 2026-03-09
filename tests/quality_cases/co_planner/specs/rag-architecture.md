# RAG Architecture Specification

> **Status: Partially superseded.** The HybridRetriever (vector + keyword search) has been replaced by the [GraphNativeRetriever](graph-native-retrieval.md) (WL hash + VF2 + GED + keyword). See ADR-007. The EmbeddingClient and PatternCorpus sections below remain relevant for legacy corpus text storage. The HybridRetriever code is kept as fallback but is no longer wired into the pipeline.

## Overview

The RAG (Retrieval-Augmented Generation) system enriches LLM prompts with similar patterns from a corpus of known flowchart fragments. This improves suggestion quality by providing domain-relevant examples.

## Components

### EmbeddingClient (Protocol)
- **Interface**: `async embed(texts: list[str]) -> list[list[float]]`
- **OpenAI implementation**: Uses `text-embedding-3-small` (1536 dimensions) via httpx
- **Fake implementation**: Deterministic SHA-256-based vectors for testing
- **Concurrency**: Bounded by `asyncio.Semaphore(5)`
- **Retry**: 3 attempts with exponential backoff on HTTP errors

### HybridRetriever
Combines two search strategies for better recall:

1. **Vector Search**
   - Serialize 2-hop neighborhood → embed → cosine similarity search in pgvector
   - Threshold: 0.6 (relatively permissive to allow diverse results)
   - Returns: (pattern_text, similarity_score)

2. **Keyword Search**
   - Extract node labels from neighborhood → PostgreSQL array overlap (`&&`)
   - Compute Jaccard-like overlap score
   - Returns: (pattern_text, overlap_score)

3. **Merge**: Deduplicate by pattern text prefix, sort by score, return top-K (default 5)

### PatternCorpus
Manages corpus ingestion:

1. **Global Seeding** (`seed_global_corpus`):
   - Reads existing JSON template files (10 templates)
   - Extracts 3-5 node subpaths from each template
   - Embeds and stores in `pattern_embeddings` table

2. **User Pattern Growth** (`ingest_subpaths`):
   - When a user accepts a suggestion, the resulting subpath is extracted
   - Embedded and stored with `source="user"` and `user_id`
   - Organic corpus growth from user interactions

### Subpath Extraction
- BFS from each node, collecting paths of length 3-5
- Avoids cycles within paths
- Deduplicates by canonical serialization (sorted labels + edges)
- Each path becomes a separate corpus entry

## Database Schema

```sql
CREATE TABLE pattern_embeddings (
    id UUID PRIMARY KEY,
    subgraph_text TEXT NOT NULL,          -- canonical serialized subgraph
    embedding vector(1536) NOT NULL,      -- OpenAI text-embedding-3-small
    node_labels TEXT[] NOT NULL,          -- for keyword search
    domain VARCHAR(100) DEFAULT 'flowchart',
    source VARCHAR(20) DEFAULT 'global', -- 'global' or 'user'
    user_id VARCHAR(255),                -- null for global patterns
    created_at TIMESTAMPTZ DEFAULT now()
);
```

## Prompt Integration

Retrieved patterns are injected into the LLM user prompt as:

```
## Similar Patterns from Corpus
- (score: 0.85, source: global)
NODES: Clean Data | Extract Data | Transform Data
EDGES:
  Clean Data -> Transform Data
  Extract Data -> Clean Data
```
