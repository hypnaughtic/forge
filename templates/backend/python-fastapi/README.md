# Python FastAPI Backend Template

## Overview

Production-ready FastAPI backend with SQLAlchemy ORM, Alembic migrations,
and Pydantic v2 for data validation. This template provides a clean,
async-first architecture suitable for building REST APIs at any scale.

## What This Template Provides

- **FastAPI** application with automatic OpenAPI documentation
- **SQLAlchemy 2.0** with async session support and declarative models
- **Alembic** for database schema migrations
- **Pydantic v2** for request/response validation and settings management
- **Repository pattern** for clean data access abstraction
- **Dependency injection** via FastAPI's built-in DI system
- **Docker** multi-stage build with docker-compose for local development
- **Health check** endpoint for container orchestration readiness

## Prerequisites

- Python 3.11+
- PostgreSQL 15+ (or use the provided docker-compose)
- Docker and Docker Compose (optional, for containerized development)

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

# Copy and configure environment
cp .env.example .env
# Edit .env with your database credentials

# Run the application
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Docker Quick Start

```bash
cp .env.example .env
docker-compose up --build
```

The API will be available at `http://localhost:8000`.
OpenAPI docs are served at `http://localhost:8000/docs`.

## Project Structure

```
app/
  main.py           # FastAPI application entry point
  config.py          # Settings via pydantic-settings
  models/            # SQLAlchemy ORM models
  repositories/      # Data access layer (repository pattern)
  routers/           # API route handlers
```
