# Discord Bot Patterns

> These patterns describe architectural decisions for the Discord bot template. No implementation is provided in this stub.

## 1. Command Module Auto-Loading

**WHY:** Adding a new command should not require modifying a central registration file. Auto-loading command modules from a directory (each file exports a command definition) keeps command development self-contained. New commands are discovered at startup, reducing merge conflicts and forgotten registrations.

## 2. Interaction Collector Pattern for Multi-Step Flows

**WHY:** Discord interactions (button clicks, select menus) are stateless events. Collectors create a temporary listener scoped to a specific message and user, enabling multi-step flows (pagination, confirmation dialogs, wizards) without global state management. Collectors auto-dispose on timeout, preventing memory leaks.

## 3. Guild-Scoped Configuration

**WHY:** Each Discord server (guild) has different needs -- different prefix, different enabled features, different language. Storing configuration per guild ID and loading it into a cache on startup allows the bot to behave differently across guilds without hardcoding, and gracefully defaults for new guilds.

## 4. Embed Template System

**WHY:** Constructing embeds inline leads to inconsistent formatting and duplicated color/footer/thumbnail code. A template system that provides pre-styled embed builders (success, error, info, paginated list) ensures visual consistency and lets developers focus on content rather than formatting boilerplate.

## 5. Graceful Shard Management

**WHY:** Discord requires bots in over 2,500 guilds to use sharding. Designing the bot's state management to be shard-aware from the start (using IPC for cross-shard queries) prevents a painful rewrite when the bot grows. Even small bots benefit from the architectural discipline this imposes.
