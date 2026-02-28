# Next.js Fullstack Template

## Overview

Production-ready fullstack application using Next.js App Router with server
components, Prisma ORM for database access, and NextAuth.js for authentication.
This template provides a unified frontend and backend in a single deployable unit.

## What This Template Provides

- **Next.js 14** App Router with React Server Components
- **Prisma** ORM for type-safe database access and migrations
- **NextAuth.js** v5 for flexible authentication (OAuth, credentials, etc.)
- **Server Actions** for type-safe server mutations without API routes
- **Server Components** by default for optimal performance
- **Health check API** route for container orchestration
- **TypeScript** throughout for full type safety

## Prerequisites

- Node.js 20+ (LTS recommended)
- PostgreSQL 15+ (or use a hosted provider)

## Quick Start

```bash
# Copy scaffold to your project
cp -r scaffold/ my-project/
cd my-project/

# Install dependencies
npm install

# Copy and configure environment
cp .env.example .env
# Edit .env with your database and auth credentials

# Generate Prisma client and run migrations
npx prisma generate
npx prisma migrate dev

# Start development server
npm run dev
```

The application will be available at `http://localhost:3000`.

## Build for Production

```bash
npm run build
npm start
```

## Project Structure

```
src/
  app/
    layout.tsx           # Root layout (server component)
    page.tsx             # Home page
    api/health/route.ts  # Health check API
  lib/
    db.ts                # Prisma client singleton
    auth.ts              # NextAuth configuration
prisma/
  schema.prisma          # Database schema
```
