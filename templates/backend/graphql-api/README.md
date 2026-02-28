# GraphQL API Template (STUB)

> **Status:** Stub template -- not yet scaffolded. This document describes what a full implementation would provide.

## Overview

A GraphQL API server supporting both TypeScript (Apollo Server) and Python (Strawberry) implementations, with DataLoader for efficient batched data fetching and N+1 query prevention.

## What a Full Scaffold Would Provide

- **Schema-first or code-first** GraphQL API with type-safe resolvers
- **DataLoader integration** for automatic batching and caching of database queries
- **Authentication and authorization** middleware with directive-based access control
- **Subscription support** via WebSockets for real-time features
- **Query complexity analysis** to prevent abusive queries
- **Automatic schema documentation** and GraphQL Playground/Explorer
- **Pagination** using cursor-based connections (Relay spec)
- **Error handling** with structured GraphQL error types
- **Database integration** with Prisma (TS) or SQLAlchemy (Python)
- **Testing utilities** for resolver unit tests and integration tests
- **Code generation** for TypeScript types from schema

## Key Technologies

| Component       | Technology (TS)     | Technology (Python) |
|----------------|---------------------|---------------------|
| Framework       | Apollo Server       | Strawberry          |
| Data Loading    | DataLoader          | Strawberry DataLoader|
| Database        | Prisma              | SQLAlchemy          |
| Auth            | JWT / OAuth2        | JWT / OAuth2        |
