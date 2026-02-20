# Contributing to Agent Starter Pack

We welcome contributions to the Agent Starter Pack! This guide helps you understand the project and make effective contributions.

## Quick Navigation

| What you're changing | Start here |
|---------------------|------------|
| Template files (Jinja templates in base_templates/) | [Template Development Workflow](#template-development-workflow) |
| CLI commands (cli/commands/) | [Code Quality](#code-quality) |
| Documentation | [Pull Request Process](#pull-request-process) |
| **AI coding agents** | See [GEMINI.md](./GEMINI.md) for comprehensive AI agent guidance |

## Understanding ASP Architecture

Agent Starter Pack is a **template generator**, not a runtime framework. The CLI generates standalone projects that users then customize and deploy.

### 4-Layer Template System

Templates are processed in order, with later layers overriding earlier ones:

1. **Base Templates** (`agent_starter_pack/base_templates/<language>/`) - Core Jinja scaffolding (Python, Go, more coming)
2. **Deployment Targets** (`agent_starter_pack/deployment_targets/`) - Environment-specific overrides (cloud_run, gke, agent_engine)
3. **Frontend Types** (`agent_starter_pack/frontends/`) - UI-specific files
4. **Agent Templates** (`agent_starter_pack/agents/*/`) - Agent-specific logic and configurations

### Key Directories

| Directory | Purpose |
|-----------|---------|
| `agent_starter_pack/base_templates/` | Jinja templates by language (see [Language-Specific Notes](#language-specific-notes)) |
| `agent_starter_pack/deployment_targets/` | Files that override/extend base for specific deployments |
| `agent_starter_pack/agents/` | Agent-specific files (adk, adk_live, langgraph, etc.) |
| `agent_starter_pack/cli/commands/` | CLI command implementations (create, setup-cicd, etc.) |
| `agent_starter_pack/cli/utils/` | Shared utilities including template processing |

## Template Development Workflow

Template changes require a specific workflow because you're modifying Jinja templates.

### Recommended Process

1. **Generate a test instance**
   ```bash
   uv run agent-starter-pack create mytest -p -s -y -d cloud_run --output-dir target
   ```
   Flags: `-p` prototype (no CI/CD), `-s` skip checks, `-y` auto-approve

2. **Initialize git in the generated project**
   ```bash
   cd target/mytest && git init && git add . && git commit -m "Initial"
   ```

3. **Develop with tight feedback loops**
   - Make changes directly in `target/mytest/`
   - Test immediately with `make lint` and running the code
   - Iterate until the change works

4. **Backport changes to Jinja templates**
   - Identify the source template file in `agent_starter_pack/`
   - Apply your changes, adding Jinja conditionals if needed
   - Use `{%- -%}` whitespace control carefully (see [GEMINI.md](./GEMINI.md#critical-whitespace-control-patterns))

5. **Validate across combinations**
   ```bash
   # Test your target combination
   _TEST_AGENT_COMBINATION="adk,cloud_run,--session-type,in_memory" make lint-templated-agents

   # Test alternate agent with same deployment
   _TEST_AGENT_COMBINATION="adk_live,cloud_run" make lint-templated-agents

   # Test same agent with alternate deployment
   _TEST_AGENT_COMBINATION="adk,agent_engine" make lint-templated-agents
   ```

### Why This Workflow?

- Jinja templates are harder to debug than rendered code
- Generated projects give immediate feedback on syntax errors
- Backporting ensures you understand exactly what changed
- Cross-combination testing catches conditional logic bugs

### Language-Specific Notes

The template development workflow above applies to all languages. Here are language-specific details:

| Language | Agent(s) | Linter | Test Command | Status |
|----------|----------|--------|--------------|--------|
| Python | adk, adk_a2a, adk_live, agentic_rag, langgraph, custom_a2a | `ruff`, `ty` | `make lint` | Production |
| Go | adk_go | `golangci-lint` | `make lint` | Production |
| Java | (coming soon) | - | - | In development |
| TypeScript | (coming soon) | - | - | In development |

**Python example:**
```bash
uv run agent-starter-pack create mytest -a adk -d cloud_run -p -s -y --output-dir target
```

**Go example:**
```bash
uv run agent-starter-pack create mytest -a adk_go -d cloud_run -p -s -y --output-dir target
```

## Testing Your Changes

### Local Testing

```bash
# Install dependencies (first time)
make install

# Run linters (ruff, ty, codespell)
make lint

# Run test suite
make test
```

### Template Combination Testing

Template changes can affect multiple agent/deployment combinations. Test the minimum coverage matrix:

```bash
# Format: agent,deployment_target,--flag,value
_TEST_AGENT_COMBINATION="adk,cloud_run,--session-type,in_memory" make lint-templated-agents
_TEST_AGENT_COMBINATION="adk,agent_engine" make lint-templated-agents
_TEST_AGENT_COMBINATION="langgraph,cloud_run" make lint-templated-agents
```

**Minimum coverage before PR:**
- [ ] Your target combination
- [ ] One alternate agent with same deployment target
- [ ] One alternate deployment target with same agent

### Quick Project Generation for Testing

```bash
# Fastest: Agent Engine prototype
uv run agent-starter-pack create test-$(date +%s) -p -s -y -d agent_engine --output-dir target

# Cloud Run with session type
uv run agent-starter-pack create test-$(date +%s) -p -s -y -d cloud_run --session-type in_memory --output-dir target

# Full project with CI/CD
uv run agent-starter-pack create test-$(date +%s) -s -y -d agent_engine --cicd-runner google_cloud_build --output-dir target
```

## Pull Request Process

### Commit Message Format

```
<type>: <concise summary in imperative mood>

<detailed explanation if needed>
- Why the change was needed
- What was the root cause (for fixes)
- How the fix addresses it
```

**Types**: `fix`, `feat`, `refactor`, `docs`, `test`, `chore`

### PR Description Template

```markdown
## Summary
- Key change 1
- Key change 2

## Problem (for fixes)
Description of the issue, including error messages if applicable.

## Solution
How the changes fix the problem.

## Testing
- [ ] Tested combination: agent,deployment
- [ ] Tested alternate: agent2,deployment
- [ ] Tested alternate: agent,deployment2
```

### Required Checks

All PRs must pass:
- `make lint` - Code style and type checking
- `make test` - Unit and integration tests
- Template linting for affected combinations

## Code Quality

### Linting Tools

| Tool | Purpose |
|------|---------|
| `ruff` | Python linting and formatting |
| `ty` | Static type checking (Astral's Rust-based checker) |
| `codespell` | Spelling mistakes in code and docs |

### Template-Specific Linting

For template files, also ensure:
- All Jinja blocks are balanced (`{% if %}` has `{% endif %}`)
- Whitespace control is correct (see [GEMINI.md](./GEMINI.md#critical-whitespace-control-patterns))
- Generated files pass `ruff` in all combinations

### Spelling Errors

For errors from [check-spelling](https://github.com/check-spelling/check-spelling):
1. Check the Job Summary for specific errors
2. Fix actual spelling mistakes
3. Add false positives to `.github/actions/spelling/allow.txt`

## Contributor License Agreement

Contributions must be accompanied by a Contributor License Agreement. You (or your employer) retain copyright; this gives us permission to use and redistribute your contributions.

Sign at [Google Developers CLA](https://cla.developers.google.com/). You generally only need to submit once.

## Community Guidelines

This project follows [Google's Open Source Community Guidelines](https://opensource.google/conduct/).

## For Google Employees

Follow the additional steps in the [Generative AI on Google Cloud repository's contributing guide](https://github.com/GoogleCloudPlatform/generative-ai/blob/main/CONTRIBUTING.md#for-google-employees).

---

## Additional Resources

- **[GEMINI.md](./GEMINI.md)** - Comprehensive guide for AI coding agents, including Jinja patterns and debugging
- **[docs/](./docs/)** - User-facing documentation for generated projects
