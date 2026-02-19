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
	echo "Enabling required APIs..." && \
	gcloud services enable compute.googleapis.com container.googleapis.com artifactregistry.googleapis.com cloudbuild.googleapis.com --project=$$PROJECT_ID && \
	echo "Ensuring VPC network exists..." && \
	(gcloud compute networks describe {{cookiecutter.project_name}}-network --project $$PROJECT_ID >/dev/null 2>&1 || \
		(echo "Creating VPC network..." && \
		 gcloud compute networks create {{cookiecutter.project_name}}-network --subnet-mode=custom --project=$$PROJECT_ID)) && \
	echo "Ensuring subnet exists..." && \
	(gcloud compute networks subnets describe {{cookiecutter.project_name}}-subnet --region us-central1 --project $$PROJECT_ID >/dev/null 2>&1 || \
		(echo "Creating subnet in us-central1..." && \
		 gcloud compute networks subnets create {{cookiecutter.project_name}}-subnet --network={{cookiecutter.project_name}}-network --region=us-central1 --range=10.0.0.0/20 --project=$$PROJECT_ID)) && \
	echo "Ensuring firewall rules exist..." && \
	(gcloud compute firewall-rules describe {{cookiecutter.project_name}}-allow-internal --project $$PROJECT_ID >/dev/null 2>&1 || \
		(echo "Creating internal firewall rule..." && \
		 gcloud compute firewall-rules create {{cookiecutter.project_name}}-allow-internal \
			--network={{cookiecutter.project_name}}-network \
			--allow=tcp,udp,icmp \
			--source-ranges=10.0.0.0/8 \
			--project=$$PROJECT_ID)) && \
	echo "Ensuring GKE cluster exists..." && \
	(gcloud container clusters describe {{cookiecutter.project_name}}-dev --region us-central1 --project $$PROJECT_ID >/dev/null 2>&1 || \
		(echo "Creating GKE Autopilot cluster (this may take a few minutes)..." && \
		 gcloud container clusters create-auto {{cookiecutter.project_name}}-dev --region us-central1 --project $$PROJECT_ID --network={{cookiecutter.project_name}}-network --subnetwork={{cookiecutter.project_name}}-subnet)) && \
	echo "Configuring kubectl credentials..." && \
	gcloud container clusters get-credentials {{cookiecutter.project_name}}-dev --region us-central1 --project $$PROJECT_ID && \
	IMAGE_TAG=$${IMAGE_TAG:-$$(date +%Y%m%d%H%M%S)} && \
	IMAGE=us-central1-docker.pkg.dev/$$PROJECT_ID/{{cookiecutter.project_name}}/{{cookiecutter.project_name}}:$$IMAGE_TAG && \
	echo "Ensuring Artifact Registry repository exists..." && \
	(gcloud artifacts repositories create {{cookiecutter.project_name}} \
		--repository-format=docker \
		--location=us-central1 \
		--project=$$PROJECT_ID 2>/dev/null || true) && \
	echo "Building and pushing Docker image..." && \
	gcloud builds submit --tag $$IMAGE && \
	echo "Applying Kubernetes manifests..." && \
	kubectl create namespace {{cookiecutter.project_name}} --dry-run=client -o yaml | kubectl apply -f - && \
	kubectl apply -f k8s/service.yaml -f k8s/serviceaccount.yaml -f k8s/hpa.yaml -f k8s/pdb.yaml && \
	echo "Setting up Workload Identity..." && \
	SA_EMAIL={{cookiecutter.project_name}}-app@$$PROJECT_ID.iam.gserviceaccount.com && \
	(gcloud iam service-accounts describe $$SA_EMAIL --project=$$PROJECT_ID >/dev/null 2>&1 || \
		gcloud iam service-accounts create {{cookiecutter.project_name}}-app \
			--display-name="{{cookiecutter.project_name}} Agent Service Account" \
			--project=$$PROJECT_ID) && \
	for ROLE in roles/aiplatform.user roles/logging.logWriter roles/cloudtrace.agent roles/storage.admin roles/serviceusage.serviceUsageConsumer roles/discoveryengine.editor; do \
		gcloud projects add-iam-policy-binding $$PROJECT_ID \
			--member="serviceAccount:$$SA_EMAIL" \
			--role="$$ROLE" --quiet --no-user-output-enabled; \
	done && \
	gcloud iam service-accounts add-iam-policy-binding $$SA_EMAIL \
		--role="roles/iam.workloadIdentityUser" \
		--member="serviceAccount:$$PROJECT_ID.svc.id.goog[{{cookiecutter.project_name}}/{{cookiecutter.project_name}}]" \
		--project=$$PROJECT_ID --quiet --no-user-output-enabled && \
	kubectl annotate serviceaccount {{cookiecutter.project_name}} \
		iam.gke.io/gcp-service-account=$$SA_EMAIL \
		-n {{cookiecutter.project_name}} --overwrite && \
	echo "Deploying container image..." && \
	sed 's|image: PLACEHOLDER|image: '"$$IMAGE"'|' k8s/deployment.yaml | kubectl apply -f - && \
	echo "Waiting for rollout to complete..." && \
	kubectl rollout status deployment/{{cookiecutter.project_name}} -n {{cookiecutter.project_name}} && \
	echo "" && \
	echo "Waiting for external IP..." && \
	for i in $$(seq 1 12); do \
		EXTERNAL_IP=$$(kubectl get svc {{cookiecutter.project_name}} -n {{cookiecutter.project_name}} -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null); \
		[ -n "$$EXTERNAL_IP" ] && break; \
		sleep 5; \
	done && \
	if [ -n "$$EXTERNAL_IP" ]; then \
		kubectl set env deployment/{{cookiecutter.project_name}} \
			APP_URL=http://$$EXTERNAL_IP:8080 \
			-n {{cookiecutter.project_name}} && \
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
