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
# ==============================================================================
# Installation & Setup
# ==============================================================================

# Download Go module dependencies and generate go.sum
install:
	go mod tidy

# ==============================================================================
# Playground Targets
# ==============================================================================

# Launch local dev playground with web UI
playground:
	@echo "==============================================================================="
	@echo "| Starting your agent playground...                                           |"
	@echo "|                                                                             |"
	@echo "| Open: http://localhost:8501/ui/                                             |"
	@echo "| Try asking: What's the weather in San Francisco?                            |"
	@echo "==============================================================================="
	go run . web --port 8501 api webui -api_server_address http://localhost:8501/api

# ==============================================================================
# Local Development Commands
# ==============================================================================

# Launch local development server with API and A2A support (matches Cloud Run)
# API endpoints: /api/run_sse, /api/apps/...
# A2A endpoint: /a2a/invoke (JSON-RPC)
# Agent card: /.well-known/agent-card.json
local-backend:
	go run . web --port 8000 api a2a

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
	echo "Enabling required APIs..." && \
	gcloud services enable compute.googleapis.com container.googleapis.com artifactregistry.googleapis.com cloudbuild.googleapis.com --project=$$PROJECT_ID && \
	echo "Ensuring VPC network exists..." && \
	(gcloud compute networks describe test-go-agent-network --project $$PROJECT_ID >/dev/null 2>&1 || \
		(echo "Creating VPC network..." && \
		 gcloud compute networks create test-go-agent-network --subnet-mode=custom --project=$$PROJECT_ID)) && \
	echo "Ensuring subnet exists..." && \
	(gcloud compute networks subnets describe test-go-agent-subnet --region us-central1 --project $$PROJECT_ID >/dev/null 2>&1 || \
		(echo "Creating subnet in us-central1..." && \
		 gcloud compute networks subnets create test-go-agent-subnet --network=test-go-agent-network --region=us-central1 --range=10.0.0.0/20 --project=$$PROJECT_ID)) && \
	echo "Ensuring firewall rules exist..." && \
	(gcloud compute firewall-rules describe test-go-agent-allow-internal --project $$PROJECT_ID >/dev/null 2>&1 || \
		(echo "Creating internal firewall rule..." && \
		 gcloud compute firewall-rules create test-go-agent-allow-internal \
			--network=test-go-agent-network \
			--allow=tcp,udp,icmp \
			--source-ranges=10.0.0.0/8 \
			--project=$$PROJECT_ID)) && \
	echo "Ensuring GKE cluster exists..." && \
	(gcloud container clusters describe test-go-agent-dev --region us-central1 --project $$PROJECT_ID >/dev/null 2>&1 || \
		(echo "Creating GKE Autopilot cluster (this may take a few minutes)..." && \
		 gcloud container clusters create-auto test-go-agent-dev --region us-central1 --project $$PROJECT_ID --network=test-go-agent-network --subnetwork=test-go-agent-subnet)) && \
	echo "Configuring kubectl credentials..." && \
	gcloud container clusters get-credentials test-go-agent-dev --region us-central1 --project $$PROJECT_ID && \
	IMAGE_TAG=$${IMAGE_TAG:-$$(date +%Y%m%d%H%M%S)} && \
	IMAGE=us-central1-docker.pkg.dev/$$PROJECT_ID/test-go-agent/test-go-agent:$$IMAGE_TAG && \
	echo "Ensuring Artifact Registry repository exists..." && \
	(gcloud artifacts repositories create test-go-agent \
		--repository-format=docker \
		--location=us-central1 \
		--project=$$PROJECT_ID 2>/dev/null || true) && \
	echo "Building and pushing Docker image..." && \
	gcloud builds submit --tag $$IMAGE && \
	echo "Applying Kubernetes manifests..." && \
	kubectl create namespace test-go-agent --dry-run=client -o yaml | kubectl apply -f - && \
	kubectl apply -f k8s/service.yaml -f k8s/serviceaccount.yaml -f k8s/hpa.yaml -f k8s/pdb.yaml && \
	echo "Setting up Workload Identity..." && \
	SA_EMAIL=test-go-agent-app@$$PROJECT_ID.iam.gserviceaccount.com && \
	(gcloud iam service-accounts describe $$SA_EMAIL --project=$$PROJECT_ID >/dev/null 2>&1 || \
		gcloud iam service-accounts create test-go-agent-app \
			--display-name="test-go-agent Agent Service Account" \
			--project=$$PROJECT_ID) && \
	for ROLE in roles/aiplatform.user roles/logging.logWriter roles/cloudtrace.agent roles/storage.admin roles/serviceusage.serviceUsageConsumer roles/discoveryengine.editor; do \
		gcloud projects add-iam-policy-binding $$PROJECT_ID \
			--member="serviceAccount:$$SA_EMAIL" \
			--role="$$ROLE" --quiet --no-user-output-enabled; \
	done && \
	gcloud iam service-accounts add-iam-policy-binding $$SA_EMAIL \
		--role="roles/iam.workloadIdentityUser" \
		--member="serviceAccount:$$PROJECT_ID.svc.id.goog[test-go-agent/test-go-agent]" \
		--project=$$PROJECT_ID --quiet --no-user-output-enabled && \
	kubectl annotate serviceaccount test-go-agent \
		iam.gke.io/gcp-service-account=$$SA_EMAIL \
		-n test-go-agent --overwrite && \
	echo "Deploying container image..." && \
	sed 's|image: PLACEHOLDER|image: '"$$IMAGE"'|' k8s/deployment.yaml | kubectl apply -f - && \
	echo "Waiting for rollout to complete..." && \
	kubectl rollout status deployment/test-go-agent -n test-go-agent && \
	echo "" && \
	echo "Waiting for external IP..." && \
	for i in $$(seq 1 12); do \
		EXTERNAL_IP=$$(kubectl get svc test-go-agent -n test-go-agent -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null); \
		[ -n "$$EXTERNAL_IP" ] && break; \
		sleep 5; \
	done && \
	if [ -n "$$EXTERNAL_IP" ]; then \
		kubectl set env deployment/test-go-agent \
			APP_URL=http://$$EXTERNAL_IP:8080 \
			-n test-go-agent && \
		echo ""; \
		echo "==============================================================================="; \
		echo "  Service URL: http://$$EXTERNAL_IP:8080"; \
		echo "==============================================================================="; \
	else \
		echo "External IP is still being provisioned. Check with:"; \
		echo "  kubectl get svc test-go-agent -n test-go-agent"; \
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
	go test -v ./agent/... ./e2e/...

# Run load tests (requires server running on port 8000)
# Server auto-loads .env on startup
# Usage: make load-test [DURATION=30s] [USERS=10] [RAMP=2]
load-test:
	_STAGING_URL=http://127.0.0.1:8000 go test -v -tags=load -timeout=5m ./e2e/load_test/... \
		-duration=$(or $(DURATION),30s) \
		-users=$(or $(USERS),10) \
		-ramp=$(or $(RAMP),2)

# Run code quality checks
lint:
	@command -v golangci-lint >/dev/null 2>&1 || { \
		echo "golangci-lint not found, installing..."; \
		go install github.com/golangci/golangci-lint/cmd/golangci-lint@latest; \
	}
	$$(go env GOPATH)/bin/golangci-lint run

# ==============================================================================
# Go-specific targets
# ==============================================================================

# Format Go code
fmt:
	go fmt ./...

# Build the binary
build:
	go build -o bin/agent .

# Clean build artifacts
clean:
	rm -rf bin/

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
	@echo "|    http://localhost:8000/.well-known/agent-card.json                        |"
	@echo "|                                                                             |"
	@echo "| Testing Remote Deployment:                                                  |"
	@echo "|    1. Run: gcloud run services describe test-go-agent --region us-central1 |"
	@echo "|    2. Copy the URL and append: /.well-known/agent-card.json                 |"
	@echo "|                                                                             |"
	@echo "==============================================================================="
	@echo ""
	cd tools/a2a-inspector/backend && uv run app.py

# Internal: Setup inspector if not already present (runs once)
setup-inspector-if-needed:
	@if [ ! -d "tools/a2a-inspector" ]; then \
		echo "" && \
		echo "First-time setup: Installing A2A Inspector..." && \
		echo "" && \
		mkdir -p tools && \
		git clone --quiet https://github.com/a2aproject/a2a-inspector.git tools/a2a-inspector && \
		(cd tools/a2a-inspector && git -c advice.detachedHead=false checkout --quiet 893e4062f6fbd85a8369228ce862ebbf4a025694) && \
		echo "Installing Python dependencies..." && \
		(cd tools/a2a-inspector && uv sync --quiet) && \
		echo "Installing Node.js dependencies..." && \
		(cd tools/a2a-inspector/frontend && npm install --silent) && \
		echo "Building frontend..." && \
		(cd tools/a2a-inspector/frontend && npm run build --silent) && \
		echo "" && \
		echo "A2A Inspector setup complete!" && \
		echo ""; \
	fi

# Internal: Build inspector frontend if needed
build-inspector-if-needed:
	@if [ -d "tools/a2a-inspector" ] && [ ! -f "tools/a2a-inspector/frontend/public/script.js" ]; then \
		echo "Building inspector frontend..."; \
		cd tools/a2a-inspector/frontend && npm run build; \
	fi

# ==============================================================================
# Gemini Enterprise Registration
# ==============================================================================

# Register agent with Gemini Enterprise for A2A discovery
# Usage: make register-gemini-enterprise (interactive - will prompt for required details)
# For non-interactive use, set env vars: ID or GEMINI_ENTERPRISE_APP_ID (full GE resource name)
# Optional env vars: GEMINI_DISPLAY_NAME, GEMINI_DESCRIPTION, AGENT_CARD_URL
register-gemini-enterprise:
	@PROJECT_ID=$$(gcloud config get-value project 2>/dev/null) && \
	PROJECT_NUMBER=$$(gcloud projects describe $$PROJECT_ID --format="value(projectNumber)" 2>/dev/null) && \
	EXTERNAL_IP=$$(kubectl get svc test-go-agent -n test-go-agent -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null) && \
	uvx agent-starter-pack@0.20.0 register-gemini-enterprise \
		--agent-card-url="http://$$EXTERNAL_IP:8080/.well-known/agent-card.json" \
		--deployment-target="gke" \
		--project-number="$$PROJECT_NUMBER"
