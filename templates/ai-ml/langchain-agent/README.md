# LangChain Agent Template (with llm-gateway)

## Overview

LangChain/LangGraph agent that routes all LLM calls through **llm-gateway**
instead of using LangChain's native provider integrations. This ensures
centralized rate limiting, cost tracking, model routing, and audit logging
through your organization's LLM gateway.

## What This Template Provides

- **GatewayLLM** class that implements LangChain's `BaseChatModel` interface
  while routing all calls through llm-gateway
- **LangGraph** agent with tool-calling capabilities
- **Example tools** demonstrating the agent-tool pattern
- **Configuration** module for gateway and agent settings
- **llm-gateway integration** as the single LLM access path

## IMPORTANT: llm-gateway Routing

This template does **NOT** use LangChain's native LLM providers
(`ChatOpenAI`, `ChatAnthropic`, etc.). All LLM calls go through
`llm-gateway`, which handles:

- Model selection and routing
- Rate limiting and cost tracking
- API key management
- Audit logging and observability

The `GatewayLLM` class in `agent/gateway_llm.py` is the bridge between
LangChain's expected interface and llm-gateway.

## Prerequisites

- Python 3.11+
- Access to an llm-gateway instance
- llm-gateway API key

## Quick Start

```bash
# Copy scaffold to your project
cp -r scaffold/ my-project/
cd my-project/

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your llm-gateway URL and API key

# Run the agent
python -m agent.agent
```

## Project Structure

```
agent/
  gateway_llm.py   # BaseChatModel implementation routing through llm-gateway
  agent.py          # LangGraph agent definition
  tools.py          # Agent tools
  config.py         # Configuration
```
