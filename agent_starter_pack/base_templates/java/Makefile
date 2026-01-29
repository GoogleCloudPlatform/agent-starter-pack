# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

{%- if extracted|default(false) %}
# ==============================================================================
# Minimal Makefile for Extracted Agent
# ==============================================================================
# This agent was extracted from a full agent-starter-pack project.
# Run `agent-starter-pack enhance` to add deployment capabilities.
# ==============================================================================

{%- else %}
# ==============================================================================
# Installation & Setup
# ==============================================================================
{%- endif %}

# Download Maven dependencies
install:
	mvn dependency:resolve

# ==============================================================================
# Playground Targets
# ==============================================================================

# Launch local dev playground with web UI
# Endpoints:
#   - Dev UI:     http://localhost:8080/dev-ui/
#   - A2A:        http://localhost:8080/a2a/remote/v1/message:send
#   - AgentCard:  http://localhost:8080/.well-known/agent-card.json
playground:
	@echo "==============================================================================="
	@echo "| Starting your agent playground...                                           |"
	@echo "|                                                                             |"
	@echo "| Open: http://localhost:8080/dev-ui/                                         |"
	@echo "| AgentCard: http://localhost:8080/.well-known/agent-card.json                |"
	@echo "| Try asking: What's the weather in San Francisco?                            |"
	@echo "==============================================================================="
	mvn compile exec:java
{%- if not extracted|default(false) %}

# ==============================================================================
# Local Development Commands
# ==============================================================================

# Launch local development server (matches Cloud Run)
local-backend:
	mvn compile exec:java

# ==============================================================================
# Backend Deployment Targets
# ==============================================================================

# Deploy the agent remotely
# Usage: make deploy [PORT=8080]
#   PORT=8080 - Specify container port
deploy:
	PROJECT_ID=$$(gcloud config get-value project) && \
	PROJECT_NUMBER=$$(gcloud projects describe $$PROJECT_ID --format="value(projectNumber)") && \
	gcloud run deploy {{cookiecutter.project_name}} \
		--source . \
		--memory "4Gi" \
		--project $$PROJECT_ID \
		--region "us-central1" \
		--no-allow-unauthenticated \
		--no-cpu-throttling \
		--labels "created-by=adk" \
		--update-env-vars "GOOGLE_CLOUD_PROJECT=$$PROJECT_ID,GOOGLE_CLOUD_LOCATION=global,GOOGLE_GENAI_USE_VERTEXAI=True" \
		$(if $(PORT),--port=$(PORT))

# Alias for 'make deploy' for backward compatibility
backend: deploy

# ==============================================================================
# Infrastructure Setup
# ==============================================================================

# Set up development environment resources using Terraform
setup-dev-env:
	PROJECT_ID=$$(gcloud config get-value project) && \
	(cd deployment/terraform/dev && terraform init && terraform apply --var-file vars/env.tfvars --var dev_project_id=$$PROJECT_ID --auto-approve)
{%- endif %}

# ==============================================================================
# Testing & Code Quality
# ==============================================================================

# Run unit tests
test:
	mvn test

# Run code quality checks (compile verification)
lint:
	mvn compile -q

# Build the project
build:
	mvn package -DskipTests

# Clean build artifacts
clean:
	mvn clean
