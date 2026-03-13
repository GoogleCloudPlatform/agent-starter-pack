# AG2 Multi-Agent with A2A Protocol

<p align="center">
  <img src="https://raw.githubusercontent.com/ag2ai/ag2/refs/heads/main/website/static/img/ag2.svg" width="50%" alt="AG2 Logo" style="margin-right: 40px; vertical-align: middle;">
  <img src="https://github.com/a2aproject/A2A/blob/main/docs/assets/a2a-logo-white.svg?raw=true" width="40%" alt="A2A Logo" style="vertical-align: middle;">
</p>

A multi-agent system built using **[AG2](https://ag2.ai/)** with **[Agent2Agent (A2A) Protocol](https://a2a-protocol.org/)** support. This template demonstrates how to build a collaborative multi-agent pipeline where specialized agents hand off work to each other using AG2's handoff routing.

## Architecture

The template implements a three-agent pipeline:

1. **Architect** - Designs system architecture given a user request
2. **Coder** - Implements the system based on the architect's design
3. **Reviewer** - Reviews the code and either approves or requests changes

Agents communicate through AG2's handoff mechanism using `OnCondition` with `StringLLMCondition` for intelligent routing.

## Key Features

- **Multi-Agent Collaboration**: Three specialized agents working together via handoffs
- **A2A Protocol Support**: Each agent is exposed as an individual A2A endpoint
- **Streaming Support**: Real-time response streaming
- **AG2 Native**: Uses AG2's `DefaultPattern` for orchestration and built-in session management

## Validating Your A2A Implementation

This template includes the **[A2A Protocol Inspector](https://github.com/a2aproject/a2a-inspector)** for validating your agent's A2A implementation.

```bash
make inspector
```

Each agent is mounted at its own A2A endpoint:
- Architect: `http://localhost:8000/a2a/architect/`
- Coder: `http://localhost:8000/a2a/coder/`
- Reviewer: `http://localhost:8000/a2a/reviewer/`

## Running the Full Pipeline

To trigger the full architect -> coder -> reviewer pipeline, use the `/run` endpoint:

```bash
curl -X POST http://localhost:8000/run \
  -H "Content-Type: application/json" \
  -d '{"message": "Design and implement a REST API for a wiki service with article CRUD operations and search"}'
```

The pipeline runs with `max_rounds=20` by default (configurable via the `max_rounds` field).
