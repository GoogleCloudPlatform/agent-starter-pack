
# ==============================================================================
# Installation & Setup
# ==============================================================================

# Install dependencies using uv package manager
install:
	@command -v uv >/dev/null 2>&1 || { echo "uv is not installed. Installing uv..."; curl -LsSf https://astral.sh/uv/0.8.13/install.sh | sh; source $HOME/.local/bin/env; }
	uv sync

# ==============================================================================
# Playground Targets
# ==============================================================================

# Launch local dev playground
playground:
	@echo "==============================================================================="
	@echo "| 🚀 Starting your agent playground...                                        |"
	@echo "|                                                                             |"
	@echo "| 💡 Try asking: What can you help me with?|"
	@echo "|                                                                             |"
	@echo "| 🔍 IMPORTANT: Select the 'test_a2a' folder to interact with your agent.          |"
	@echo "==============================================================================="
	uv run adk web . --port 8501 --reload_agents

# ==============================================================================
# Local Development Commands
# ==============================================================================

# Launch local development server with hot-reload
# Usage: make local-backend [PORT=8000] - Specify PORT for parallel scenario testing
local-backend:
	uv run uvicorn test_a2a.fast_api_app:app --host localhost --port $(or $(PORT),8000) --reload

# ==============================================================================
# A2A Protocol Inspector
# ==============================================================================

# Launch A2A Protocol Inspector to test your agent implementation
inspector: setup-inspector-if-needed build-inspector-if-needed
	@echo "==============================================================================="
	@echo "| 🔍 A2A Protocol Inspector                                                  |"
	@echo "==============================================================================="
	@echo "| 🌐 Inspector UI: http://localhost:5001                                     |"
	@echo "|                                                                             |"
	@echo "| 💡 Testing Locally:                                                         |"
	@echo "|    Paste this URL into the inspector:                                      |"
	@echo "|    http://localhost:8000/a2a/test_a2a/.well-known/agent-card.json              |"
	@echo "|                                                                             |"
	@echo "| 💡 Testing Remote Deployment:                                               |"
	@echo "|    <SERVICE_URL>/a2a/test_a2a/.well-known/agent-card.json"
	@echo "|    (Get SERVICE_URL from 'make deploy' output or Cloud Console)            |"
	@echo "|                                                                             |"
	@echo "|    🔐 Auth: Expand 'Authentication & Headers', select 'Bearer Token',       |"
	@echo "|       and paste output of: gcloud auth print-identity-token                |"
	@echo "==============================================================================="
	@echo ""
	cd tools/a2a-inspector/backend && uv run app.py

# Internal: Setup inspector if not already present (runs once)
# TODO: Update to --branch v1.0.0 when a2a-inspector publishes releases
setup-inspector-if-needed:
	@if [ ! -d "tools/a2a-inspector" ]; then \
		echo "" && \
		echo "📦 First-time setup: Installing A2A Inspector..." && \
		echo "" && \
		mkdir -p tools && \
		git clone --quiet https://github.com/a2aproject/a2a-inspector.git tools/a2a-inspector && \
		(cd tools/a2a-inspector && git -c advice.detachedHead=false checkout --quiet 893e4062f6fbd85a8369228ce862ebbf4a025694) && \
		echo "📥 Installing Python dependencies..." && \
		(cd tools/a2a-inspector && uv sync --quiet) && \
		echo "📥 Installing Node.js dependencies..." && \
		(cd tools/a2a-inspector/frontend && npm install --silent) && \
		echo "🔨 Building frontend..." && \
		(cd tools/a2a-inspector/frontend && npm run build --silent) && \
		echo "" && \
		echo "✅ A2A Inspector setup complete!" && \
		echo ""; \
	fi

# Internal: Build inspector frontend if needed
build-inspector-if-needed:
	@if [ -d "tools/a2a-inspector" ] && [ ! -f "tools/a2a-inspector/frontend/public/script.js" ]; then \
		echo "🔨 Building inspector frontend..."; \
		cd tools/a2a-inspector/frontend && npm run build; \
	fi

# ==============================================================================
# Backend Deployment Targets
# ==============================================================================

# Deploy the agent remotely
# Usage: make deploy [IMAGE_TAG=mytag] - Build and deploy to GKE cluster
deploy:
	@PROJECT_ID=$$(gcloud config get-value project) && \
	echo "Enabling required APIs..." && \
	gcloud services enable compute.googleapis.com container.googleapis.com artifactregistry.googleapis.com cloudbuild.googleapis.com --project=$$PROJECT_ID && \
	echo "Ensuring VPC network exists..." && \
	(gcloud compute networks describe test-a2a-network --project $$PROJECT_ID >/dev/null 2>&1 || \
		(echo "Creating VPC network..." && \
		 gcloud compute networks create test-a2a-network --subnet-mode=custom --project=$$PROJECT_ID)) && \
	echo "Ensuring subnet exists..." && \
	(gcloud compute networks subnets describe test-a2a-subnet --region us-central1 --project $$PROJECT_ID >/dev/null 2>&1 || \
		(echo "Creating subnet in us-central1..." && \
		 gcloud compute networks subnets create test-a2a-subnet --network=test-a2a-network --region=us-central1 --range=10.0.0.0/20 --project=$$PROJECT_ID)) && \
	echo "Ensuring firewall rules exist..." && \
	(gcloud compute firewall-rules describe test-a2a-allow-internal --project $$PROJECT_ID >/dev/null 2>&1 || \
		(echo "Creating internal firewall rule..." && \
		 gcloud compute firewall-rules create test-a2a-allow-internal \
			--network=test-a2a-network \
			--allow=tcp,udp,icmp \
			--source-ranges=10.0.0.0/8 \
			--project=$$PROJECT_ID)) && \
	echo "Ensuring GKE cluster exists..." && \
	(gcloud container clusters describe test-a2a-dev --region us-central1 --project $$PROJECT_ID >/dev/null 2>&1 || \
		(echo "Creating GKE Autopilot cluster (this may take a few minutes)..." && \
		 gcloud container clusters create-auto test-a2a-dev --region us-central1 --project $$PROJECT_ID --network=test-a2a-network --subnetwork=test-a2a-subnet)) && \
	echo "Configuring kubectl credentials..." && \
	gcloud container clusters get-credentials test-a2a-dev --region us-central1 --project $$PROJECT_ID && \
	IMAGE_TAG=$${IMAGE_TAG:-$$(date +%Y%m%d%H%M%S)} && \
	IMAGE=us-central1-docker.pkg.dev/$$PROJECT_ID/test-a2a/test-a2a:$$IMAGE_TAG && \
	echo "Ensuring Artifact Registry repository exists..." && \
	(gcloud artifacts repositories create test-a2a \
		--repository-format=docker \
		--location=us-central1 \
		--project=$$PROJECT_ID 2>/dev/null || true) && \
	echo "Building and pushing Docker image..." && \
	gcloud builds submit --tag $$IMAGE && \
	echo "Applying Kubernetes manifests..." && \
	kubectl create namespace test-a2a --dry-run=client -o yaml | kubectl apply -f - && \
	kubectl apply -f k8s/service.yaml -f k8s/serviceaccount.yaml -f k8s/hpa.yaml -f k8s/pdb.yaml && \
	echo "Setting up Workload Identity..." && \
	SA_EMAIL=test-a2a-app@$$PROJECT_ID.iam.gserviceaccount.com && \
	(gcloud iam service-accounts describe $$SA_EMAIL --project=$$PROJECT_ID >/dev/null 2>&1 || \
		gcloud iam service-accounts create test-a2a-app \
			--display-name="test-a2a Agent Service Account" \
			--project=$$PROJECT_ID) && \
	for ROLE in roles/aiplatform.user roles/logging.logWriter roles/cloudtrace.agent roles/storage.admin roles/serviceusage.serviceUsageConsumer roles/discoveryengine.editor; do \
		gcloud projects add-iam-policy-binding $$PROJECT_ID \
			--member="serviceAccount:$$SA_EMAIL" \
			--role="$$ROLE" --quiet --no-user-output-enabled; \
	done && \
	gcloud iam service-accounts add-iam-policy-binding $$SA_EMAIL \
		--role="roles/iam.workloadIdentityUser" \
		--member="serviceAccount:$$PROJECT_ID.svc.id.goog[test-a2a/test-a2a]" \
		--project=$$PROJECT_ID --quiet --no-user-output-enabled && \
	kubectl annotate serviceaccount test-a2a \
		iam.gke.io/gcp-service-account=$$SA_EMAIL \
		-n test-a2a --overwrite && \
	echo "Deploying container image..." && \
	sed 's|image: PLACEHOLDER|image: '"$$IMAGE"'|' k8s/deployment.yaml | kubectl apply -f - && \
	echo "Waiting for rollout to complete..." && \
	kubectl rollout status deployment/test-a2a -n test-a2a && \
	echo "" && \
	echo "Waiting for external IP..." && \
	for i in $$(seq 1 12); do \
		EXTERNAL_IP=$$(kubectl get svc test-a2a -n test-a2a -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null); \
		[ -n "$$EXTERNAL_IP" ] && break; \
		sleep 5; \
	done && \
	if [ -n "$$EXTERNAL_IP" ]; then \
		kubectl set env deployment/test-a2a \
			APP_URL=http://$$EXTERNAL_IP:8080 \
			-n test-a2a && \
		echo ""; \
		echo "==============================================================================="; \
		echo "  Service URL: http://$$EXTERNAL_IP:8080"; \
		echo "==============================================================================="; \
	else \
		echo "External IP is still being provisioned. Check with:"; \
		echo "  kubectl get svc test-a2a -n test-a2a"; \
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

# ==============================================================================
# Agent Evaluation
# ==============================================================================

# Run agent evaluation using ADK eval
# Usage: make eval [EVALSET=tests/eval/evalsets/basic.evalset.json] [EVAL_CONFIG=tests/eval/eval_config.json]
eval:
	@echo "==============================================================================="
	@echo "| Running Agent Evaluation                                                    |"
	@echo "==============================================================================="
	uv sync --dev --extra eval
	uv run adk eval ./test_a2a $${EVALSET:-tests/eval/evalsets/basic.evalset.json} \
		$(if $(EVAL_CONFIG),--config_file_path=$(EVAL_CONFIG),$(if $(wildcard tests/eval/eval_config.json),--config_file_path=tests/eval/eval_config.json,))

# Run evaluation with all evalsets
eval-all:
	@echo "==============================================================================="
	@echo "| Running All Evalsets                                                        |"
	@echo "==============================================================================="
	@for evalset in tests/eval/evalsets/*.evalset.json; do \
		echo ""; \
		echo "▶ Running: $$evalset"; \
		$(MAKE) eval EVALSET=$$evalset || exit 1; \
	done
	@echo ""
	@echo "✅ All evalsets completed"

# Run code quality checks (codespell, ruff, ty)
lint:
	uv sync --dev --extra lint
	uv run codespell
	uv run ruff check . --diff
	uv run ruff format . --check --diff
	uv run ty check .

# ==============================================================================
# Gemini Enterprise Integration
# ==============================================================================

# Register the deployed agent to Gemini Enterprise
# Usage: make register-gemini-enterprise (interactive - will prompt for required details)
# For non-interactive use, set env vars: ID or GEMINI_ENTERPRISE_APP_ID (full GE resource name)
# Optional env vars: GEMINI_DISPLAY_NAME, GEMINI_DESCRIPTION, AGENT_CARD_URL
register-gemini-enterprise:
	@PROJECT_ID=$$(gcloud config get-value project 2>/dev/null) && \
	PROJECT_NUMBER=$$(gcloud projects describe $$PROJECT_ID --format="value(projectNumber)" 2>/dev/null) && \
	EXTERNAL_IP=$$(kubectl get svc test-a2a -n test-a2a -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null) && \
	uvx agent-starter-pack@0.20.0 register-gemini-enterprise \
		--agent-card-url="http://$$EXTERNAL_IP:8080/a2a/test_a2a/.well-known/agent-card.json" \
		--deployment-target="gke" \
		--project-number="$$PROJECT_NUMBER"
