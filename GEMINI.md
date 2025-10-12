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

## File Modification Checklist

-   [ ] **Jinja Syntax:** All `{% if %}` and `{% for %}` blocks correctly closed?
-   [ ] **Variable Consistency:** `cookiecutter.` variables spelled correctly?
-   [ ] **Cross-Target Impact:** Base template changes checked against deployment targets?
-   [ ] **CI/CD Parity:** Changes applied to both GitHub Actions and Cloud Build?
-   [ ] **Multi-Agent Testing:** Tested with different agent types and configurations?

### Key Tooling

-   **`uv` for Python:** Primary tool for dependency management and CLI execution
