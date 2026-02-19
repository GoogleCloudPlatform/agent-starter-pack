
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
	echo "Enabling required APIs..." && \
	gcloud services enable compute.googleapis.com container.googleapis.com artifactregistry.googleapis.com cloudbuild.googleapis.com --project=$$PROJECT_ID && \
	echo "Ensuring VPC network exists..." && \
	(gcloud compute networks describe test-adk-live-network --project $$PROJECT_ID >/dev/null 2>&1 || \
		(echo "Creating VPC network..." && \
		 gcloud compute networks create test-adk-live-network --subnet-mode=custom --project=$$PROJECT_ID)) && \
	echo "Ensuring subnet exists..." && \
	(gcloud compute networks subnets describe test-adk-live-subnet --region us-central1 --project $$PROJECT_ID >/dev/null 2>&1 || \
		(echo "Creating subnet in us-central1..." && \
		 gcloud compute networks subnets create test-adk-live-subnet --network=test-adk-live-network --region=us-central1 --range=10.0.0.0/20 --project=$$PROJECT_ID)) && \
	echo "Ensuring firewall rules exist..." && \
	(gcloud compute firewall-rules describe test-adk-live-allow-internal --project $$PROJECT_ID >/dev/null 2>&1 || \
		(echo "Creating internal firewall rule..." && \
		 gcloud compute firewall-rules create test-adk-live-allow-internal \
			--network=test-adk-live-network \
			--allow=tcp,udp,icmp \
			--source-ranges=10.0.0.0/8 \
			--project=$$PROJECT_ID)) && \
	echo "Ensuring GKE cluster exists..." && \
	(gcloud container clusters describe test-adk-live-dev --region us-central1 --project $$PROJECT_ID >/dev/null 2>&1 || \
		(echo "Creating GKE Autopilot cluster (this may take a few minutes)..." && \
		 gcloud container clusters create-auto test-adk-live-dev --region us-central1 --project $$PROJECT_ID --network=test-adk-live-network --subnetwork=test-adk-live-subnet)) && \
	echo "Configuring kubectl credentials..." && \
	gcloud container clusters get-credentials test-adk-live-dev --region us-central1 --project $$PROJECT_ID && \
	IMAGE_TAG=$${IMAGE_TAG:-$$(date +%Y%m%d%H%M%S)} && \
	IMAGE=us-central1-docker.pkg.dev/$$PROJECT_ID/test-adk-live/test-adk-live:$$IMAGE_TAG && \
	echo "Ensuring Artifact Registry repository exists..." && \
	(gcloud artifacts repositories create test-adk-live \
		--repository-format=docker \
		--location=us-central1 \
		--project=$$PROJECT_ID 2>/dev/null || true) && \
	echo "Building and pushing Docker image..." && \
	gcloud builds submit --tag $$IMAGE && \
	echo "Applying Kubernetes manifests..." && \
	kubectl create namespace test-adk-live --dry-run=client -o yaml | kubectl apply -f - && \
	kubectl apply -f k8s/service.yaml -f k8s/serviceaccount.yaml -f k8s/hpa.yaml -f k8s/pdb.yaml && \
	echo "Setting up Workload Identity..." && \
	SA_EMAIL=test-adk-live-app@$$PROJECT_ID.iam.gserviceaccount.com && \
	(gcloud iam service-accounts describe $$SA_EMAIL --project=$$PROJECT_ID >/dev/null 2>&1 || \
		gcloud iam service-accounts create test-adk-live-app \
			--display-name="test-adk-live Agent Service Account" \
			--project=$$PROJECT_ID) && \
	for ROLE in roles/aiplatform.user roles/logging.logWriter roles/cloudtrace.agent roles/storage.admin roles/serviceusage.serviceUsageConsumer roles/discoveryengine.editor; do \
		gcloud projects add-iam-policy-binding $$PROJECT_ID \
			--member="serviceAccount:$$SA_EMAIL" \
			--role="$$ROLE" --quiet --no-user-output-enabled; \
	done && \
	gcloud iam service-accounts add-iam-policy-binding $$SA_EMAIL \
		--role="roles/iam.workloadIdentityUser" \
		--member="serviceAccount:$$PROJECT_ID.svc.id.goog[test-adk-live/test-adk-live]" \
		--project=$$PROJECT_ID --quiet --no-user-output-enabled && \
	kubectl annotate serviceaccount test-adk-live \
		iam.gke.io/gcp-service-account=$$SA_EMAIL \
		-n test-adk-live --overwrite && \
	echo "Deploying container image..." && \
	sed 's|image: PLACEHOLDER|image: '"$$IMAGE"'|' k8s/deployment.yaml | kubectl apply -f - && \
	echo "Waiting for rollout to complete..." && \
	kubectl rollout status deployment/test-adk-live -n test-adk-live && \
	echo "" && \
	echo "Waiting for external IP..." && \
	for i in $$(seq 1 12); do \
		EXTERNAL_IP=$$(kubectl get svc test-adk-live -n test-adk-live -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null); \
		[ -n "$$EXTERNAL_IP" ] && break; \
		sleep 5; \
	done && \
	if [ -n "$$EXTERNAL_IP" ]; then \
		kubectl set env deployment/test-adk-live \
			APP_URL=http://$$EXTERNAL_IP:8080 \
			-n test-adk-live && \
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
