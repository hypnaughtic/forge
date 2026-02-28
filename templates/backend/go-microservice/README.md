# Go Microservice Template (STUB)

> **Status:** Stub template -- not yet scaffolded. This document describes what a full implementation would provide.

## Overview

A production-ready Go microservice using Gin for HTTP routing, GORM for database access, and clean architecture principles. Packaged with Docker multi-stage builds for minimal container images.

## What a Full Scaffold Would Provide

- **Project structure** following clean architecture (domain, usecase, repository, handler layers)
- **Gin HTTP server** with middleware for logging, CORS, rate limiting, and request ID tracing
- **GORM integration** with migrations, connection pooling, and repository pattern
- **Docker multi-stage build** producing a minimal scratch-based container
- **Health check endpoints** (liveness and readiness probes)
- **Configuration management** via environment variables and config files
- **Structured logging** with slog or zerolog
- **Graceful shutdown** handling OS signals
- **OpenAPI/Swagger** documentation generation
- **Unit and integration test** scaffolding with testify
- **Makefile** with build, test, lint, and docker targets
- **CI/CD pipeline** configuration (GitHub Actions)

## Key Technologies

| Component       | Technology          |
|----------------|---------------------|
| Language        | Go 1.22+           |
| HTTP Framework  | Gin                |
| ORM             | GORM               |
| Containerization| Docker multi-stage |
| Testing         | testify, httptest  |
