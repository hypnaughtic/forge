# Temporal AI Workflow Template (STUB)

> **Status:** Stub template -- not yet scaffolded. This document describes what a full implementation would provide.

## Overview

Production-ready AI pipeline orchestration using Temporal durable workflows with llm-gateway integration. Activities wrap llm-gateway calls; workflows never call LLMs directly. Supports complex multi-step AI pipelines with retry, timeout, and human-in-the-loop patterns.

## What a Full Scaffold Would Provide

- **Temporal workflows** for orchestrating multi-step AI pipelines
- **Activity implementations** that wrap llm-gateway for all model interactions
- **LLM-gateway integration** as the exclusive interface for model calls
- **Retry and timeout policies** tuned for LLM call characteristics
- **Human-in-the-loop** signal handling for approval gates
- **Pipeline patterns** for RAG, chain-of-thought, and multi-model routing
- **Observability** with workflow history, activity metrics, and cost tracking
- **Error handling** with compensating actions for partial pipeline failures
- **Testing** with Temporal test framework and mocked activities
- **Worker configuration** with concurrency limits and task queue routing
- **Docker Compose** with Temporal server, workers, and llm-gateway

## Key Technologies

| Component       | Technology          |
|----------------|---------------------|
| Orchestration   | Temporal            |
| LLM Access      | llm-gateway         |
| Languages       | Python, TypeScript  |
| Observability   | Temporal UI, OpenTelemetry |

## Important Constraint

Activities wrap llm-gateway; workflows NEVER call LLMs directly. This ensures all model interactions are retryable, observable, and cost-tracked.
