
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
	@echo "| 🔍 IMPORTANT: Select the 'test_adk' folder to interact with your agent.          |"
	@echo "==============================================================================="
	uv run adk web . --port 8501 --reload_agents

# ==============================================================================
# Local Development Commands
# ==============================================================================

# Launch local development server with hot-reload
# Usage: make local-backend [PORT=8000] - Specify PORT for parallel scenario testing
local-backend:
	uv run uvicorn test_adk.fast_api_app:app --host localhost --port $(or $(PORT),8000) --reload

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
	(gcloud compute networks describe test-adk-base-network --project $$PROJECT_ID >/dev/null 2>&1 || \
		(echo "Creating VPC network..." && \
		 gcloud compute networks create test-adk-base-network --subnet-mode=custom --project=$$PROJECT_ID)) && \
	echo "Ensuring subnet exists..." && \
	(gcloud compute networks subnets describe test-adk-base-subnet --region us-central1 --project $$PROJECT_ID >/dev/null 2>&1 || \
		(echo "Creating subnet in us-central1..." && \
		 gcloud compute networks subnets create test-adk-base-subnet --network=test-adk-base-network --region=us-central1 --range=10.0.0.0/20 --project=$$PROJECT_ID)) && \
	echo "Ensuring firewall rules exist..." && \
	(gcloud compute firewall-rules describe test-adk-base-allow-internal --project $$PROJECT_ID >/dev/null 2>&1 || \
		(echo "Creating internal firewall rule..." && \
		 gcloud compute firewall-rules create test-adk-base-allow-internal \
			--network=test-adk-base-network \
			--allow=tcp,udp,icmp \
			--source-ranges=10.0.0.0/8 \
			--project=$$PROJECT_ID)) && \
	echo "Ensuring GKE cluster exists..." && \
	(gcloud container clusters describe test-adk-base-dev --region us-central1 --project $$PROJECT_ID >/dev/null 2>&1 || \
		(echo "Creating GKE Autopilot cluster (this may take a few minutes)..." && \
		 gcloud container clusters create-auto test-adk-base-dev --region us-central1 --project $$PROJECT_ID --network=test-adk-base-network --subnetwork=test-adk-base-subnet)) && \
	echo "Configuring kubectl credentials..." && \
	gcloud container clusters get-credentials test-adk-base-dev --region us-central1 --project $$PROJECT_ID && \
	IMAGE_TAG=$${IMAGE_TAG:-$$(date +%Y%m%d%H%M%S)} && \
	IMAGE=us-central1-docker.pkg.dev/$$PROJECT_ID/test-adk-base/test-adk-base:$$IMAGE_TAG && \
	echo "Ensuring Artifact Registry repository exists..." && \
	(gcloud artifacts repositories create test-adk-base \
		--repository-format=docker \
		--location=us-central1 \
		--project=$$PROJECT_ID 2>/dev/null || true) && \
	echo "Building and pushing Docker image..." && \
	gcloud builds submit --tag $$IMAGE && \
	echo "Applying Kubernetes manifests..." && \
	kubectl create namespace test-adk-base --dry-run=client -o yaml | kubectl apply -f - && \
	kubectl apply -f k8s/service.yaml -f k8s/serviceaccount.yaml -f k8s/hpa.yaml -f k8s/pdb.yaml && \
	echo "Setting up Workload Identity..." && \
	SA_EMAIL=test-adk-base-app@$$PROJECT_ID.iam.gserviceaccount.com && \
	(gcloud iam service-accounts describe $$SA_EMAIL --project=$$PROJECT_ID >/dev/null 2>&1 || \
		gcloud iam service-accounts create test-adk-base-app \
			--display-name="test-adk-base Agent Service Account" \
			--project=$$PROJECT_ID) && \
	for ROLE in roles/aiplatform.user roles/logging.logWriter roles/cloudtrace.agent roles/storage.admin roles/serviceusage.serviceUsageConsumer roles/discoveryengine.editor; do \
		gcloud projects add-iam-policy-binding $$PROJECT_ID \
			--member="serviceAccount:$$SA_EMAIL" \
			--role="$$ROLE" --quiet --no-user-output-enabled; \
	done && \
	gcloud iam service-accounts add-iam-policy-binding $$SA_EMAIL \
		--role="roles/iam.workloadIdentityUser" \
		--member="serviceAccount:$$PROJECT_ID.svc.id.goog[test-adk-base/test-adk-base]" \
		--project=$$PROJECT_ID --quiet --no-user-output-enabled && \
	kubectl annotate serviceaccount test-adk-base \
		iam.gke.io/gcp-service-account=$$SA_EMAIL \
		-n test-adk-base --overwrite && \
	echo "Deploying container image..." && \
	sed 's|image: PLACEHOLDER|image: '"$$IMAGE"'|' k8s/deployment.yaml | kubectl apply -f - && \
	echo "Waiting for rollout to complete..." && \
	kubectl rollout status deployment/test-adk-base -n test-adk-base && \
	echo "" && \
	echo "Waiting for external IP..." && \
	for i in $$(seq 1 12); do \
		EXTERNAL_IP=$$(kubectl get svc test-adk-base -n test-adk-base -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null); \
		[ -n "$$EXTERNAL_IP" ] && break; \
		sleep 5; \
	done && \
	if [ -n "$$EXTERNAL_IP" ]; then \
		kubectl set env deployment/test-adk-base \
			APP_URL=http://$$EXTERNAL_IP:8080 \
			-n test-adk-base && \
		echo ""; \
		echo "==============================================================================="; \
		echo "  Service URL: http://$$EXTERNAL_IP:8080"; \
		echo "==============================================================================="; \
	else \
		echo "External IP is still being provisioned. Check with:"; \
		echo "  kubectl get svc test-adk-base -n test-adk-base"; \
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
	uv run adk eval ./test_adk $${EVALSET:-tests/eval/evalsets/basic.evalset.json} \
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
