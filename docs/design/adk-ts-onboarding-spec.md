# Design Spec: TypeScript ADK Agent Template Onboarding

**Status**: Draft
**Author**: Agent Starter Pack Team
**Date**: 2026-01-22
**Reference**: [Go Implementation PR #670](https://github.com/GoogleCloudPlatform/agent-starter-pack/pull/670)

---

## Executive Summary

This document outlines the design for adding TypeScript ADK (`adk_ts`) as a new agent template to the Agent Starter Pack, following the same pattern established for Go support in PR #670. The implementation will mirror the Go architecture with language-specific adaptations.

**Source of Truth**: The `/adk-ts-agent` folder in this repository contains a fully working, E2E-tested TypeScript ADK agent. This reference implementation will be decomposed into the template layers - we are **extracting** from a working example, not creating from scratch.

---

## Table of Contents

1. [Goals & Non-Goals](#1-goals--non-goals)
2. [Architecture Pattern (Parallel to Go)](#2-architecture-pattern-parallel-to-go)
3. [Implementation Plan](#3-implementation-plan)
4. [File Specifications](#4-file-specifications)
5. [CLI Changes](#5-cli-changes)
6. [Testing Strategy](#6-testing-strategy)
7. [Open Questions](#7-open-questions)

---

## 1. Goals & Non-Goals

### Goals

- Add TypeScript ADK as a first-class agent template **parallel to Go**
- Support Cloud Run deployment target (same as Go)
- Follow the exact same 3-layer pattern: base_template → deployment_target → agent
- Maintain consistency with existing Go implementation
- Use `@google/adk` and `@google/adk-devtools` packages

### Non-Goals (Initial Release - Same as Go)

- Agent Engine deployment target
- Session management (Cloud SQL, Firestore)
- Data ingestion pipeline (RAG)
- A2A protocol support
- Frontend templates

---

## 2. Architecture Pattern (Parallel to Go)

### 2.1 Go Implementation Structure (Reference)

```
agent_starter_pack/
├── base_templates/
│   └── go/                              # Go base template
│       ├── .asp.toml                    # Project metadata
│       ├── .cloudbuild/                 # Cloud Build CI/CD
│       ├── .github/workflows/           # GitHub Actions CI/CD
│       ├── .env, .env.example
│       ├── .gitignore, .golangci.yml
│       ├── Makefile, README.md
│       ├── go.mod, go.sum               # Go dependencies
│       ├── main.go                      # Entry point
│       ├── agent/agent.go               # Placeholder agent
│       └── e2e/                         # Tests
│           ├── integration/server_e2e_test.go
│           └── load_test/load_test.go
│
├── deployment_targets/
│   └── cloud_run/
│       └── go/                          # Go-specific Cloud Run
│           ├── Dockerfile
│           └── deployment/terraform/
│               ├── service.tf
│               └── dev/service.tf
│
└── agents/
    └── adk_go/                          # Go agent template
        ├── .template/templateconfig.yaml
        └── agent/
            ├── agent.go
            └── agent_test.go
```

### 2.2 TypeScript Implementation Structure (Parallel)

```
agent_starter_pack/
├── base_templates/
│   └── typescript/                      # TypeScript base template
│       ├── .asp.toml                    # Project metadata
│       ├── .cloudbuild/                 # Cloud Build CI/CD
│       ├── .github/workflows/           # GitHub Actions CI/CD
│       ├── .env, .env.example
│       ├── .gitignore
│       ├── eslint.config.mjs            # Linting config
│       ├── vitest.config.ts             # Test runner config
│       ├── tsconfig.json                # TypeScript config
│       ├── package.json                 # Dependencies
│       ├── package-lock.json            # Lock file
│       ├── Makefile, README.md
│       ├── app/agent.ts                 # Placeholder agent
│       └── tests/                       # Tests (parallel to Go's e2e/)
│           ├── integration/server_e2e.test.ts
│           ├── unit/dummy.test.ts
│           └── load_test/
│               ├── load_test.ts
│               └── README.md
│
├── deployment_targets/
│   └── cloud_run/
│       └── typescript/                  # TypeScript-specific Cloud Run
│           ├── Dockerfile
│           └── deployment/terraform/
│               ├── service.tf
│               └── dev/service.tf
│
└── agents/
    └── adk_ts/                          # TypeScript agent template
        ├── .template/templateconfig.yaml
        └── app/
            ├── agent.ts
            └── agent.test.ts
```

### 2.3 Comparison Table

| Component | Go | TypeScript |
|-----------|-----|------------|
| Base template dir | `base_templates/go/` | `base_templates/typescript/` |
| Agent template dir | `agents/adk_go/` | `agents/adk_ts/` |
| Deployment target | `cloud_run/go/` | `cloud_run/typescript/` |
| Agent directory | `agent/` | `app/` |
| Package manager | go mod | npm |
| Lock file | go.sum | package-lock.json |
| Entry point | main.go | (via adk-devtools) |
| Tests directory | e2e/ | tests/ |
| Linter config | .golangci.yml | eslint.config.mjs |
| Type config | N/A (built-in) | tsconfig.json |

---

## 3. Implementation Plan

### Reference Implementation Decomposition

The `/adk-ts-agent` folder will be decomposed as follows:

| Source (`/adk-ts-agent/`) | Destination | Layer |
|---------------------------|-------------|-------|
| `package.json` | `base_templates/typescript/` | Base |
| `tsconfig.json` | `base_templates/typescript/` | Base |
| `vitest.config.ts` | `base_templates/typescript/` | Base |
| `eslint.config.mjs` | `base_templates/typescript/` | Base |
| `.env`, `.env.example` | `base_templates/typescript/` | Base |
| `.gitignore`, `.dockerignore` | `base_templates/typescript/` | Base |
| `Makefile` | `base_templates/typescript/` | Base |
| `README.md` | `base_templates/typescript/` | Base |
| `.cloudbuild/*` | `base_templates/typescript/` | Base |
| `tests/unit/*` | `base_templates/typescript/tests/unit/` | Base |
| `tests/integration/server_e2e.test.ts` | `base_templates/typescript/tests/integration/` | Base |
| `tests/load_test/*` | `base_templates/typescript/tests/load_test/` | Base |
| `Dockerfile` | `deployment_targets/cloud_run/typescript/` | Deployment |
| `deployment/terraform/*` | `deployment_targets/cloud_run/typescript/` | Deployment |
| `app/agent.ts` | `agents/adk_ts/app/` | Agent |
| `tests/integration/agent.test.ts` | `agents/adk_ts/tests/integration/` | Agent |

**Key Principle**: Files that are agent-agnostic go to `base_templates/`, deployment-specific files go to `deployment_targets/`, and agent-specific logic goes to `agents/`.

**Templatization Required**: When copying files, replace hardcoded values with Cookiecutter variables:
- `my-agent` / `adk-ts-agent` → `{{cookiecutter.project_name}}`
- `app/` references → `{{cookiecutter.agent_directory}}/`
- Project-specific names in Terraform → `var.project_name`

### Phase 1: Base Template (`base_templates/typescript/`)

Create all files that apply to ANY TypeScript project.

**Files to create:**
```
base_templates/typescript/
├── .asp.toml
├── .cloudbuild/
│   ├── pr_checks.yaml
│   ├── staging.yaml
│   └── deploy-to-prod.yaml
├── .github/workflows/
│   ├── pr_checks.yaml
│   ├── staging.yaml
│   └── deploy-to-prod.yaml
├── .env
├── .env.example
├── .gitignore
├── .dockerignore
├── eslint.config.mjs
├── vitest.config.ts
├── tsconfig.json
├── package.json
├── Makefile
├── README.md
├── app/
│   └── agent.ts                    # Placeholder (overwritten by agent template)
└── tests/
    ├── unit/
    │   └── dummy.test.ts
    ├── integration/
    │   └── server_e2e.test.ts
    └── load_test/
        ├── load_test.ts
        ├── README.md
        └── .results/.placeholder
```

### Phase 2: Deployment Target (`deployment_targets/cloud_run/typescript/`)

Create Cloud Run-specific files (parallel to Go).

**Files to create:**
```
deployment_targets/cloud_run/typescript/
├── Dockerfile
└── deployment/terraform/
    ├── service.tf
    └── dev/
        └── service.tf
```

### Phase 3: Agent Template (`agents/adk_ts/`)

Create the TypeScript ADK agent (parallel to adk_go).

**Files to create:**
```
agents/adk_ts/
├── .template/
│   └── templateconfig.yaml
└── app/
    ├── agent.ts
    └── agent.test.ts
```

### Phase 4: CLI Changes

#### 4a. Update `template.py`

**Changes:**
1. Add `"typescript"` to `SUPPORTED_LANGUAGES`
2. Add `"adk_ts"` to `PRIORITY_ORDER` in `get_available_agents()`
3. Add TypeScript to `GROUP_ORDER` for display sorting
4. Skip uv.lock handling for TypeScript (no Python lock file needed)
5. Add `_copy_without_render` patterns for TypeScript files

#### 4b. Update `enhance.py`

The enhance command has language-specific logic that needs TypeScript support.

**Current Go Detection Pattern:**
```python
# Line 737-740: Detect Go project
is_go_project = base_template and base_template.endswith("_go")
if asp_config and asp_config.get("language") == "go":
    is_go_project = True

# Line 743: Default agent directory
detected_agent_directory = "agent" if is_go_project else "app"

# Line 849-859: Agent file detection
agent_go = agent_folder / "agent.go"
is_go = (base_template and base_template.endswith("_go")) or (
    agent_go.exists() and not agent_py.exists() and not root_agent_yaml.exists()
)
```

**TypeScript Changes:**
```python
# Add TypeScript detection (parallel to Go)
is_go_project = base_template and base_template.endswith("_go")
is_ts_project = base_template and base_template.endswith("_ts")

if asp_config:
    if asp_config.get("language") == "go":
        is_go_project = True
    elif asp_config.get("language") == "typescript":
        is_ts_project = True

# Default agent directory (TypeScript uses "app" like Python)
if is_go_project:
    detected_agent_directory = "agent"
else:
    detected_agent_directory = "app"  # Both Python and TypeScript use "app"

# Add agent.ts file detection
agent_ts = agent_folder / "agent.ts"

# Update is_go and is_ts detection for file checking
is_go = (base_template and base_template.endswith("_go")) or (
    agent_go.exists() and not agent_py.exists() and not root_agent_yaml.exists()
)
is_ts = (base_template and base_template.endswith("_ts")) or (
    agent_ts.exists() and not agent_py.exists() and not root_agent_yaml.exists()
)

# Update file detection messages
if agent_ts.exists():
    console.print(f"✅ Found [cyan]/{final_agent_directory}/agent.ts[/cyan]")
elif agent_go.exists():
    console.print(f"✅ Found [cyan]/{final_agent_directory}/agent.go[/cyan]")
elif agent_py.exists():
    # existing Python handling
    ...
else:
    # Update "file not found" message
    if is_go:
        agent_file = "agent.go"
    elif is_ts:
        agent_file = "agent.ts"
    else:
        agent_file = "agent.py"
```

**Key Points:**
- TypeScript uses `app/` as agent directory (same as Python, unlike Go's `agent/`)
- Detect `agent.ts` file in addition to `agent.py` and `agent.go`
- Check for `_ts` suffix in base_template name
- Check for `language == "typescript"` in `.asp.toml` config

### Phase 5: Lock File Generation (`generate_locks.py`)

Update `generate_locks.py` to handle TypeScript (parallel to Go pattern).

**Current Go Pattern:**
- Go is skipped in Python lock generation (line 201-202: `if config.get("language") == "go": continue`)
- Go has `generate_go_lock_file()` which creates `go.sum` and `go.mod` directly in `base_templates/go/`
- Lock files live in the base template, not in `resources/locks/`

**TypeScript Pattern (same approach):**
- Skip TypeScript in Python lock generation
- Add `generate_typescript_lock_file()` to create `package-lock.json` in `base_templates/typescript/`
- Run `npm install --package-lock-only` to generate lock file

```python
# In generate_locks.py

TS_BASE_TEMPLATE = pathlib.Path("agent_starter_pack/base_templates/typescript")

def generate_typescript_lock_file() -> None:
    """Generate package-lock.json for TypeScript base template."""
    package_json_path = TS_BASE_TEMPLATE / "package.json"

    if not package_json_path.exists():
        print("Skipping TypeScript lock generation: package.json not found")
        return

    print("Generating package-lock.json for TypeScript base template...")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_dir = pathlib.Path(tmpdir)
        project_name = "ts-lock-gen"

        # Generate a TypeScript project using the CLI
        subprocess.run(
            [
                "uv", "run", "agent-starter-pack", "create", project_name,
                "-p", "-s", "-y",
                "-a", "adk_ts",
                "-d", "cloud_run",
                "--output-dir", str(tmp_dir),
            ],
            check=True,
            capture_output=True,
        )

        project_dir = tmp_dir / project_name

        # Run npm install to generate lock file
        subprocess.run(
            ["npm", "install", "--package-lock-only"],
            cwd=project_dir,
            check=True,
        )

        # Copy package-lock.json back to template
        generated_lock = project_dir / "package-lock.json"
        if generated_lock.exists():
            # Replace project name with Jinja variable
            with open(generated_lock, encoding="utf-8") as f:
                lock_content = f.read()
            lock_content = lock_content.replace(
                project_name, "{{cookiecutter.project_name}}"
            )
            lock_path = TS_BASE_TEMPLATE / "package-lock.json"
            with open(lock_path, "w", encoding="utf-8") as f:
                f.write(lock_content)
            print(f"Generated {lock_path}")

# In main():
# Skip TypeScript in Python lock loop
if config.get("language") in ("go", "typescript"):
    continue

# At end of main():
generate_go_lock_file()
generate_typescript_lock_file()  # NEW
```

### Phase 6: Terraform Build Triggers (`.cloudbuild/terraform/build_triggers.tf`)

Update CI/CD triggers to include TypeScript agent testing.

**Current Go Pattern:**
```hcl
# In agent_testing_combinations:
{
  name  = "adk_go-cloud_run"
  value = "adk_go,cloud_run"
}

# Dedicated Go-specific included files:
go_agent_testing_included_files = {
  "adk_go-cloud_run" = [
    "agent_starter_pack/agents/adk_go/**",
    "agent_starter_pack/base_templates/_shared/**",
    "agent_starter_pack/base_templates/go/**",
    "agent_starter_pack/deployment_targets/cloud_run/_shared/**",
    "agent_starter_pack/deployment_targets/cloud_run/go/**",
    ...
  ]
}
```

**TypeScript Changes:**
```hcl
# Add to agent_testing_combinations:
{
  name  = "adk_ts-cloud_run"
  value = "adk_ts,cloud_run"
}

# Add TypeScript-specific included files:
ts_agent_testing_included_files = {
  "adk_ts-cloud_run" = [
    "agent_starter_pack/agents/adk_ts/**",
    "agent_starter_pack/base_templates/_shared/**",
    "agent_starter_pack/base_templates/typescript/**",
    "agent_starter_pack/deployment_targets/cloud_run/_shared/**",
    "agent_starter_pack/deployment_targets/cloud_run/typescript/**",
    "agent_starter_pack/cli/**",
    "tests/integration/test_template_linting.py",
    "tests/integration/test_templated_patterns.py",
    "agent_starter_pack/resources/locks/**",
    "pyproject.toml",
    "uv.lock",
  ]
}

# Add to e2e_agent_deployment_combinations:
{
  name  = "adk_ts-cloud_run"
  value = "adk_ts,cloud_run"
}

# Add to go_e2e_agent_deployment_included_files (rename to non_python_e2e_...):
ts_e2e_agent_deployment_included_files = {
  "adk_ts-cloud_run" = [
    "agent_starter_pack/agents/adk_ts/**",
    "agent_starter_pack/base_templates/_shared/**",
    "agent_starter_pack/base_templates/typescript/**",
    "agent_starter_pack/deployment_targets/cloud_run/_shared/**",
    "agent_starter_pack/deployment_targets/cloud_run/typescript/**",
    "agent_starter_pack/cli/**",
    "tests/cicd/test_e2e_deployment.py",
    "agent_starter_pack/resources/locks/**",
    "pyproject.toml",
    "uv.lock",
    ".cloudbuild/**",
  ]
}

# Update the lookup logic to check for _ts suffix (like _go):
agent_testing_included_files = {
  for combo in local.agent_testing_combinations :
  combo.name => (
    endswith(split(",", combo.value)[0], "_go") ? local.go_agent_testing_included_files[combo.name] :
    endswith(split(",", combo.value)[0], "_ts") ? local.ts_agent_testing_included_files[combo.name] :
    [...python files...]
  )
}
```

---

## 4. File Specifications

### 4.1 templateconfig.yaml (agents/adk_ts/)

```yaml
# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# ...

description: "Simple ReAct agent"
example_question: "What's the weather in San Francisco?"
settings:
  language: "typescript"
  requires_data_ingestion: false
  requires_session: false
  deployment_targets: ["cloud_run"]
  extra_dependencies: []
  tags: ["adk", "typescript"]
  frontend_type: "None"
  agent_directory: "app"
```

### 4.2 .asp.toml (base_templates/typescript/)

```toml
# Agent Starter Pack Configuration
# This file is used by the 'enhance' command to identify project settings

[project]
name = "{{cookiecutter.project_name}}"
version = "{{cookiecutter.package_version}}"
language = "typescript"
base_template = "{{cookiecutter.agent_name}}"
deployment_target = "{{cookiecutter.deployment_target}}"
cicd_runner = "{{cookiecutter.cicd_runner}}"
```

### 4.3 package.json (base_templates/typescript/)

```json
{
  "name": "{{cookiecutter.project_name}}",
  "version": "1.0.0",
  "description": "AI Agent built with Google ADK (TypeScript)",
  "type": "module",
  "main": "app/agent.ts",
  "scripts": {
    "build": "tsc",
    "dev": "npm run build && npx @google/adk-devtools web --port 3000",
    "run": "npm run build && npx @google/adk-devtools run dist/agent.js",
    "start": "npm run build && npx @google/adk-devtools api_server dist/agent.js --port 8080",
    "test": "vitest run",
    "test:unit": "vitest run tests/unit",
    "test:integration": "vitest run tests/integration",
    "lint": "eslint .",
    "lint:fix": "eslint . --fix",
    "typecheck": "tsc --noEmit"
  },
  "dependencies": {
    "@google/adk": "^0.2.0",
    "zod": "^3.25.76"
  },
  "devDependencies": {
    "@google/adk-devtools": "^0.2.0",
    "@types/node": "^22.0.0",
    "dotenv": "^16.4.5",
    "eslint": "^9.0.0",
    "tsx": "^4.0.0",
    "typescript": "^5.9.0",
    "typescript-eslint": "^8.0.0",
    "vitest": "^3.0.0"
  },
  "engines": {
    "node": ">=20.0.0"
  }
}
```

### 4.4 tsconfig.json (base_templates/typescript/)

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "NodeNext",
    "moduleResolution": "NodeNext",
    "outDir": "./dist",
    "rootDir": "./app",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true,
    "declaration": true,
    "declarationMap": true,
    "sourceMap": true
  },
  "include": ["app/**/*"],
  "exclude": ["node_modules", "dist", "tests"]
}
```

### 4.5 agent.ts (agents/adk_ts/app/)

```typescript
{%- if not cookiecutter.use_google_api_key %}
// Configure Vertex AI
process.env.GOOGLE_GENAI_USE_VERTEXAI = "true";
{%- endif %}

import { FunctionTool, LlmAgent } from "@google/adk";
import { z } from "zod";

/**
 * Tool: Get current weather for a city
 */
const getWeather = new FunctionTool({
  name: "get_weather",
  description: "Returns the current weather in a specified city.",
  parameters: z.object({
    city: z.string().describe("The city to get weather for"),
  }),
  execute: async ({ city }) => {
    return {
      status: "success",
      report: `The weather in ${city} is sunny with a high of 75°F.`,
    };
  },
});

/**
 * Tool: Get current time for a city
 */
const getTime = new FunctionTool({
  name: "get_time",
  description: "Returns the current time in a specified city.",
  parameters: z.object({
    city: z.string().describe("The city to get time for"),
  }),
  execute: async ({ city }) => {
    const now = new Date();
    return {
      status: "success",
      time: `The current time in ${city} is ${now.toLocaleTimeString()}.`,
    };
  },
});

/**
 * Root Agent: Weather and Time Assistant
 */
export const rootAgent = new LlmAgent({
  name: "{{cookiecutter.project_name}}_agent",
  model: "gemini-2.0-flash",
  description: "An assistant that provides weather and time information.",
  instruction: `You are a helpful assistant that can provide weather and time information.

When asked about weather, use the get_weather tool.
When asked about time, use the get_time tool.
Always be friendly and concise in your responses.`,
  tools: [getWeather, getTime],
});
```

### 4.6 Dockerfile (deployment_targets/cloud_run/typescript/)

```dockerfile
# Build stage
FROM node:20-slim AS builder

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

# Runtime stage
FROM node:20-slim AS runtime

WORKDIR /app

COPY package*.json ./
RUN npm ci --omit=dev

COPY --from=builder /app/dist ./dist

ARG COMMIT_SHA="unknown"
ARG AGENT_VERSION="1.0.0"
ENV COMMIT_SHA=${COMMIT_SHA}
ENV AGENT_VERSION=${AGENT_VERSION}

EXPOSE 8080

CMD ["npx", "@google/adk-devtools", "api_server", "dist/agent.js", "--port", "8080"]
```

### 4.7 service.tf (deployment_targets/cloud_run/typescript/)

```hcl
# Cloud Run service for TypeScript agent
# Parallel to cloud_run/go/deployment/terraform/service.tf

data "google_project" "deploy_projects" {
  for_each   = local.deploy_project_ids
  project_id = each.value
}

resource "google_cloud_run_v2_service" "agent" {
  for_each = local.deploy_project_ids
  provider = google

  name                = var.project_name
  location            = var.region
  project             = each.value
  deletion_protection = false
  ingress             = "INGRESS_TRAFFIC_ALL"

  labels = {
    created-by      = "asp"
    agent-framework = "google-adk"
    language        = "typescript"
  }

  template {
    service_account = google_service_account.app_sa[each.key].email

    containers {
      # Placeholder image - will be replaced by CI/CD pipeline
      image = "us-docker.pkg.dev/cloudrun/container/hello"

      resources {
        limits = {
          cpu    = "4"
          memory = "8Gi"
        }
        cpu_idle = false
      }

      env {
        name  = "LOGS_BUCKET_NAME"
        value = google_storage_bucket.logs[each.value].name
      }
      env {
        name  = "GOOGLE_GENAI_USE_VERTEXAI"
        value = "true"
      }
      env {
        name  = "GOOGLE_CLOUD_PROJECT"
        value = each.value
      }
      env {
        name  = "GOOGLE_CLOUD_LOCATION"
        value = var.region
      }
    }

    scaling {
      min_instance_count = 1
      max_instance_count = 10
    }

    max_instance_request_concurrency = 40
    session_affinity                 = true
  }

  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }

  lifecycle {
    ignore_changes = [
      template[0].containers[0].image,
    ]
  }
}
```

### 4.8 Makefile (base_templates/typescript/)

```makefile
.PHONY: install build dev run test lint typecheck clean deploy playground local-backend load-test

# Project configuration
PROJECT_NAME := {{cookiecutter.project_name}}
REGION := us-central1
PORT := 8080

install:
	npm ci

build:
	npm run build

playground:
	npm run dev

run:
	npm run run

local-backend:
	npm run start

test:
	npm run test

test-unit:
	npm run test:unit

test-integration:
	npm run test:integration

lint:
	npm run lint

lint-fix:
	npm run lint:fix

typecheck:
	npm run typecheck

clean:
	rm -rf dist node_modules

load-test:
	npx tsx tests/load_test/load_test.ts

deploy:
	gcloud run deploy $(PROJECT_NAME) \
		--source . \
		--region $(REGION) \
		--port $(PORT) \
		--set-env-vars="GOOGLE_GENAI_USE_VERTEXAI=true" \
		--set-env-vars="GOOGLE_CLOUD_PROJECT=$$(gcloud config get-value project)" \
		--set-env-vars="GOOGLE_CLOUD_LOCATION=$(REGION)"

setup-dev-env:
	cd deployment/terraform/dev && \
	terraform init && \
	terraform apply -var-file=vars/env.tfvars
```

### 4.9 pr_checks.yaml (.cloudbuild/)

```yaml
steps:
  - id: "install-dependencies"
    name: "node:20-slim"
    entrypoint: "npm"
    args: ["ci"]

  - id: "build"
    name: "node:20-slim"
    entrypoint: "npm"
    args: ["run", "build"]
    waitFor: ["install-dependencies"]

  - id: "lint"
    name: "node:20-slim"
    entrypoint: "npm"
    args: ["run", "lint"]
    waitFor: ["install-dependencies"]

  - id: "typecheck"
    name: "node:20-slim"
    entrypoint: "npm"
    args: ["run", "typecheck"]
    waitFor: ["install-dependencies"]

  - id: "unit-tests"
    name: "node:20-slim"
    entrypoint: "npm"
    args: ["run", "test:unit"]
    waitFor: ["build"]
    env:
      - "GOOGLE_GENAI_USE_VERTEXAI=true"
      - "GOOGLE_CLOUD_PROJECT=$PROJECT_ID"
      - "GOOGLE_CLOUD_LOCATION=$_REGION"

  - id: "integration-tests"
    name: "node:20-slim"
    entrypoint: "npm"
    args: ["run", "test:integration"]
    waitFor: ["build"]
    env:
      - "GOOGLE_GENAI_USE_VERTEXAI=true"
      - "GOOGLE_CLOUD_PROJECT=$PROJECT_ID"
      - "GOOGLE_CLOUD_LOCATION=$_REGION"

options:
  logging: CLOUD_LOGGING_ONLY

substitutions:
  _REGION: "us-central1"

logsBucket: "gs://${PROJECT_ID}-{{cookiecutter.project_name}}-logs/build-logs"
```

---

## 5. CLI Changes

### 5.1 template.py Modifications

```python
# Line ~348: Add TypeScript to supported languages
SUPPORTED_LANGUAGES = ["python", "go", "typescript"]

# Line ~368: Add to PRIORITY_ORDER
PRIORITY_ORDER = {
    "adk": 0,
    "adk_a2a": 1,
    "adk_live": 2,
    "agentic_rag": 3,
    "langgraph": 0,
    "adk_go": 0,
    "adk_ts": 0,  # NEW
}

# Line ~419: Add to GROUP_ORDER
GROUP_ORDER = {
    ("python", "adk"): 0,
    ("python", "langgraph"): 1,
    ("go", "adk"): 2,
    ("typescript", "adk"): 3,  # NEW
}

# Line ~1279: Already includes TypeScript in _copy_without_render
"_copy_without_render": [
    "*.ts",   # Don't render TypeScript files
    "*.tsx",  # Don't render TypeScript React files
    ...
]

# Line ~1682-1714: Skip Python-specific lock file handling for TypeScript
if language == "python":
    # existing uv.lock handling
elif language == "go":
    # Go doesn't need special lock handling (go.sum is in base template)
    pass
elif language == "typescript":
    # TypeScript doesn't need special lock handling (package-lock.json is in base template)
    pass
```

### 5.2 GCP Project Handling for Non-Python Templates

**Discovery**: Go templates have special handling in `create.py` (lines 887-902) to fetch the GCP project ID from gcloud even when `--skip-checks` is used. This is necessary because Go/TypeScript templates use `.env` files that require a valid GCP project ID for local development with Vertex AI.

**Why This Matters**:
- Python templates work without this because they can use ADC (Application Default Credentials) directly
- Go/TypeScript templates load `.env` files at runtime, which need the project ID populated
- The `.env` file uses `{{cookiecutter.google_cloud_project}}` which defaults to `"your-gcp-project-id"` if not provided
- Without the special handling, tests fail with "Permission denied on resource project your-gcp-project-id"

**Implementation**:
```python
# In create.py (line 887-902)
elif skip_checks and not google_api_key and (
    final_agent.endswith("_go") or final_agent.endswith("_ts")
):
    # For Go/TypeScript templates, try to get project ID from gcloud config even when skipping checks
    # This is needed because their .env requires a valid project ID for local development
    try:
        result = subprocess.run(
            ["gcloud", "config", "get-value", "project"],
            capture_output=True,
            text=True,
            check=False,
        )
        project_id = result.stdout.strip()
        if project_id:
            creds_info = {"project": project_id}
            logging.debug(f"Got project ID from gcloud config: {project_id}")
    except Exception as e:
        logging.debug(f"Could not get project ID from gcloud: {e}")
```

**TypeScript was added to this check** to match Go's behavior.

### 5.3 Summary of CLI Changes

| Change | Location | Description |
|--------|----------|-------------|
| Add language | `SUPPORTED_LANGUAGES` | Add `"typescript"` |
| Add priority | `PRIORITY_ORDER` | Add `"adk_ts": 0` |
| Add group order | `GROUP_ORDER` | Add `("typescript", "adk"): 3` |
| Skip lock handling | `process_template()` | No uv.lock for TypeScript |
| GCP project handling | `create.py` | Add `_ts` to project ID fetch with `--skip-checks` |

### Phase 7: Documentation Updates

Update user-facing documentation to include TypeScript (parallel to Go).

**Key Files to Update:**

#### docs/agents/overview.md

Add to the templates table:
```markdown
| `adk_ts` | A base ReAct agent implemented using Google's [Agent Development Kit for TypeScript](https://github.com/anthropics/adk-ts) | TypeScript-based conversational agent |
```

Add new section:
```markdown
### ADK Base TypeScript (`adk_ts`)

This template provides a minimal example of a ReAct agent built using Google's [Agent Development Kit for TypeScript](https://github.com/google/adk-ts). It offers the same core ADK concepts as the Python version but for TypeScript/JavaScript developers. Ideal for:

*   TypeScript/JavaScript developers building agents on Google Cloud.
*   Teams with existing Node.js codebases wanting to add AI agent capabilities.
*   Full-stack JavaScript teams leveraging familiar tooling (npm, vitest, eslint).

**Note:** Currently supports Cloud Run deployment only.
```

Update "Choosing the Right Template" factor:
```markdown
2.  **Programming Language**: Do you prefer Python, Go, or TypeScript? Most templates are Python-based, but `adk_go` provides a Go alternative and `adk_ts` provides a TypeScript alternative.
```

#### docs/guide/getting-started.md

Update Prerequisites:
```markdown
**Python 3.10+** (or **Go 1.21+** for Go templates, or **Node.js 20+** for TypeScript templates) | ...
```

Add example:
```bash
# TypeScript agent with Cloud Run
agent-starter-pack create my-ts-agent -a adk_ts -d cloud_run
```

Update directory structure:
```markdown
*   `app/` (Python/TypeScript) or `agent/` (Go): Backend agent code.
*   `tests/` (Python/TypeScript) or `e2e/` (Go): Unit and integration tests.
```

#### docs/cli/create.md

Add to Basic Usage:
```bash
# Create a TypeScript agent (Cloud Run only)
uvx agent-starter-pack create my-ts-agent -a adk_ts
```

#### docs/guide/installation.md

Add Node.js section:
```markdown
### Node.js (for TypeScript templates)

TypeScript templates require Node.js 20 or later:

- **macOS/Linux:** Use [nvm](https://github.com/nvm-sh/nvm) or download from [nodejs.org](https://nodejs.org/)
- **Windows:** Download from [nodejs.org](https://nodejs.org/) or use [nvm-windows](https://github.com/coreybutler/nvm-windows)

Verify installation:
```bash
node --version  # Should be v20.x or later
npm --version
```

---

## 6. Testing Strategy

### 6.1 Template Generation Test

```bash
# Test TypeScript agent creation (parallel to Go test)
uv run agent-starter-pack create test-ts-$(date +%s) \
  --agent adk_ts \
  --deployment-target cloud_run \
  --prototype \
  --skip-checks \
  --auto-approve \
  --output-dir target
```

### 6.2 Generated Project Verification

```bash
cd target/test-ts-*

# Install dependencies
npm install

# Build
npm run build

# Lint
npm run lint

# Type check
npm run typecheck

# Unit tests
npm run test:unit

# Integration tests
npm run test:integration

# Start local server
npm run start

# Docker build
docker build -t test-ts-agent .
```

### 6.3 CI/CD Test Matrix

| Test | adk_ts + cloud_run |
|------|-------------------|
| Project creation | ✓ |
| npm install | ✓ |
| npm run build | ✓ |
| npm run lint | ✓ |
| npm run test | ✓ |
| Docker build | ✓ |
| Cloud Run deploy | ✓ |

---

## 7. Open Questions

### 7.1 Decisions to Confirm

| Question | Go Pattern | TypeScript Proposal |
|----------|------------|---------------------|
| Agent directory | `agent/` | `app/` (match Python) |
| Tests directory | `e2e/` | `tests/` (match reference) |
| Lock file location | `go.sum` in base_templates | `package-lock.json` in base_templates |
| Entry point | `main.go` | None (adk-devtools handles) |

### 7.2 Future Considerations

- **Agent Engine**: Requires TypeScript SDK for Vertex AI Agent Engine
- **GitHub Actions**: Add parallel to Cloud Build (like Go has)
- **Session management**: Cloud SQL support in TypeScript
- **A2A protocol**: TypeScript implementation

---

## Appendix A: File Mapping from Reference (/adk-ts-agent)

| Reference File | Template Location |
|----------------|-------------------|
| `app/agent.ts` | `agents/adk_ts/app/agent.ts` |
| `package.json` | `base_templates/typescript/package.json` |
| `tsconfig.json` | `base_templates/typescript/tsconfig.json` |
| `vitest.config.ts` | `base_templates/typescript/vitest.config.ts` |
| `eslint.config.mjs` | `base_templates/typescript/eslint.config.mjs` |
| `Makefile` | `base_templates/typescript/Makefile` |
| `Dockerfile` | `deployment_targets/cloud_run/typescript/Dockerfile` |
| `.cloudbuild/*` | `base_templates/typescript/.cloudbuild/*` |
| `tests/unit/*` | `base_templates/typescript/tests/unit/*` |
| `tests/integration/*` | `base_templates/typescript/tests/integration/*` |
| `tests/load_test/*` | `base_templates/typescript/tests/load_test/*` |
| `deployment/terraform/*` | `deployment_targets/cloud_run/typescript/deployment/terraform/*` |

---

## Appendix B: Implementation Checklist

### Phase 1: Base Template
- [ ] Create `base_templates/typescript/` directory
- [ ] Add `.asp.toml`
- [ ] Add `package.json`
- [ ] Add `tsconfig.json`
- [ ] Add `vitest.config.ts`
- [ ] Add `eslint.config.mjs`
- [ ] Add `.env` and `.env.example`
- [ ] Add `.gitignore` and `.dockerignore`
- [ ] Add `Makefile`
- [ ] Add `README.md`
- [ ] Add `app/agent.ts` (placeholder)
- [ ] Add `tests/unit/dummy.test.ts`
- [ ] Add `tests/integration/server_e2e.test.ts`
- [ ] Add `tests/load_test/load_test.ts`
- [ ] Add `.cloudbuild/` workflows
- [ ] Add `.github/workflows/` (optional)

### Phase 2: Deployment Target
- [ ] Create `deployment_targets/cloud_run/typescript/`
- [ ] Add `Dockerfile`
- [ ] Add `deployment/terraform/service.tf`
- [ ] Add `deployment/terraform/dev/service.tf`

### Phase 3: Agent Template
- [ ] Create `agents/adk_ts/`
- [ ] Add `.template/templateconfig.yaml`
- [ ] Add `app/agent.ts`
- [ ] Add `app/agent.test.ts`

### Phase 4: CLI Changes

#### 4a: `template.py`
- [ ] Add `"typescript"` to `SUPPORTED_LANGUAGES`
- [ ] Add `"adk_ts"` to `PRIORITY_ORDER`
- [ ] Add TypeScript to `GROUP_ORDER`
- [ ] Skip uv.lock for TypeScript (like Go)

#### 4b: `enhance.py`
- [ ] Add `is_ts_project` detection (parallel to `is_go_project`)
- [ ] Add `agent.ts` file detection
- [ ] Update agent file detection messages for TypeScript
- [ ] Update "file not found" suggestions for TypeScript

#### 4c: `extract.py`
- [ ] Add `"typescript"` to `LANGUAGE_CONFIGS` dictionary
- [ ] Update `detect_language()` to check TypeScript before Python
- [ ] Update `detect_agent_directory()` to check for `agent.ts`
- [ ] Update agent file warning to handle `agent.ts`

The extract command uses an extensible `LANGUAGE_CONFIGS` dictionary. Add TypeScript support:

```python
# Add to LANGUAGE_CONFIGS (line ~91-114)
"typescript": {
    "detection_files": ["package.json", "tsconfig.json"],
    "config_file": ".asp.toml",  # Same as Go
    "config_path": ["project"],   # Same as Go
    "project_files": [
        "package.json",
        "package-lock.json",
        "tsconfig.json",
        "vitest.config.ts",
        "eslint.config.mjs",
        ".asp.toml",
    ],
    "lock_file": "package-lock.json",
    "lock_command": ["npm", "install", "--package-lock-only"],
    "lock_command_name": "npm install --package-lock-only",
    "strip_dependencies": False,  # Keep package.json as-is
    "display_name": "TypeScript",
},
```

**Additional Changes:**
- Update `detect_language()` (line ~201) to check TypeScript before Python:
  ```python
  for lang in ["go", "typescript", "python"]:  # TypeScript before Python
  ```
- Update `detect_agent_directory()` (line ~156-159) to also check for `agent.ts`:
  ```python
  for candidate in ["app", "agent", "src"]:
      candidate_path = project_dir / candidate
      if candidate_path.is_dir() and (
          (candidate_path / "agent.py").exists() or
          (candidate_path / "agent.ts").exists()
      ):
          return candidate
  ```
- Update agent file warning (line ~716-719) to handle `agent.ts`

### Phase 5: Lock File Generation (`generate_locks.py`)
- [ ] Add `TS_BASE_TEMPLATE` path constant
- [ ] Add `generate_typescript_lock_file()` function
- [ ] Skip TypeScript in Python lock loop (`if config.get("language") in ("go", "typescript"): continue`)
- [ ] Call `generate_typescript_lock_file()` at end of `main()`
- [ ] Test `make generate-lock` includes TypeScript

### Phase 6: Terraform Build Triggers (`build_triggers.tf`)
- [ ] Add `adk_ts-cloud_run` to `agent_testing_combinations`
- [ ] Add `ts_agent_testing_included_files` local variable
- [ ] Add `adk_ts-cloud_run` to `e2e_agent_deployment_combinations`
- [ ] Add `ts_e2e_agent_deployment_included_files` local variable
- [ ] Update `agent_testing_included_files` lookup to handle `_ts` suffix
- [ ] Update `e2e_agent_deployment_included_files` lookup to handle `_ts` suffix
- [ ] Apply Terraform changes to create new triggers

### Phase 7: Documentation Updates

#### docs/agents/overview.md
- [ ] Add `adk_ts` to the Available Templates table
- [ ] Add "ADK Base TypeScript (`adk_ts`)" section (parallel to Go section)
- [ ] Update "Programming Language" factor to include TypeScript

#### docs/guide/getting-started.md
- [ ] Add **Node.js 20+** to Prerequisites (alongside Python and Go)
- [ ] Add TypeScript example in "Examples" section
- [ ] Update directory structure to include TypeScript (`app/` for TS)

#### docs/cli/create.md
- [ ] Add TypeScript example command: `agent-starter-pack create my-ts-agent -a adk_ts -d cloud_run`
- [ ] Update "Basic Usage" section with TypeScript example

#### docs/guide/installation.md
- [ ] Add Node.js installation instructions
- [ ] Add npm as package manager option

#### docs/guide/development-guide.md
- [ ] Add TypeScript development workflow section
- [ ] Add npm commands (parallel to uv/go commands)

#### docs/index.md (if applicable)
- [ ] Update any language mentions to include TypeScript

### Phase 8: Test File Updates

#### tests/integration/test_templated_patterns.py
The test file has language-specific logic for Go that needs TypeScript parallel:

```python
# Current (line ~70):
is_go = (project_path / "go.mod").exists()

# Add TypeScript detection:
is_go = (project_path / "go.mod").exists()
is_ts = (project_path / "package.json").exists() and (project_path / "tsconfig.json").exists()

# Update essential files check:
if is_go:
    essential_files = ["go.mod", "main.go", "agent/agent.go", "Makefile"]
elif is_ts:
    essential_files = ["package.json", "tsconfig.json", "app/agent.ts", "Makefile"]
else:
    essential_files = [...]  # Python
```

#### tests/integration/test_template_linting.py
- [ ] Add TypeScript linting validation (eslint, tsc)
- [ ] Skip Python-specific linting (ruff, ty) for TypeScript

#### lock_utils.py (if needed)
The file has hardcoded `uv-*` lock file naming. TypeScript doesn't use this pattern (lock is in base_templates), but verify no changes needed.

### Phase 9: Testing & Validation
- [ ] Test `uv run agent-starter-pack create` with `--agent adk_ts`
- [ ] Test `npm install && npm run build`
- [ ] Test `npm run lint && npm run typecheck`
- [ ] Test `npm run test`
- [ ] Test Docker build
- [ ] Test Cloud Run deployment
- [ ] Test `make generate-lock` regenerates TypeScript lock
- [ ] Verify CI triggers fire correctly on PR
- [ ] Verify documentation renders correctly
- [ ] Run integration tests with TypeScript combinations
