# Agent Starter Pack - Coding Agent Guide

This document provides essential guidance, architectural insights, and best practices for AI coding agents tasked with modifying the Google Cloud Agent Starter Pack. Adhering to these principles is critical for making safe, consistent, and effective changes.

## Core Principles for AI Agents

1.  **Preserve and Isolate:** Your primary objective is surgical precision. Modify *only* the code segments directly related to the user's request. Preserve all surrounding code, comments, and formatting. Do not rewrite entire files or functions to make a small change.
2.  **Follow Conventions:** This project relies heavily on established patterns. Before writing new code, analyze the surrounding files to understand and replicate existing conventions for naming, templating logic, and directory structure.
3.  **Search Comprehensively:** A single change often requires updates in multiple places. When modifying configuration, variables, or infrastructure, you **must** search across the entire repository, including:
    *   `agent-starter-pack/base_template/` (the core template)
    *   `agent-starter-pack/deployment_targets/` (environment-specific overrides)
    *   `.github/` and `.cloudbuild/` (CI/CD workflows)
    *   `docs/` (user-facing documentation)

## Project Architecture Overview

### Templating Engine: Cookiecutter + Jinja2

The starter pack uses **Cookiecutter** to generate project scaffolding from templates that are heavily customized with the **Jinja2** templating language. Understanding the rendering process is key to avoiding errors.

**Multi-Phase Template Processing:**

Templates are processed in a specific order. A failure at any stage will break the project generation.

1.  **Cookiecutter Variable Substitution:** Simple replacement of `{{cookiecutter.variable_name}}` placeholders with values from `cookiecutter.json`.
2.  **Jinja2 Logic Execution:** Conditional blocks (`{% if %}`), loops (`{% for %}`), and other logic are executed. This is the most complex and error-prone stage.
3.  **File/Directory Name Templating:** File and directory names containing Jinja2 blocks are rendered. For example, `{% if cookiecutter.cicd_runner == 'github_actions' %}.github{% else %}unused_github{% endif %}`.

### Key Directory Structures

-   `agent-starter-pack/base_template/`: This is the **core template**. Most changes that should apply to all generated projects should start here.
-   `agent-starter-pack/deployment_targets/`: Contains files that **override or are added to** the `base_template` for a specific deployment target (e.g., `cloud_run`, `gke`, `agent_engine`). If a file exists in both `base_template` and a deployment target, the latter is typically used.
-   `agent-starter-pack/agents/`: Contains pre-packaged, self-contained agent examples. Each has its own `.template/templateconfig.yaml` to define its specific variables and dependencies.
-   `agent-starter-pack/cli/commands`: Contains the logic for the CLI commands, such as `create` and `setup-cicd`.

### CLI Commands

-   `create.py`: Handles the creation of new agent projects. It orchestrates the template processing, configuration merging, and deployment target selection.
-   `setup_cicd.py`: Automates the setup of the CI/CD pipeline. It interacts with `gcloud` and `gh` to configure GitHub repositories, Cloud Build triggers, and Terraform backend.

### Template Processing

-   `template.py`: Located in `agent-starter-pack/cli/utils`, this script contains the core logic for processing the templates. It copies the base template, overlays the deployment target files, and then applies the agent-specific files.

## Critical Jinja Templating Rules

Failure to follow these rules is the most common source of project generation errors.

### 1. Block Balancing
**Every opening Jinja block must have a corresponding closing block.** This is the most critical rule.

-   `{% if ... %}` requires `{% endif %}`
-   `{% for ... %}` requires `{% endfor %}`
-   `{% raw %}` requires `{% endraw %}`

**Correct:**
```jinja
{% if cookiecutter.deployment_target == 'cloud_run' %}
  # Cloud Run specific content
{% endif %}
```

### 2. Variable Usage
Distinguish between substitution and logic:

-   **Substitution (in file content):** Use double curly braces: `{{ cookiecutter.project_name }}`
-   **Logic (in `if`/`for` blocks):** Use the variable directly: `{% if cookiecutter.use_alloydb %}`

### 3. Whitespace Control
Jinja is sensitive to whitespace. Use hyphens to control newlines and prevent unwanted blank lines in rendered files.

-   `{%-` removes whitespace before the block.
-   `-%}` removes whitespace after the block.

**Example:**
```jinja
{%- if cookiecutter.some_option %}
option = true
{%- endif %}
```

## Terraform Best Practices

### Unified Service Account (`app_sa`)
The project uses a single, unified application service account (`app_sa`) across all deployment targets to simplify IAM management.

-   **Do not** create target-specific service accounts (e.g., `cloud_run_sa`).
-   Define roles for this account in `app_sa_roles`.
-   Reference this account consistently in all Terraform and CI/CD files.

### Resource Referencing
Use consistent and clear naming for Terraform resources. When referencing resources, especially those created conditionally or with `for_each`, ensure the reference is also correctly keyed.

**Example:**
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

## CI/CD Integration (GitHub Actions & Cloud Build)

The project maintains parallel CI/CD implementations. **Any change to CI/CD logic must be applied to both.**

-   **GitHub Actions:** Configured in `.github/workflows/`. Uses `${{ vars.VAR_NAME }}` for repository variables.
-   **Google Cloud Build:** Configured in `.cloudbuild/`. Uses `${_VAR_NAME}` for substitution variables.

When adding a new variable or secret, ensure it is configured correctly for both systems in the Terraform scripts that manage them (e.g., `github_actions_variable` resource and Cloud Build trigger substitutions).

## Advanced Template System Patterns

### 4-Layer Architecture
Template processing follows this hierarchy (later layers override earlier ones):
1. **Base Template** (`agent-starter-pack/base_template/`) - Applied to ALL projects
2. **Deployment Targets** (`agent-starter-pack/deployment_targets/`) - Environment overrides  
3. **Frontend Types** (`agent-starter-pack/frontends/`) - UI-specific files
4. **Agent Templates** (`agent-starter-pack/agents/*/`) - Individual agent logic

**Rule**: Always place changes in the correct layer. Check if deployment targets need corresponding updates.

### Template Processing Flow
1. Variable resolution from `cookiecutter.json`
2. File copying (base → overlays)
3. Jinja2 rendering of content
4. File/directory name rendering

### Cross-File Dependencies
Changes often require coordinated updates:
- **Configuration**: `templateconfig.yaml` → `cookiecutter.json` → rendered templates
- **CI/CD**: `.github/workflows/` ↔ `.cloudbuild/` (must stay in sync)
- **Infrastructure**: Base terraform → deployment target overrides

### Conditional Logic Patterns
```jinja
{%- if cookiecutter.agent_name == "adk_live" %}
# Agent-specific logic
{%- elif cookiecutter.deployment_target == "cloud_run" %}
# Deployment-specific logic  
{%- endif %}
```

### Testing Strategy
Test changes across multiple dimensions:
- Agent types (adk_live, adk_base, etc.)
- Deployment targets (cloud_run, agent_engine)
- Feature combinations (data_ingestion, frontend_type)
- Example command for testing the starter pack creation - from the root of the repo run: `uv run agent-starter-pack create myagent-$(date +%s) --output-dir target`

### Common Pitfalls
- **Hardcoded URLs**: Use relative paths for frontend connections
- **Missing Conditionals**: Wrap agent-specific code in proper `{% if %}` blocks
- **Dependency Conflicts**: Some agents lack certain extras (e.g., adk_live + lint)

## Linting and Testing Multiple Combinations

**IMPORTANT:** Only run linting when explicitly requested by the user. Do not proactively lint unless asked.

### Linting System

The project uses **Ruff** for linting and formatting. Use these commands to validate template combinations:

**Linting:**
```bash
SKIP_MYPY=1 _TEST_AGENT_COMBINATION="agent,target,--param,value" make lint-templated-agents
```

**Testing:**
```bash
_TEST_AGENT_COMBINATION="agent,target,--param,value" make test-templated-agents
```

Both commands use the same `_TEST_AGENT_COMBINATION` environment variable to control which agent combination to validate.

### Testing Methodology

**Critical Principle:** Template changes can affect MULTIPLE agent/deployment combinations. Test across combinations when making template modifications.

**Common Combinations:**
```bash
# Linting examples
SKIP_MYPY=1 _TEST_AGENT_COMBINATION="adk_base,cloud_run,--session-type,in_memory" make lint-templated-agents
SKIP_MYPY=1 _TEST_AGENT_COMBINATION="adk_base,agent_engine" make lint-templated-agents
SKIP_MYPY=1 _TEST_AGENT_COMBINATION="crewai_coding_crew,cloud_run" make lint-templated-agents

# Testing examples
_TEST_AGENT_COMBINATION="adk_base,cloud_run,--session-type,in_memory" make test-templated-agents
_TEST_AGENT_COMBINATION="langgraph_base_react,agent_engine" make test-templated-agents
```

### Critical Whitespace Control Patterns

Jinja2 whitespace control is the #1 source of linting failures. Understanding these patterns is essential.

#### Pattern 1: Conditional Imports with Blank Line Separation

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

{%- if cookiecutter.is_adk_a2a %}
from {{cookiecutter.agent_directory}}.agent import app as adk_app

{% endif %}
from {{cookiecutter.agent_directory}}.app_utils.gcs import create_bucket_if_not_exists
```

**Key points:**
- Use `{%- -%}` to control BOTH sides when needed
- The blank line AFTER the conditional import goes INSIDE the if block when needed
- Test BOTH when condition is true AND false

#### Pattern 2: Long Import Lines

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

#### Pattern 3: File End Newlines

**Problem:** Ruff requires exactly ONE newline at the end of every file, no more, no less.

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

### Debugging Linting Failures

**Step 1: Identify the exact error**
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

**Step 2: Find the generated file**
```bash
# Generated files are in target/
cat target/project-name/app/fast_api_app.py | head -30
```

**Step 3: Trace back to template**
```bash
# Find the template source
find agent_starter_pack -name "fast_api_app.py" -type f
```

**Step 4: Check BOTH branches of conditionals**
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
   - Conditional imports (session_type, is_adk_a2a)
   - Long import lines
   - Complex nested conditionals

3. **Any file with `{% if cookiecutter.agent_name == "..." %}`**
   - Different agents trigger different code paths
   - Must test multiple agent types

### Testing Workflow for Template Changes

**Before committing ANY template change:**

```bash
# 1. Test the specific combination you're working on
SKIP_MYPY=1 _TEST_AGENT_COMBINATION="adk_base,cloud_run,--session-type,in_memory" make lint-templated-agents

# 2. Test related combinations (same deployment, different agents)
SKIP_MYPY=1 _TEST_AGENT_COMBINATION="adk_live,cloud_run,--session-type,in_memory" make lint-templated-agents
SKIP_MYPY=1 _TEST_AGENT_COMBINATION="crewai_coding_crew,cloud_run" make lint-templated-agents

# 3. Test alternate code paths (different deployment, session types)
SKIP_MYPY=1 _TEST_AGENT_COMBINATION="adk_base,cloud_run,--session-type,agent_engine" make lint-templated-agents
SKIP_MYPY=1 _TEST_AGENT_COMBINATION="adk_base,agent_engine" make lint-templated-agents

# 4. If modifying deployment target files, test all agents with that target
# For agent_engine changes:
SKIP_MYPY=1 _TEST_AGENT_COMBINATION="adk_base,agent_engine" make lint-templated-agents
SKIP_MYPY=1 _TEST_AGENT_COMBINATION="adk_live,agent_engine" make lint-templated-agents
SKIP_MYPY=1 _TEST_AGENT_COMBINATION="langgraph_base_react,agent_engine" make lint-templated-agents
```

### Quick Reference: Whitespace Control Cheat Sheet

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

**Golden Rule:** After ANY template change affecting imports, conditionals, or file endings, test AT LEAST 3 combinations:
1. The target combination
2. An alternate agent with same deployment
3. An alternate deployment with same agent

## File Modification Checklist

-   [ ] **Jinja Syntax:** All `{% if %}` and `{% for %}` blocks correctly closed?
-   [ ] **Variable Consistency:** `cookiecutter.` variables spelled correctly?
-   [ ] **Cross-Target Impact:** Base template changes checked against deployment targets?
-   [ ] **CI/CD Parity:** Changes applied to both GitHub Actions and Cloud Build?
-   [ ] **Multi-Agent Testing:** Tested with different agent types and configurations?

## Pull Request Best Practices

When creating pull requests for this repository, follow these guidelines for clear, professional commits and PR descriptions.

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

### Key Tooling

-   **`uv` for Python:** Primary tool for dependency management and CLI execution
