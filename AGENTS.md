# Agent Starter Pack — Notes for AI Contributors

This file contains quick-reference information for agents (and humans) contributing to the Agent Starter Pack (ASP).

## Project Overview

ASP is a **template generator**, not a runtime framework. The CLI scaffolds standalone agent projects that users customize and deploy on Google Cloud.

> ⚠️ **Maintenance mode**: Active development has moved to [`agents-cli`](https://github.com/google/agents-cli). ASP receives critical fixes only. New projects should use `agents-cli`.

## Repository Layout

| Path | Purpose |
|------|---------|
| `agent_starter_pack/base_templates/<language>/` | Core Jinja scaffolding (Python, Go, more coming) |
| `agent_starter_pack/deployment_targets/` | Environment-specific overrides (`cloud_run`, `gke`, `agent_engine`) |
| `agent_starter_pack/frontends/` | UI-specific files |
| `agent_starter_pack/agents/` | Agent-specific logic and configurations (`adk`, `adk_a2a`, `adk_live`, `langgraph`, `agentic_rag`, etc.) |
| `agent_starter_pack/cli/` | CLI command implementations and shared utilities |
| `tests/` | Unit and integration tests |

## Development Commands

Uses [`uv`](https://docs.astral.sh/uv/) for dependency management.

```bash
# First-time setup
make install

# Run linters (ruff + ty + codespell)
make lint

# Run unit tests
make test

# Lint generated templates for a specific combination
_TEST_AGENT_COMBINATION="adk,cloud_run,--session-type,in_memory" make lint-templated-agents
```

## Template Development Workflow

When modifying Jinja templates:

1. Generate a test instance:
   ```bash
   uv run agent-starter-pack create mytest -p -s -y -d cloud_run --output-dir target
   ```
2. Iterate in `target/mytest/` using `make lint` and running the code.
3. Backport changes to the source Jinja templates in `agent_starter_pack/`.
4. Validate across combinations:
   ```bash
   _TEST_AGENT_COMBINATION="adk,cloud_run" make lint-templated-agents
   _TEST_AGENT_COMBINATION="adk,agent_engine" make lint-templated-agents
   _TEST_AGENT_COMBINATION="adk_live,cloud_run" make lint-templated-agents
   ```

See [`CONTRIBUTING.md`](./CONTRIBUTING.md) and [`GEMINI.md`](./GEMINI.md) for full details, including critical Jinja whitespace patterns.

## Code Style

- Python: `ruff` (line length 88, target `py311`), `ty` type checker, `codespell`.
- Go templates: follow the conventions in `base_templates/go/`.
- Keep generated output deterministic and backward-compatible.

## Contribution Tips for Agents

- Prefer small, focused PRs.
- Do not change core schema/agent/model tools unless required by an open issue.
- Run `make lint` and `make test` before pushing.
- When in doubt, generate a test project and verify the rendered output compiles.
