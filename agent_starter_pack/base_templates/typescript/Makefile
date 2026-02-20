# ==============================================================================
# Installation & Setup
# ==============================================================================

# Install dependencies using npm
install:
	npm ci

# ==============================================================================
# Playground Targets
# ==============================================================================

# Launch local dev playground
playground:
	@echo "==============================================================================="
	@echo "| Starting your agent playground...                                           |"
	@echo "|                                                                             |"
	@echo "| Try asking: What's the weather in San Francisco?                             |"
	@echo "==============================================================================="
	npm run build && npm run dev

# ==============================================================================
# Local Development Commands
# ==============================================================================

# Launch local development server
local-backend:
	npm run build && npx @google/adk-devtools api_server -h localhost --port 8000 dist/agent.js

# Run agent with CLI
run:
	npm run run

# ==============================================================================
# Backend Deployment Targets
# ==============================================================================

# Deploy the agent remotely
{%- if cookiecutter.deployment_target == 'cloud_run' %}
# Usage: make deploy [IAP=true] [PORT=8080] - Set IAP=true to enable Identity-Aware Proxy, PORT to specify container port
deploy:
	PROJECT_ID=$$(gcloud config get-value project) && \
	AGENT_VERSION=$$(node -e "console.log(require('./package.json').version)") && \
	gcloud beta run deploy {{cookiecutter.project_name}} \
		--source . \
		--memory "4Gi" \
		--project $$PROJECT_ID \
		--region "us-central1" \
		--no-allow-unauthenticated \
		--no-cpu-throttling \
		--labels "created-by=adk" \
		--update-build-env-vars "AGENT_VERSION=$$AGENT_VERSION" \
		--update-env-vars \
		"COMMIT_SHA=$(shell git rev-parse HEAD),GOOGLE_GENAI_USE_VERTEXAI=true,GOOGLE_CLOUD_PROJECT=$$PROJECT_ID,GOOGLE_CLOUD_LOCATION=us-central1" \
		$(if $(IAP),--iap) \
		$(if $(PORT),--port=$(PORT))
{%- elif cookiecutter.deployment_target == 'gke' %}
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
	gcloud container clusters get-credentials {{cookiecutter.project_name}}-dev --region us-central1 --project $$PROJECT_ID && \
	IMAGE_TAG=$${IMAGE_TAG:-$$(date +%Y%m%d%H%M%S)} && \
	IMAGE=us-central1-docker.pkg.dev/$$PROJECT_ID/{{cookiecutter.project_name}}/{{cookiecutter.project_name}}:$$IMAGE_TAG && \
	echo "Building and pushing Docker image..." && \
	gcloud builds submit --tag $$IMAGE && \
	echo "Deploying container image..." && \
	kubectl apply -f deployment/k8s/deployment.yaml && \
	kubectl set image deployment/{{cookiecutter.project_name}} \
		{{cookiecutter.project_name}}=$$IMAGE \
		-n {{cookiecutter.project_name}} && \
	echo "Waiting for rollout to complete..." && \
	kubectl rollout status deployment/{{cookiecutter.project_name}} -n {{cookiecutter.project_name}} --timeout=300s && \
	EXTERNAL_IP=$$(kubectl get svc {{cookiecutter.project_name}} -n {{cookiecutter.project_name}} -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null) && \
	if [ -n "$$EXTERNAL_IP" ]; then \
		kubectl set env deployment/{{cookiecutter.project_name}} APP_URL=http://$$EXTERNAL_IP:8080 -n {{cookiecutter.project_name}}; \
		echo ""; \
		echo "==============================================================================="; \
		echo "  Service URL: http://$$EXTERNAL_IP:8080"; \
		echo "==============================================================================="; \
	else \
		echo "External IP is still being provisioned. Check with:"; \
		echo "  kubectl get svc {{cookiecutter.project_name}} -n {{cookiecutter.project_name}}"; \
	fi
{%- endif %}

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

# Run unit and integration tests
test:
	npm run test

# Run load tests (requires local-backend running in another terminal)
load-test:
	npx tsx tests/load_test/load_test.ts

# Run code quality checks
lint:
	npm run lint

# ==============================================================================
# TypeScript-specific targets
# ==============================================================================

# Build TypeScript
build:
	npm run build

# Type checking only
typecheck:
	npm run typecheck

# Clean build artifacts
clean:
	rm -rf dist node_modules
