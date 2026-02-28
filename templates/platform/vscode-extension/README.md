# VS Code Extension Template (STUB)

> **Status:** Stub template -- not yet scaffolded. This document describes what a full implementation would provide.

## Overview

A Visual Studio Code extension with Language Server Protocol (LSP) support, built with TypeScript. Provides commands, code actions, diagnostics, and IntelliSense features with a robust extension development workflow.

## What a Full Scaffold Would Provide

- **Extension activation** with event-based triggers and disposable management
- **LSP server** with document synchronization, diagnostics, and completions
- **Commands** registered in package.json with keybindings
- **Code actions** and quick fixes for automated refactoring
- **Webview panels** for rich custom UI within VS Code
- **Tree view** providers for sidebar navigation
- **Configuration** schema with settings UI integration
- **Status bar** items with interactive feedback
- **Testing** with @vscode/test-electron for integration tests
- **Debugging** launch configurations for extension and LSP
- **Packaging** with vsce for marketplace publishing
- **CI/CD** pipeline for automated testing and publishing

## Key Technologies

| Component       | Technology          |
|----------------|---------------------|
| Language        | TypeScript          |
| Protocol        | Language Server Protocol |
| LSP Library     | vscode-languageserver |
| Testing         | @vscode/test-electron |
| Packaging       | vsce                |
