# VS Code Extension Patterns

> These patterns describe architectural decisions for the VS Code extension template. No implementation is provided in this stub.

## 1. Language Server Protocol Separation

**WHY:** Implementing language features (completions, diagnostics, hover) directly in the extension ties them to VS Code. Using LSP separates the language intelligence into a standalone server that can be reused by Neovim, Sublime Text, and other editors. This doubles the audience for the language features without duplicating code.

## 2. Disposable Resource Management

**WHY:** VS Code extensions activate and deactivate throughout the editor's lifecycle. Registering all subscriptions, watchers, and connections as disposables and pushing them to context.subscriptions ensures automatic cleanup when the extension deactivates. Failing to dispose resources causes memory leaks that degrade editor performance over time.

## 3. Lazy Activation with Activation Events

**WHY:** Extensions that activate on startup slow down VS Code's launch time, frustrating users who may not need the extension for every session. Declaring specific activation events (onLanguage, onCommand, workspaceContains) ensures the extension loads only when relevant, keeping the editor fast for all users.

## 4. Webview Security with Content Security Policy

**WHY:** Webview panels execute arbitrary HTML/JS within VS Code, creating an XSS attack surface. A strict Content Security Policy that whitelists only extension-bundled resources and uses nonces for inline scripts prevents malicious content injection, which is especially critical for extensions that render user-provided or network-fetched content.

## 5. Configuration-Driven Feature Toggles

**WHY:** Users have different needs and workflows. Exposing extension behavior through VS Code's settings system (contributes.configuration in package.json) lets users customize the extension without modifying code, and the settings UI provides discoverability. Reacting to configuration changes in real-time avoids requiring editor restarts.
