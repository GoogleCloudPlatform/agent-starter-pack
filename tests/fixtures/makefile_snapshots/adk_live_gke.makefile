
# ==============================================================================
# Installation & Setup
# ==============================================================================

# Install dependencies using uv package manager
install:
	@command -v uv >/dev/null 2>&1 || { echo "uv is not installed. Installing uv..."; curl -LsSf https://astral.sh/uv/0.8.13/install.sh | sh; source $HOME/.local/bin/env; }
	uv sync && (cd frontend && npm install)

# ==============================================================================
# Playground Targets
# ==============================================================================

# Launch local dev playground
playground: build-frontend-if-needed
	@echo "==============================================================================="
	@echo "| 🚀 Starting your agent playground...                                        |"
	@echo "|                                                                             |"
	@echo "| 🌐 Access your app at: http://localhost:8000                               |"
	@echo "| 💡 Try asking: Tell me about your capabilities|"
	@echo "==============================================================================="
	uv run uvicorn test_adk_live.fast_api_app:app --host localhost --port 8000 --reload

# ==============================================================================
# Local Development Commands
# ==============================================================================

# Launch local development server with hot-reload
# Usage: make local-backend [PORT=8000] - Specify PORT for parallel scenario testing
local-backend:
	uv run uvicorn test_adk_live.fast_api_app:app --host localhost --port $(or $(PORT),8000) --reload

# ==============================================================================
# ADK Live Commands
# ==============================================================================

# Build the frontend for production
build-frontend:
	(cd frontend && npm run build)

# Build the frontend only if needed (conditional build)
build-frontend-if-needed:
	@if [ ! -d "frontend/build" ] || [ ! -f "frontend/build/index.html" ]; then \
		echo "Frontend build directory not found or incomplete. Building..."; \
		$(MAKE) build-frontend; \
	elif [ "frontend/package.json" -nt "frontend/build/index.html" ] || \
		 find frontend/src -newer frontend/build/index.html 2>/dev/null | head -1 | grep -q .; then \
		echo "Frontend source files are newer than build. Rebuilding..."; \
		$(MAKE) build-frontend; \
	else \
		echo "Frontend build is up to date. Skipping build..."; \
	fi

# ==============================================================================
# Backend Deployment Targets
# ==============================================================================

# Deploy the agent remotely
# Usage: make deploy [IMAGE_TAG=mytag] - Build and deploy to GKE cluster
deploy:
	@PROJECT_ID=$$(gcloud config get-value project) && \
	echo "Provisioning infrastructure via Terraform..." && \
	(cd deployment/terraform/dev && terraform init && \
	terraform apply --var-file vars/env.tfvars --var dev_project_id=$$PROJECT_ID --auto-approve) && \
	echo "Configuring kubectl credentials..." && \
	gcloud container clusters get-credentials test-adk-live-dev --region us-central1 --project $$PROJECT_ID && \
	IMAGE_TAG=$${IMAGE_TAG:-$$(date +%Y%m%d%H%M%S)} && \
	IMAGE=us-central1-docker.pkg.dev/$$PROJECT_ID/test-adk-live/test-adk-live:$$IMAGE_TAG && \
	echo "Building and pushing Docker image..." && \
	gcloud builds submit --tag $$IMAGE && \
	echo "Deploying container image..." && \
	kubectl apply -f deployment/k8s/deployment.yaml && \
	kubectl set image deployment/test-adk-live \
		test-adk-live=$$IMAGE \
		-n test-adk-live && \
	echo "Waiting for rollout to complete..." && \
	kubectl rollout status deployment/test-adk-live -n test-adk-live --timeout=300s && \
	EXTERNAL_IP=$$(kubectl get svc test-adk-live -n test-adk-live -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null) && \
	if [ -n "$$EXTERNAL_IP" ]; then \
		kubectl set env deployment/test-adk-live APP_URL=http://$$EXTERNAL_IP:8080 -n test-adk-live; \
		echo ""; \
		echo "==============================================================================="; \
		echo "  Service URL: http://$$EXTERNAL_IP:8080"; \
		echo "==============================================================================="; \
	else \
		echo "External IP is still being provisioned. Check with:"; \
		echo "  kubectl get svc test-adk-live -n test-adk-live"; \
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

# Run unit and integration tests
test:
	uv sync --dev
	uv run pytest tests/unit && uv run pytest tests/integration

# Run code quality checks (codespell, ruff, ty)
lint:
	uv sync --dev --extra lint
	uv run codespell
	uv run ruff check . --diff
	uv run ruff format . --check --diff
	uv run ty check .
