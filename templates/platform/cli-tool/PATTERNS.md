# CLI Tool Patterns

> These patterns describe architectural decisions for the CLI tool template. No implementation is provided in this stub.

## 1. Subcommand Hierarchy with Plugin Architecture

**WHY:** A flat list of commands becomes unnavigable as the tool grows. Grouping related commands under subcommands (e.g., `tool db migrate`, `tool db seed`) provides natural organization. A plugin architecture allows third-party or internal extensions to register new subcommands without modifying the core CLI, enabling ecosystem growth.

## 2. Configuration Cascade (Flags > Env > File > Defaults)

**WHY:** Different deployment contexts need different configuration sources. CI/CD prefers environment variables, developers prefer config files, and one-off usage needs flags. A consistent cascade (flags override env vars override config files override defaults) ensures predictable behavior while supporting all use cases without special-casing.

## 3. Structured Output with Machine-Readable Modes

**WHY:** CLIs serve both humans and scripts. Defaulting to colored, formatted output for terminals while supporting --json and --yaml flags for piping to jq or other tools makes the CLI useful in automation without sacrificing the interactive experience. Detecting TTY to auto-switch formatting prevents garbled output in pipelines.

## 4. Progressive Disclosure of Complexity

**WHY:** New users are overwhelmed by tools that expose every option upfront. Showing essential options in --help while hiding advanced ones behind --help-all, and using interactive prompts for missing required inputs, creates a gentle learning curve. Power users can always bypass prompts with flags for scriptability.

## 5. Idempotent Commands by Default

**WHY:** Users frequently re-run CLI commands after interruptions or errors. Commands that check current state before acting (e.g., "already migrated, skipping") are safe to retry without unintended side effects. This builds trust and reduces the anxiety of running commands in production environments.
