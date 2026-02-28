# Slack Bot Patterns

> These patterns describe architectural decisions for the Slack bot template. No implementation is provided in this stub.

## 1. Event-Driven Handler Registration

**WHY:** Slack sends diverse event types (messages, reactions, slash commands, interactive actions) that need different processing logic. Registering dedicated handlers per event type (app.message, app.command, app.action) keeps each handler focused and testable, rather than building a monolithic event router with conditional branches.

## 2. Socket Mode for Development, HTTP for Production

**WHY:** Slack's Events API requires a publicly accessible URL, which is cumbersome during local development (ngrok, tunnels). Socket Mode uses WebSocket connections that work behind firewalls without URL exposure. Using Socket Mode locally and HTTP events in production gives the best of both worlds without code changes.

## 3. Acknowledge-Then-Process Pattern

**WHY:** Slack requires a 3-second response to interactions or it shows an error to the user. Immediately acknowledging the request and processing the work asynchronously (then updating the message) prevents timeout errors for any operation that takes more than a moment, which is virtually every useful operation.

## 4. Block Kit Composition Functions

**WHY:** Constructing Block Kit JSON manually is verbose and error-prone. Wrapping common message patterns (success card, error card, form, table) in composition functions ensures visual consistency across the bot, reduces code duplication, and makes it easy to update the bot's visual style in one place.

## 5. Workspace-Scoped State Management

**WHY:** Multi-workspace bots must isolate configuration and data per workspace. Scoping all state (settings, user preferences, cached data) by workspace ID prevents cross-workspace data leakage and allows per-workspace customization. This is the Slack equivalent of multi-tenant architecture.
