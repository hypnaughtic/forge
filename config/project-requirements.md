# MVP Chatbot — Project Requirements

## Overview
Build an MVP real-time chatbot application with a FastAPI backend, a simple
HTML/JS frontend, and LLM integration via the llm-gateway plugin using
local-claude sessions.

## Target Users
- Developers who want a quick chatbot prototype to test LLM interactions.
- Internal teams evaluating Claude via local-claude integration.

## Features

### Backend (FastAPI)
1. **POST /api/chat** — Send a user message, receive an LLM-generated response.
   - Request: `{ "message": "...", "session_id": "..." }`
   - Response: `{ "reply": "...", "session_id": "...", "tokens_used": N }`
2. **GET /api/chat/history/{session_id}** — Retrieve conversation history.
3. **DELETE /api/chat/history/{session_id}** — Clear a conversation.
4. **GET /api/health** — Health check endpoint.
5. In-memory session store (dict) is acceptable for MVP.

### Frontend (HTML + Vanilla JS)
1. Single-page chat UI served at `GET /`.
2. Message input box, send button, scrollable message list.
3. Messages styled with user/assistant distinction (left/right bubbles).
4. Session ID generated client-side (UUID) and persisted in localStorage.
5. Loading spinner while waiting for LLM response.

### LLM Integration (llm-gateway + local-claude)
1. All LLM calls go through the llm-gateway plugin — no direct SDK usage.
2. Use `local-claude` mode so the chatbot invokes the local Claude CLI for
   inference during development and testing.
3. Configurable model via environment variable `LLM_GATEWAY_MODEL`
   (default: `claude-sonnet-4-20250514`).

## Technical Constraints
- Python 3.11+, FastAPI, uvicorn.
- No database — in-memory storage only.
- Serve static frontend from FastAPI's `StaticFiles`.
- Single `docker-compose.yml` for local dev.
- `.env` file for config (model name, port, etc.).

## Non-Functional Requirements
- Response latency: <5 s for typical messages (depends on LLM).
- Basic structured logging (structlog).
- Type-annotated code, Pydantic models for request/response.
