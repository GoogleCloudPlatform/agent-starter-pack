# Copyright 2026 Google LLC
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

# Load .env file if it exists (for local development)
ifneq (,$(wildcard ./.env))
    include .env
    export
endif

# ==============================================================================
# Installation & Setup
# ==============================================================================

# Download Maven dependencies
install:
	mvn dependency:resolve

# ==============================================================================
# Playground Targets
# ==============================================================================

# Launch local dev playground with web UI
# Endpoints:
#   - ADK Web:     http://localhost:8080/dev-ui
playground:
	@echo "==============================================================================="
	@echo "| Starting your agent playground...                                           |"
	@echo "|                                                                             |"
	@echo "| ADK Web: http://localhost:8080/dev-ui                                       |"
	@echo "| Try asking: What's the weather in San Francisco?                            |"
	@echo "==============================================================================="
	mvn compile exec:java -Dlogging.level.root=WARN -Dlogging.level.com.google.adk=INFO

# ==============================================================================
# Local Development Commands
# ==============================================================================

# Launch local development server (matches Cloud Run)
local-backend:
	mvn compile exec:java -Dlogging.level.root=WARN -Dlogging.level.com.google.adk=INFO

# ==============================================================================
# Backend Deployment Targets
# ==============================================================================

# Deploy the agent remotely
# Usage: make deploy [IMAGE_TAG=mytag]
#   IMAGE_TAG - Specify the Docker image tag (defaults to timestamp)
#
# Deploys to GKE cluster
# Example: make deploy IMAGE_TAG=v1.0.0
deploy:
	@PROJECT_ID=$$(gcloud config get-value project) && \
	echo "Provisioning infrastructure via Terraform..." && \
	(cd deployment/terraform/dev && terraform init && \
	terraform apply --var-file vars/env.tfvars --var dev_project_id=$$PROJECT_ID --auto-approve) && \
	echo "Configuring kubectl credentials..." && \
	gcloud container clusters get-credentials test-java-agent-dev --region us-central1 --project $$PROJECT_ID && \
	IMAGE_TAG=$${IMAGE_TAG:-$$(date +%Y%m%d%H%M%S)} && \
	IMAGE=us-central1-docker.pkg.dev/$$PROJECT_ID/test-java-agent/test-java-agent:$$IMAGE_TAG && \
	echo "Building and pushing Docker image..." && \
	gcloud builds submit --tag $$IMAGE && \
	echo "Deploying container image..." && \
	kubectl apply -f deployment/k8s/deployment.yaml && \
	kubectl set image deployment/test-java-agent \
		test-java-agent=$$IMAGE \
		-n test-java-agent && \
	echo "Waiting for rollout to complete..." && \
	kubectl rollout status deployment/test-java-agent -n test-java-agent --timeout=300s && \
	EXTERNAL_IP=$$(kubectl get svc test-java-agent -n test-java-agent -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null) && \
	if [ -n "$$EXTERNAL_IP" ]; then \
		kubectl set env deployment/test-java-agent APP_URL=http://$$EXTERNAL_IP:8080 -n test-java-agent; \
		echo ""; \
		echo "==============================================================================="; \
		echo "  Service URL: http://$$EXTERNAL_IP:8080"; \
		echo "==============================================================================="; \
	else \
		echo "External IP is still being provisioned. Check with:"; \
		echo "  kubectl get svc test-java-agent -n test-java-agent"; \
	fi

# Alias for 'make deploy' for backward compatibility
backend: deploy

# ==============================================================================
# Infrastructure Setup
# ==============================================================================

# Set up development environment resources using Terraform
setup-dev-env:
	PROJECT_ID=$$(gcloud config get-value project) && \
	(cd deployment/terraform/dev && terraform init && terraform apply --var-file vars/env.tfvars --var dev_project_id=$$PROJECT_ID --auto-approve)

# ==============================================================================
# Testing & Code Quality
# ==============================================================================

# Run unit and e2e tests
test:
	mvn test

# Run load tests
# Usage: make load-test [URL=http://127.0.0.1:8080] [DURATION=30] [USERS=10] [RAMP=2]
# Local:  make load-test
# Remote: make load-test URL=https://your-service.run.app
load-test:
	mvn test-compile failsafe:integration-test failsafe:verify \
		-Dstaging.url=$(or $(URL),http://127.0.0.1:8080) \
		-Dload.duration=$(or $(DURATION),30) \
		-Dload.users=$(or $(USERS),10) \
		-Dload.ramp=$(or $(RAMP),2)

# Run code quality checks
lint:
	mvn checkstyle:check

# Build the project
build:
	mvn package -DskipTests

# Clean build artifacts
clean:
	mvn clean

# ==============================================================================
# A2A Protocol Inspector
# ==============================================================================

# Launch A2A Protocol Inspector to test your agent implementation
inspector: setup-inspector-if-needed build-inspector-if-needed
	@echo "==============================================================================="
	@echo "| A2A Protocol Inspector                                                      |"
	@echo "==============================================================================="
	@echo "| Inspector UI: http://localhost:5001                                         |"
	@echo "|                                                                             |"
	@echo "| Testing Locally:                                                            |"
	@echo "|    Paste this URL into the inspector:                                       |"
	@echo "|    http://localhost:8080/.well-known/agent-card.json                        |"
	@echo "|                                                                             |"
	@echo "| Testing Remote Deployment:                                                  |"
	@echo "|    1. Run: gcloud run services describe test-java-agent --region us-central1 |"
	@echo "|    2. Copy the URL and append: /.well-known/agent-card.json                 |"
	@echo "|                                                                             |"
	@echo "==============================================================================="
	cd tools/a2a-inspector/backend && uv run app.py

# Internal: Setup inspector if not already present
setup-inspector-if-needed:
	@if [ ! -d "tools/a2a-inspector" ]; then \
		mkdir -p tools && \
		git clone --quiet https://github.com/a2aproject/a2a-inspector.git tools/a2a-inspector && \
		(cd tools/a2a-inspector && git -c advice.detachedHead=false checkout --quiet 893e4062f6fbd85a8369228ce862ebbf4a025694) && \
		(cd tools/a2a-inspector && uv sync --quiet) && \
		(cd tools/a2a-inspector/frontend && npm install --silent && npm run build --silent); \
	fi

# Internal: Build inspector frontend if needed
build-inspector-if-needed:
	@if [ -d "tools/a2a-inspector" ] && [ ! -f "tools/a2a-inspector/frontend/public/script.js" ]; then \
		cd tools/a2a-inspector/frontend && npm run build; \
	fi
