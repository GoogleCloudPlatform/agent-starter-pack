# Agent Starter Pack - AI Coding Agent Guide

> **Scope**: This document is for AI coding agents contributing to the **Agent Starter Pack repository itself** (the template generator). For guidance on working with **generated projects**, see [llm.txt](./llm.txt).

This document provides essential guidance, architectural insights, and best practices for AI coding agents tasked with modifying the Google Cloud Agent Starter Pack. Adhering to these principles is critical for making safe, consistent, and effective changes.

---

## Core Principles for AI Agents

1.  **Preserve and Isolate:** Your primary objective is surgical precision. Modify *only* the code segments directly related to the user's request. Preserve all surrounding code, comments, and formatting. Do not rewrite entire files or functions to make a small change.
2.  **Follow Conventions:** This project relies heavily on established patterns. Before writing new code, analyze the surrounding files to understand and replicate existing conventions for naming, templating logic, and directory structure.
3.  **Template-First Mindset:** ASP is a template generator. The CLI should remain lean with good defaults. Most features belong in templates, not CLI code.
4.  **Search Comprehensively:** A single change often requires updates in multiple places. When modifying configuration, variables, or infrastructure, you **must** search across the entire repository, including:
    *   `agent_starter_pack/base_templates/` (core templates by language)
    *   `agent_starter_pack/deployment_targets/` (environment-specific overrides)
    *   `.github/` and `.cloudbuild/` (CI/CD workflows)
    *   `docs/` (user-facing documentation)

---

## Project Architecture Overview

### 4-Layer Template System

Template processing follows this hierarchy (later layers override earlier ones):

| Layer | Directory | Purpose |
|-------|-----------|---------|
| 1. Base | `agent_starter_pack/base_templates/<language>/` | Core Jinja scaffolding (Python, Go, more coming) |
| 2. Deployment | `agent_starter_pack/deployment_targets/` | Environment overrides (cloud_run, agent_engine) |
| 3. Frontend | `agent_starter_pack/frontends/` | UI-specific files |
| 4. Agent | `agent_starter_pack/agents/*/` | Agent-specific logic and configurations |

**Rule**: Always place changes in the correct layer. Check if deployment targets need corresponding updates.

### Key Directory Structure

```
agent_starter_pack/
├── agents/                    # Agent-specific files
│   ├── adk/                   # Base ADK agent (Python)
│   ├── adk_a2a/               # A2A-enabled ADK agent
│   ├── adk_go/                # Base ADK agent (Go)
│   ├── adk_live/              # Real-time multimodal agent
│   ├── agentic_rag/           # RAG agent
│   └── langgraph/             # LangGraph-based agent
├── base_templates/            # Core Jinja templates by language
│   ├── python/                # Python project template
│   │   ├── {{cookiecutter.agent_directory}}/
│   │   ├── deployment/
│   │   ├── tests/
│   │   └── Makefile
│   └── go/                    # Go project template
├── deployment_targets/        # Environment-specific overrides
│   ├── agent_engine/          # Agent Engine deployment
│   └── cloud_run/             # Cloud Run deployment
├── frontends/                 # UI templates
└── cli/                       # CLI implementation
    ├── commands/              # create, setup-cicd, enhance, etc.
    └── utils/                 # Template processing, helpers
```

### When to Modify What

| Change Type | Where to Modify | Also Check |
|-------------|-----------------|------------|
| Affects ALL generated projects | `base_templates/<language>/` | Deployment targets for conflicts |
| Deployment-specific logic | `deployment_targets/<target>/` | Base templates for shared code |
| Agent-specific feature | `agents/<agent>/` | Other agents for consistency |
| New CLI flag/command | `cli/commands/` | `cli/utils/` for shared logic |
| CI/CD changes | Both `.github/` AND `.cloudbuild/` | Keep in sync |
| Documentation | `docs/` | README.md for overview changes |

### Template Processing Flow

1.  **Variable resolution** from `cookiecutter.json`
2.  **File copying** (base → deployment → frontend → agent overlays)
3.  **Jinja2 rendering** of file content
4.  **File/directory name rendering** (Jinja in filenames)

### Cross-File Dependencies

Changes often require coordinated updates:
- **Configuration**: `templateconfig.yaml` → `cookiecutter.json` → rendered templates
- **CI/CD**: `.github/workflows/` ↔ `.cloudbuild/` (must stay in sync)
- **Infrastructure**: Base terraform → deployment target overrides

---

## Template Development Workflow

Template changes require a specific workflow because you're modifying Jinja templates, not regular source files.

> **Note:** This workflow applies to both Python and Go templates. Both use Jinja templating with the same patterns (`{{cookiecutter.*}}`, `{% if %}`, etc.).

### Step-by-Step Process

#### 1. Generate a Test Instance

```bash
uv run agent-starter-pack create mytest -p -s -y -d cloud_run --output-dir target
```

Flags explained:
- `-p` / `--prototype`: Minimal project (no CI/CD or Terraform)
- `-s` / `--skip-checks`: Skip GCP/Vertex AI verification
- `-y` / `--auto-approve`: Skip all confirmation prompts
- `-d`: Deployment target
- `--output-dir target`: Output to target/ (gitignored)

#### 2. Initialize Git in the Generated Project

```bash
cd target/mytest && git init && git add . && git commit -m "Initial"
```

This creates a baseline for tracking your changes with `git diff`.

#### 3. Develop with Tight Feedback Loops

- Make changes directly in `target/mytest/`
- Test immediately: `make lint`, run the code, check output
- Iterate until the change works correctly
- Use `git diff` to see exactly what you changed

#### 4. Backport Changes to Jinja Templates

- Find the source template: `find agent_starter_pack -name "filename.py" -type f`
- Apply your changes to the template file
- Add Jinja conditionals if the change is conditional
- Use `{%- -%}` whitespace control carefully

#### 5. Validate Across Combinations

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

---

## Jinja Templating Rules

> **Note:** These rules apply to both Python and Go templates. Both languages use the same Jinja2 templating patterns.

### Templating Engine: Cookiecutter + Jinja2

The starter pack uses **Cookiecutter** to generate project scaffolding from templates customized with **Jinja2**. Understanding the rendering process is key to avoiding errors.

**Multi-Phase Template Processing:**

1.  **Cookiecutter Variable Substitution:** Replacement of `{{cookiecutter.variable_name}}` placeholders
2.  **Jinja2 Logic Execution:** Conditional blocks (`{% if %}`), loops (`{% for %}`)
3.  **File/Directory Name Templating:** Jinja2 in filenames is rendered

### Block Balancing (Critical)

**Every opening Jinja block must have a corresponding closing block.**

-   `{% if ... %}` requires `{% endif %}`
-   `{% for ... %}` requires `{% endfor %}`
-   `{% raw %}` requires `{% endraw %}`

```jinja
{% if cookiecutter.deployment_target == 'cloud_run' %}
  # Cloud Run specific content
{% endif %}
```

### Variable Usage

Distinguish between substitution and logic:

-   **Substitution (in file content):** `{{ cookiecutter.project_name }}`
-   **Logic (in `if`/`for` blocks):** `{% if cookiecutter.session_type == 'cloud_sql' %}`

### Whitespace Control

Jinja is sensitive to whitespace. Use hyphens to control newlines:

-   `{%-` removes whitespace before the block
-   `-%}` removes whitespace after the block
-   `{%- -%}` removes whitespace on both sides

```jinja
{%- if cookiecutter.some_option %}
option = true
{%- endif %}
```

### Conditional Logic Patterns

```jinja
{%- if cookiecutter.agent_name == "adk_live" %}
# Agent-specific logic
{%- elif cookiecutter.deployment_target == "cloud_run" %}
# Deployment-specific logic
{%- endif %}
```

---

## Critical Whitespace Control Patterns

Jinja2 whitespace control is the #1 source of linting failures. Understanding these patterns is essential.

### Pattern 1: Conditional Imports with Blank Line Separation

**Problem:** Python requires blank lines to separate third-party imports from project imports. Conditional imports must handle this correctly.

**Wrong - Creates extra blank line:**
```jinja
from opentelemetry.sdk.trace import TracerProvider, export
{% if cookiecutter.session_type == "agent_engine" %}
from vertexai import agent_engines
{% endif %}

from app.app_utils.gcs import create_bucket_if_not_exists
```

**Correct - Exactly one blank line:**
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

**Key points:**
- Use `{%- -%}` to control BOTH sides when needed
- The blank line AFTER the conditional import goes INSIDE the if block when needed
- Test BOTH when condition is true AND false

### Pattern 2: Long Import Lines

**Problem:** Ruff enforces line length limits. Long import statements must be split.

**Wrong - Too long:**
```python
from app.app_utils.typing import Feedback, InputChat, Request, dumps, ensure_valid_config
```

**Correct - Split with parentheses:**
```python
from app.app_utils.typing import (
    Feedback,
    InputChat,
    Request,
    dumps,
    ensure_valid_config,
)
```

### Pattern 3: File End Newlines

**Problem:** Ruff requires exactly ONE newline at the end of every file.

**Wrong - No newline:**
```jinja
agent_engine = AgentEngineApp(project_id=project_id)
{%- endif %}
```

**Wrong - Extra newline:**
```jinja
agent_engine = AgentEngineApp(project_id=project_id)
{%- endif %}

```

**Correct - Exactly one:**
```jinja
agent_engine = AgentEngineApp(project_id=project_id)
{%- endif %}
```

**Key for nested conditionals:**
```jinja
agent_engine = AgentEngineApp(
    app=adk_app,
    artifact_service_builder=artifact_service_builder,
)
{%- endif -%}
{% else %}

import logging
```

Notice `{%- endif -%}` to prevent blank line before the else block.

### Whitespace Control Cheat Sheet

```jinja
# Remove whitespace BEFORE the tag
{%- if condition %}

# Remove whitespace AFTER the tag
{% if condition -%}

# Remove whitespace on BOTH sides
{%- if condition -%}

# Typical pattern for conditional imports
{% if condition -%}
import something
{% endif %}

# Typical pattern for conditional code blocks with blank line before
{%- if condition %}

some_code()
{%- endif %}

# Pattern for preventing blank line between consecutive conditionals
{%- endif -%}
{%- if next_condition %}
```

---

## Testing Strategy

### Testing Coverage Matrix

**Critical Principle:** Template changes can affect MULTIPLE agent/deployment combinations. Test across combinations when making template modifications.

| Dimension | Options |
|-----------|---------|
| Agents | adk, adk_a2a, adk_go, adk_live, agentic_rag, langgraph |
| Deployments | cloud_run, agent_engine |
| Session types | in_memory, cloud_sql, agent_engine |
| Features | data_ingestion, frontend_type |

### Minimum Coverage Before PR

- [ ] Your target combination
- [ ] One alternate agent with same deployment target
- [ ] One alternate deployment target with same agent

### Linting Commands

**IMPORTANT:** Only run linting when explicitly requested by the user. Do not proactively lint unless asked.

```bash
# Linting a specific combination
_TEST_AGENT_COMBINATION="agent,target,--param,value" make lint-templated-agents

# Testing a specific combination
_TEST_AGENT_COMBINATION="agent,target,--param,value" make test-templated-agents
```

### Common Test Combinations

```bash
# Cloud Run combinations (Python)
_TEST_AGENT_COMBINATION="adk,cloud_run,--session-type,in_memory" make lint-templated-agents
_TEST_AGENT_COMBINATION="adk_live,cloud_run,--session-type,in_memory" make lint-templated-agents

# Agent Engine combinations (Python)
_TEST_AGENT_COMBINATION="adk,agent_engine" make lint-templated-agents
_TEST_AGENT_COMBINATION="adk_live,agent_engine" make lint-templated-agents
_TEST_AGENT_COMBINATION="langgraph,agent_engine" make lint-templated-agents

# Go template testing
_TEST_AGENT_COMBINATION="adk_go,cloud_run" make lint-templated-agents

# With session type variations
_TEST_AGENT_COMBINATION="adk,cloud_run,--session-type,agent_engine" make lint-templated-agents
```

### Testing Workflow for Template Changes

**Before committing ANY template change:**

```bash
# 1. Test the specific combination you're working on
_TEST_AGENT_COMBINATION="adk,cloud_run,--session-type,in_memory" make lint-templated-agents

# 2. Test related combinations (same deployment, different agents)
_TEST_AGENT_COMBINATION="adk_live,cloud_run,--session-type,in_memory" make lint-templated-agents

# 3. Test alternate code paths (different deployment, session types)
_TEST_AGENT_COMBINATION="adk,cloud_run,--session-type,agent_engine" make lint-templated-agents
_TEST_AGENT_COMBINATION="adk,agent_engine" make lint-templated-agents

# 4. If modifying deployment target files, test all agents with that target
# For agent_engine changes:
_TEST_AGENT_COMBINATION="adk,agent_engine" make lint-templated-agents
_TEST_AGENT_COMBINATION="adk_live,agent_engine" make lint-templated-agents
_TEST_AGENT_COMBINATION="langgraph,agent_engine" make lint-templated-agents
```

**Golden Rule:** After ANY template change affecting imports, conditionals, or file endings, test AT LEAST 3 combinations:
1. The target combination
2. An alternate agent with same deployment
3. An alternate deployment with same agent

---

## Debugging Linting Failures

### Step 1: Identify the Exact Error

```bash
# Look for the diff output in the error message
--- app/fast_api_app.py
+++ app/fast_api_app.py
@@ -21,6 +21,7 @@
 from opentelemetry import trace
 from vertexai import agent_engines
+
 from app.app_utils.gcs import create_bucket_if_not_exists
```

The `+` line shows what Ruff WANTS to add. In this case, it wants a blank line after `agent_engines`.

### Step 2: Find the Generated File

```bash
# Generated files are in target/
cat target/project-name/app/fast_api_app.py | head -30
```

### Step 3: Trace Back to Template

```bash
# Find the template source
find agent_starter_pack -name "fast_api_app.py" -type f
```

### Step 4: Check BOTH Branches of Conditionals

- If `{% if condition %}` exists, test with condition true AND false
- Use different agent combinations to toggle different conditions

### Common Linting Errors and Fixes

| Error | Cause | Fix |
|-------|-------|-----|
| Missing blank line between imports | Conditional import without proper spacing | Add blank line inside `{% if %}` block with correct `{%- -%}` control |
| Extra blank line between imports | Jinja block creating unwanted newline | Use `{%- endif -%}` to strip both sides |
| Missing newline at end of file | Template ends without final newline | Ensure template has exactly one blank line at end |
| Extra blank line at end of file | Multiple newlines or `{% endif %}` creating extra line | Use `{%- endif -%}` pattern |
| Line too long | Import statement exceeds limit | Split into multi-line with parentheses |

### Files Most Prone to Linting Issues

1. **`agent_engine_app.py`** (deployment_targets/agent_engine/)
   - Multiple conditional paths (adk_live, adk_a2a, regular)
   - End-of-file newline issues

2. **`fast_api_app.py`** (deployment_targets/cloud_run/)
   - Conditional imports (session_type, is_a2a)
   - Long import lines
   - Complex nested conditionals

3. **Any file with `{% if cookiecutter.agent_name == "..." %}`**
   - Different agents trigger different code paths
   - Must test multiple agent types

---

## CI/CD Integration

The project maintains parallel CI/CD implementations. **Any change to CI/CD logic must be applied to both.**

-   **GitHub Actions:** Configured in `.github/workflows/`. Uses `${{ vars.VAR_NAME }}` for repository variables.
-   **Google Cloud Build:** Configured in `.cloudbuild/`. Uses `${_VAR_NAME}` for substitution variables.

When adding a new variable or secret, ensure it is configured correctly for both systems in the Terraform scripts that manage them (e.g., `github_actions_variable` resource and Cloud Build trigger substitutions).

---

## Terraform Best Practices

### Unified Service Account (`app_sa`)

The project uses a single, unified application service account (`app_sa`) across all deployment targets to simplify IAM management.

-   **Do not** create target-specific service accounts (e.g., `cloud_run_sa`)
-   Define roles for this account in `app_sa_roles`
-   Reference this account consistently in all Terraform and CI/CD files

### Resource Referencing

Use consistent and clear naming for Terraform resources. When referencing resources, especially those created conditionally or with `for_each`, ensure the reference is also correctly keyed.

```hcl
# Creation
resource "google_service_account" "app_sa" {
  for_each   = local.deploy_project_ids # e.g., {"staging" = "...", "prod" = "..."}
  account_id = "${var.project_name}-app"
  # ...
}

# Correct Reference
# In a Cloud Run module for the staging environment
service_account = google_service_account.app_sa["staging"].email
```

---

## Pull Request Best Practices

### Commit Message Format

```
<type>: <concise summary in imperative mood>

<detailed explanation of the change>
- Why the change was needed
- What was the root cause
- How the fix addresses it
```

**Types**: `fix`, `feat`, `refactor`, `docs`, `test`, `chore`

### PR Structure Example

**Title:** Brief, descriptive summary (50-60 chars)
```
Fix Cloud Build service account permission for GitHub PAT secret access
```

**Description:**
```markdown
## Summary
- Key change 1 (what was added/modified)
- Key change 2
- Key change 3

## Problem
Clear description of the issue, including:
- Error messages or symptoms
- Why it was failing
- Context about when/where it occurs

## Solution
Explanation of how the changes fix the problem:
- What resources/files were modified
- Why this approach was chosen
- Any dependencies or sequencing requirements
```

### Example (based on actual PR)

**Commit:**
```
Fix Cloud Build service account permission for GitHub PAT secret access

Add IAM binding to grant Cloud Build service account the secretAccessor
role for the GitHub PAT secret. This resolves permission errors when
Terraform creates Cloud Build v2 connections in E2E tests.

The CLI setup already grants this permission via gcloud, but the
Terraform configuration was missing this binding, causing failures when
Terraform runs independently.
```

**PR Description:**
```markdown
## Summary
- Grant Cloud Build service account `secretmanager.secretAccessor` role
- Add proper dependency to Cloud Build v2 connection resource

## Problem
E2E tests failed when Terraform attempted to create Cloud Build v2 connections:
```
Error: could not access secret with service account:
generic::permission_denied
```

The CLI setup grants this permission via gcloud, but Terraform
configuration lacked the IAM binding.

## Solution
Added `google_secret_manager_secret_iam_member` resource to grant the
Cloud Build service account permission to access the GitHub PAT secret
before creating the connection.
```

### Key Principles

- **Concise but complete**: Provide enough context for reviewers
- **Problem-first**: Explain the "why" before the "what"
- **Professional tone**: Avoid mentions of AI tools or assistants

---

## File Modification Checklist

-   [ ] **Jinja Syntax:** All `{% if %}` and `{% for %}` blocks correctly closed?
-   [ ] **Variable Consistency:** `cookiecutter.` variables spelled correctly?
-   [ ] **Cross-Target Impact:** Base template changes checked against deployment targets?
-   [ ] **CI/CD Parity:** Changes applied to both GitHub Actions and Cloud Build?
-   [ ] **Multi-Agent Testing:** Tested with different agent types and configurations?

---

## Quick Reference

### Fast Project Creation

```bash
# Quick prototype project (no CI/CD, no Terraform, no prompts)
uv run agent-starter-pack create mytest -p -s -y -d agent_engine --output-dir target

# Flags explained:
# -p / --prototype  : Minimal project (no CI/CD or Terraform)
# -s / --skip-checks: Skip GCP/Vertex AI verification
# -y / --auto-approve: Skip all confirmation prompts
# -d : Deployment target
# --output-dir target: Output to target/ (gitignored)
```

### Common Test Combinations

```bash
# Agent Engine + prototype (fastest)
uv run agent-starter-pack create test-$(date +%s) -p -s -y -d agent_engine --output-dir target

# Cloud Run with session type
uv run agent-starter-pack create test-$(date +%s) -p -s -y -d cloud_run --session-type in_memory --output-dir target

# Full project with CI/CD
uv run agent-starter-pack create test-$(date +%s) -s -y -d agent_engine --cicd-runner google_cloud_build --output-dir target
```

### Key Files Reference

| File | Purpose |
|------|---------|
| `agent_starter_pack/cli/commands/create.py` | Main create command, CLI flags, shared options |
| `agent_starter_pack/cli/utils/template.py` | Template processing, `process_template()`, CI/CD runner prompt |
| `agent_starter_pack/base_templates/python/pyproject.toml` | Generated project metadata, `[tool.agent-starter-pack]` section |
| `agent_starter_pack/base_templates/python/Makefile` | Generated project Makefile targets |

### Key Tooling

-   **`uv` for Python:** Primary tool for dependency management and CLI execution

---

## Common Pitfalls

- **Hardcoded URLs**: Use relative paths for frontend connections
- **Missing Conditionals**: Wrap agent-specific code in proper `{% if %}` blocks
- **Dependency Conflicts**: Some agents lack certain extras (e.g., adk_live + lint)
- **makefile_hashes.json**: Can cause merge conflicts during active development - regenerate if needed

---

## Project Metadata Structure

Generated projects store creation context in `pyproject.toml`:

```toml
[tool.agent-starter-pack]
# Metadata
name = "my-project"
base_template = "adk"
asp_version = "0.25.0"

[tool.agent-starter-pack.create_params]
# CLI params used during creation - used by enhance command
deployment_target = "cloud_run"
session_type = "in_memory"
cicd_runner = "skip"
include_data_ingestion = false
```

The `create_params` section enables the `enhance` command to recreate identical scaffolding with the locked ASP version.
