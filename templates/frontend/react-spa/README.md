# React SPA Template

## Overview

Modern React single-page application built with TypeScript, Vite, Tailwind CSS,
and React Router. This template provides a fast, type-safe foundation for
building rich client-side applications.

## What This Template Provides

- **React 18** with TypeScript for type-safe component development
- **Vite** for lightning-fast dev server and optimized production builds
- **Tailwind CSS** for utility-first styling without CSS-in-JS overhead
- **React Router v6** with route-based code splitting
- **Abstract API client** ready to connect to any backend
- **Layout system** with composable page structure
- **Environment configuration** via Vite env variables

## Prerequisites

- Node.js 20+ (LTS recommended)

## Quick Start

```bash
# Copy scaffold to your project
cp -r scaffold/ my-project/
cd my-project/

# Install dependencies
npm install

# Copy and configure environment
cp .env.example .env
# Edit .env with your API URL

# Start development server
npm run dev
```

The application will be available at `http://localhost:5173`.

## Build for Production

```bash
npm run build
npm run preview   # preview the production build locally
```

## Project Structure

```
src/
  App.tsx              # Main app with router setup
  main.tsx             # Application entry point
  api/                 # API client abstraction
  components/          # Shared UI components
```

## Adding New Pages

1. Create a component in `src/pages/`
2. Add a route in `src/App.tsx`
3. Use `React.lazy()` for automatic code splitting
