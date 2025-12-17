# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Agent Starter Pack is a Python CLI package that generates production-ready GenAI agent projects on Google Cloud from templates. It uses **Cookiecutter** with **Jinja2** templating to scaffold projects with infrastructure, CI/CD, observability, and deployment configurations.

## Development Commands

### Testing
```bash
# Run all tests
make test

# Run integration tests for templated patterns
make test-templated-agents

# Run E2E deployment tests (requires .env setup)
make test-e2e

# Test specific agent/deployment combinations
_TEST_AGENT_COMBINATION="adk_base,cloud_run,--session-type,in_memory" make test-templated-agents
_TEST_AGENT_COMBINATION="langgraph_base,agent_engine" make test-templated-agents
```

### Linting
**IMPORTANT:** Only run linting when explicitly requested by the user. The project uses Ruff for linting/formatting and mypy for type checking.

```bash
# Lint the CLI and tests code
make lint

# Lint generated templates (when explicitly requested)
SKIP_MYPY=1 _TEST_AGENT_COMBINATION="adk_base,cloud_run,--session-type,in_memory" make lint-templated-agents
SKIP_MYPY=1 _TEST_AGENT_COMBINATION="adk_base,agent_engine" make lint-templated-agents
```

### Installation
```bash
# Install all dependencies with dev tools
make install

# Generate dependency locks
make generate-lock
```

### Fast Project Creation for Testing
```bash
# Quick prototype (no CI/CD, no Terraform, no prompts)
uv run agent-starter-pack create mytest -p -s -y -d agent_engine --output-dir target

# Flags:
# -p / --prototype  : Minimal project (no CI/CD or Terraform)
# -s / --skip-checks: Skip GCP/Vertex AI verification
# -y / --auto-approve: Skip all confirmation prompts
# -d : Deployment target
# --output-dir target: Output to target/ (gitignored)

# Test with Cloud Run and session type
uv run agent-starter-pack create test-$(date +%s) -p -s -y -d cloud_run --session-type in_memory --output-dir target
```

## Architecture

### 4-Layer Template System

Templates are processed in this hierarchy (later layers override earlier):

1. **Base Template** (`agent_starter_pack/base_template/`) - Applied to ALL projects
2. **Deployment Targets** (`agent_starter_pack/deployment_targets/`) - Environment-specific overrides (cloud_run, agent_engine)
3. **Frontend Types** (`agent_starter_pack/frontends/`) - UI-specific files (adk_live_react, etc.)
4. **Agent Templates** (`agent_starter_pack/agents/*/`) - Individual agent implementations (adk_base, adk_live, langgraph_base, agentic_rag, adk_a2a_base)

### Template Processing Flow

1. Variable resolution from `cookiecutter.json` or `.template/templateconfig.yaml`
2. File copying (base → deployment target → frontend → agent overlays)
3. Jinja2 rendering of file content
4. File/directory name rendering (e.g., `{% if cookiecutter.cicd_runner == 'github_actions' %}.github{% else %}unused_github{% endif %}`)

### Key Directories

- `agent_starter_pack/cli/commands/` - CLI command implementations (create, enhance, setup-cicd)
- `agent_starter_pack/cli/utils/` - Core utilities for template processing, GCP interaction, CI/CD setup
- `agent_starter_pack/agents/` - Pre-built agent templates (each has `.template/templateconfig.yaml`)
- `agent_starter_pack/deployment_targets/` - Platform-specific files (Cloud Run, Agent Engine)
- `agent_starter_pack/frontends/` - UI templates
- `agent_starter_pack/base_template/` - Core template files applied to all projects

## Critical Jinja2 Templating Rules

### Block Balancing
Every opening Jinja block MUST have a closing block:
- `{% if ... %}` requires `{% endif %}`
- `{% for ... %}` requires `{% endfor %}`
- `{% raw %}` requires `{% endraw %}`

### Variable Usage
- **Substitution (in content):** `{{ cookiecutter.project_name }}`
- **Logic (in conditionals):** `{% if cookiecutter.session_type == 'cloud_sql' %}`

### Whitespace Control
Jinja is sensitive to whitespace. Use hyphens to control newlines:
- `{%-` removes whitespace before the block
- `-%}` removes whitespace after the block

**Critical Pattern - Conditional Imports:**
```jinja
from opentelemetry.sdk.trace import TracerProvider, export
{% if cookiecutter.session_type == "agent_engine" -%}
from vertexai import agent_engines
{% endif %}

{%- if cookiecutter.is_a2a %}
from {{cookiecutter.agent_directory}}.agent import app as adk_app

{% endif %}
from {{cookiecutter.agent_directory}}.app_utils.gcs import create_bucket_if_not_exists
```

### Common Whitespace Pitfalls

1. **Missing blank line between imports** - Use `{%- -%}` to preserve exactly one blank line
2. **Extra blank lines** - Use `{%- endif -%}` to strip both sides
3. **File end newlines** - Ruff requires exactly ONE newline at end of every file

## Testing Template Changes

**CRITICAL:** Template changes can affect MULTIPLE agent/deployment combinations. Before committing ANY template change:

1. Test the target combination
2. Test an alternate agent with same deployment
3. Test an alternate deployment with same agent

Common test combinations:
```bash
# Base template + different agents
SKIP_MYPY=1 _TEST_AGENT_COMBINATION="adk_base,cloud_run,--session-type,in_memory" make lint-templated-agents
SKIP_MYPY=1 _TEST_AGENT_COMBINATION="adk_live,cloud_run,--session-type,in_memory" make lint-templated-agents

# Same agent + different deployments
SKIP_MYPY=1 _TEST_AGENT_COMBINATION="adk_base,cloud_run,--session-type,in_memory" make lint-templated-agents
SKIP_MYPY=1 _TEST_AGENT_COMBINATION="adk_base,agent_engine" make lint-templated-agents
```

## Terraform Patterns

### Unified Service Account
- Use single `app_sa` service account across all deployment targets
- Do NOT create target-specific service accounts
- Define roles in `app_sa_roles`

### Resource Referencing
```hcl
# Creation with for_each
resource "google_service_account" "app_sa" {
  for_each   = local.deploy_project_ids # {"staging" = "...", "prod" = "..."}
  account_id = "${var.project_name}-app"
}

# Correct reference
service_account = google_service_account.app_sa["staging"].email
```

## CI/CD Integration

The project maintains parallel implementations. **Any CI/CD change must be applied to BOTH:**

- **GitHub Actions:** `.github/workflows/` - Uses `${{ vars.VAR_NAME }}`
- **Google Cloud Build:** `.cloudbuild/` - Uses `${_VAR_NAME}`

## Project Metadata

Generated projects store creation context in `pyproject.toml`:

```toml
[tool.agent-starter-pack]
name = "my-project"
base_template = "adk_base"
asp_version = "0.29.0"

[tool.agent-starter-pack.create_params]
deployment_target = "cloud_run"
session_type = "in_memory"
cicd_runner = "skip"
```

The `create_params` section enables the `enhance` command to recreate scaffolding with the locked ASP version.

## Files Most Prone to Issues

1. **`agent_engine_app.py`** (deployment_targets/agent_engine/) - Multiple conditional paths, end-of-file issues
2. **`fast_api_app.py`** (deployment_targets/cloud_run/) - Conditional imports, long import lines
3. **Any file with `{% if cookiecutter.agent_name == "..." %}`** - Different agents trigger different code paths

## Modification Checklist

When making template changes:

- [ ] All `{% if %}` and `{% for %}` blocks correctly closed?
- [ ] `cookiecutter.` variables spelled correctly?
- [ ] Base template changes checked against deployment targets?
- [ ] Changes applied to both GitHub Actions AND Cloud Build?
- [ ] Tested with multiple agent types and configurations?
- [ ] Whitespace control correct for import sections?
- [ ] Exactly one newline at end of files?

## Core Principles

1. **Preserve and Isolate:** Modify ONLY code segments directly related to the request. Do not rewrite entire files.
2. **Follow Conventions:** Analyze surrounding files to understand patterns before writing new code.
3. **Search Comprehensively:** Changes often require updates in multiple places across `base_template/`, `deployment_targets/`, `.github/`, `.cloudbuild/`, and `docs/`.

## Additional Resources

- See `GEMINI.md` for comprehensive templating patterns, debugging strategies, and whitespace control details
- See `CONTRIBUTING.md` for code quality checks and contribution workflow
- Documentation: https://googlecloudplatform.github.io/agent-starter-pack/
