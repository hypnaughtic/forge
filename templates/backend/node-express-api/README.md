# Node.js Express API Template

## Overview

Production-ready Express.js backend with TypeScript, Prisma ORM, and JWT
authentication. This template provides a structured, type-safe foundation
for building REST APIs with Node.js.

## What This Template Provides

- **Express.js** with TypeScript for type-safe API development
- **Prisma** ORM for type-safe database access and migrations
- **JWT authentication** middleware ready for integration
- **Zod** for runtime request validation and DTO definitions
- **Structured error handling** with centralized error middleware
- **Docker** setup with docker-compose for local development
- **Health check** endpoint for container orchestration

## Prerequisites

- Node.js 20+ (LTS recommended)
- PostgreSQL 15+ (or use the provided docker-compose)
- Docker and Docker Compose (optional)

## Quick Start

```bash
# Copy scaffold to your project
cp -r scaffold/ my-project/
cd my-project/

# Install dependencies
npm install

# Copy and configure environment
cp .env.example .env
# Edit .env with your database credentials

# Generate Prisma client
npx prisma generate

# Run database migrations
npx prisma migrate dev

# Start development server
npm run dev
```

## Docker Quick Start

```bash
cp .env.example .env
docker-compose up --build
```

The API will be available at `http://localhost:3000`.

## Project Structure

```
src/
  index.ts             # Express application entry point
  config/              # Environment and app configuration
  middleware/           # Express middleware (error handling, auth)
  routes/              # Route handlers
```
