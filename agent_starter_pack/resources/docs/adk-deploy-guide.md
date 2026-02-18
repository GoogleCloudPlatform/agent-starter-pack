# ADK Deployment Guide

This guide covers infrastructure setup, deployment workflows, CI/CD pipelines, secret management, and testing deployed ADK agents.

---

## Custom Infrastructure (Terraform)

**CRITICAL**: When your agent requires custom infrastructure (Cloud SQL, Pub/Sub topics, Eventarc triggers, BigQuery datasets, VPC connectors, etc.), you MUST define it in Terraform - never create resources manually via `gcloud` commands.

### Where to Put Custom Terraform

| Scenario | Location | When to Use |
|----------|----------|-------------|
| Dev-only infrastructure | `deployment/terraform/dev/` | Quick prototyping, single environment |
| CI/CD environments (staging/prod) | `deployment/terraform/` | Production deployments with staging/prod separation |

### Adding Custom Infrastructure

**For dev-only (Option A deployment):**

Create a new `.tf` file in `deployment/terraform/dev/`:

```hcl
# deployment/terraform/dev/custom_resources.tf

# Example: Pub/Sub topic for event processing
resource "google_pubsub_topic" "events" {
  name    = "${var.project_name}-events"
  project = var.dev_project_id
}

# Example: BigQuery dataset for analytics
resource "google_bigquery_dataset" "analytics" {
  dataset_id = "${replace(var.project_name, "-", "_")}_analytics"
  project    = var.dev_project_id
  location   = var.region
}

# Example: Eventarc trigger for Cloud Storage
resource "google_eventarc_trigger" "storage_trigger" {
  name     = "${var.project_name}-storage-trigger"
  location = var.region
  project  = var.dev_project_id

  matching_criteria {
    attribute = "type"
    value     = "google.cloud.storage.object.v1.finalized"
  }
  matching_criteria {
    attribute = "bucket"
    value     = google_storage_bucket.uploads.name
  }

  destination {
    cloud_run_service {
      service = google_cloud_run_v2_service.app.name
      region  = var.region
      path    = "/invoke"
    }
  }

  service_account = google_service_account.app_sa.email
}
```

**For CI/CD environments (Option B deployment):**

Add resources to `deployment/terraform/` (applies to staging and prod):

```hcl
# deployment/terraform/custom_resources.tf

# Resources here are created in BOTH staging and prod projects
# Use for_each with local.deploy_project_ids for multi-environment

resource "google_pubsub_topic" "events" {
  for_each = local.deploy_project_ids
  name     = "${var.project_name}-events"
  project  = each.value
}
```

### IAM for Custom Resources

When adding custom resources, ensure your app service account has the necessary permissions:

```hcl
# Add to deployment/terraform/dev/iam.tf or deployment/terraform/iam.tf

# Example: Grant Pub/Sub publisher permission
resource "google_pubsub_topic_iam_member" "app_publisher" {
  topic   = google_pubsub_topic.events.name
  project = var.dev_project_id
  role    = "roles/pubsub.publisher"
  member  = "serviceAccount:${google_service_account.app_sa.email}"
}

# Example: Grant BigQuery data editor
resource "google_bigquery_dataset_iam_member" "app_editor" {
  dataset_id = google_bigquery_dataset.analytics.dataset_id
  project    = var.dev_project_id
  role       = "roles/bigquery.dataEditor"
  member     = "serviceAccount:${google_service_account.app_sa.email}"
}
```

### Applying Custom Infrastructure

```bash
# For dev-only infrastructure
make setup-dev-env  # Runs terraform apply in deployment/terraform/dev/

# For CI/CD, infrastructure is applied automatically:
# - On setup-cicd: Terraform runs for staging and prod
# - On git push: CI/CD pipeline runs terraform plan/apply
```

### Common Patterns

**Cloud Storage trigger (Eventarc):**
- Create bucket in Terraform
- Create Eventarc trigger pointing to `/invoke` endpoint
- Grant `eventarc.eventReceiver` role to app service account

**Pub/Sub processing:**
- Create topic and push subscription in Terraform
- Point subscription to `/invoke` endpoint
- Grant `iam.serviceAccountTokenCreator` role for push auth

**BigQuery Remote Function:**
- Create BigQuery connection in Terraform
- Grant connection service account permission to invoke Cloud Run
- Create the remote function via SQL after deployment

**Cloud SQL sessions:**
- Already configured by ASP when using `--session-type cloud_sql`
- Additional tables/schemas can be added via migration scripts

---

## Secret Manager (for API credentials)

Instead of passing sensitive keys as environment variables (which can be logged or visible in console), use GCP Secret Manager.

### 1. Store secrets via gcloud

```bash
# Create the secret
echo -n "YOUR_API_KEY" | gcloud secrets create MY_SECRET_NAME --data-file=-

# Update an existing secret
echo -n "NEW_API_KEY" | gcloud secrets versions add MY_SECRET_NAME --data-file=-
```

### 2. Grant access (IAM)

The agent's service account needs the `Secret Manager Secret Accessor` role:
```bash
PROJECT_ID=$(gcloud config get-value project)
PROJECT_NUMBER=$(gcloud projects list --filter="project_id:$PROJECT_ID" --format="value(project_number)")
SA_EMAIL="service-$PROJECT_NUMBER@gcp-sa-aiplatform-re.iam.gserviceaccount.com"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SA_EMAIL" \
    --role="roles/secretmanager.secretAccessor"
```

### 3. Use secrets in deployment

**Agent Engine:**

Pass secrets during deployment with `--set-secrets`. Note: `make deploy` doesn't support secrets, so run deploy.py directly:
```bash
uv run python -m <your-agent-directory>.app_utils.deploy --set-secrets "API_KEY=my-api-key,DB_PASS=db-password:2"
```

Format: `ENV_VAR=SECRET_ID` or `ENV_VAR=SECRET_ID:VERSION` (defaults to latest).

In your agent code, access via `os.environ`:
```python
import os
import json

api_key = os.environ.get("API_KEY")
# For JSON secrets:
db_creds = json.loads(os.environ.get("DB_PASS", "{}"))
```

**Cloud Run:**

Mount secrets as environment variables in Cloud Run:
```bash
gcloud run deploy SERVICE_NAME \
    --set-secrets="API_KEY=my-api-key:latest,DB_PASS=db-password:2"
```

In your agent code, access via `os.environ`:
```python
import os
api_key = os.environ.get("API_KEY")
```

Alternatively, pull secrets at runtime:
```python
from google.cloud import secretmanager
import google.auth

def get_secret(secret_id: str) -> str:
    """Retrieves the latest version of a secret from Secret Manager."""
    _, project_id = google.auth.default()
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{project_id}/secrets/{secret_id}/versions/latest"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("UTF-8")

API_KEY = get_secret("MY_SECRET_NAME")
```

---

## Pre-Deployment Tests

Once evaluation thresholds are met, run tests before deployment:

```bash
make test
```

If tests fail, fix issues and run again until all tests pass.

---

## Deploy to Dev Environment

Deploy to the development environment for final testing:

1. **Notify the human**: "Eval scores meet thresholds and tests pass. Ready to deploy to dev?"
2. **Wait for explicit approval**
3. Once approved: `make deploy`

This deploys to the dev GCP project for live testing.

**IMPORTANT**: Never run `make deploy` without explicit human approval.

### Deployment Timeouts

Agent Engine deployments can take 5-10 minutes. If `make deploy` times out:

1. Check if deployment succeeded:
```python
import vertexai
client = vertexai.Client(location="us-central1")
for engine in client.agent_engines.list():
    print(engine.name, engine.display_name)
```

2. If the engine exists, update `deployment_metadata.json` with the engine ID.

---

## Production Deployment - Choose Your Path

After validating in dev, **ask the user** which deployment approach they prefer:

### Option A: Simple Single-Project Deployment (Recommended for getting started)

**Best for:**
- Personal projects or prototypes
- Teams without complex CI/CD requirements
- Quick deployments to a single environment

**Steps:**
1. Set up infrastructure: `make setup-dev-env`
2. Deploy: `make deploy`

**Pros:**
- Simpler setup, faster to get running
- Single GCP project to manage
- Direct control over deployments

**Cons:**
- No automated staging/prod pipeline
- Manual deployments each time
- No automated testing on push

### Option B: Full CI/CD Pipeline (Recommended for production)

**Best for:**
- Production applications
- Teams requiring staging -> production promotion
- Automated testing and deployment workflows

**Prerequisites:**
1. Project must NOT be in a gitignored folder
2. User must provide staging and production GCP project IDs
3. GitHub repository name and owner

Note: `setup-cicd` automatically initializes git if needed.

**Steps:**
1. If prototype, first add Terraform/CI-CD files:
   ```bash
   # Programmatic invocation (requires --cicd-runner with -y to skip prompts)
   uvx agent-starter-pack enhance . \
     --cicd-runner github_actions \
     -y -s
   ```
   Or use the equivalent MCP tool call (`enhance_project`) if available.

2. Ensure you're logged in to GitHub CLI:
   ```bash
   gh auth login  # (skip if already authenticated)
   ```

3. Run setup-cicd with your GCP project IDs (no PAT needed - uses gh auth):
   ```bash
   uvx agent-starter-pack setup-cicd \
     --staging-project YOUR_STAGING_PROJECT \
     --prod-project YOUR_PROD_PROJECT \
     --repository-name YOUR_REPO_NAME \
     --repository-owner YOUR_GITHUB_USERNAME \
     --auto-approve \
     --create-repository
   ```
   Note: The CI/CD runner type is auto-detected from Terraform files created by `enhance`.

4. This creates infrastructure in BOTH staging and production projects
5. Sets up GitHub Actions triggers
6. Push code to trigger deployments

**Pros:**
- Automated testing on every push
- Safe staging -> production promotion
- Audit trail and approval workflows

**Cons:**
- Requires 2-3 GCP projects (staging, prod, optionally cicd)
- More initial setup time
- Requires GitHub repository

### Choosing a CI/CD Runner

| Runner | Pros | Cons |
|--------|------|------|
| **github_actions** (Default) | No PAT needed, uses `gh auth`, WIF-based, fully automated | Requires GitHub CLI authentication |
| **google_cloud_build** | Native GCP integration | Requires interactive browser authorization (or PAT + app installation ID for programmatic mode) |

**How authentication works:**
- **github_actions**: The Terraform GitHub provider automatically uses your `gh auth` credentials. No separate PAT export needed.
- **google_cloud_build**: Interactive mode uses browser auth. Programmatic mode requires `--github-pat` and `--github-app-installation-id`.

---

## After CI/CD Setup: Activating the Pipeline

**IMPORTANT**: `setup-cicd` creates infrastructure but doesn't deploy the agent automatically.

Terraform automatically configures all required GitHub secrets and variables (WIF credentials, project IDs, service accounts, etc.). No manual configuration needed.

### Step 1: Commit and Push

```bash
git add . && git commit -m "Initial agent implementation"
git push origin main
```

### Step 2: Monitor Deployment

- **GitHub Actions**: Check the Actions tab in your repository
- **Cloud Build**: `gcloud builds list --project=YOUR_CICD_PROJECT --region=YOUR_REGION`

**Staging deployment** happens automatically on push to main.
**Production deployment** requires manual approval:

```bash
# GitHub Actions (recommended): Approve via repository Actions tab
# Production deploys are gated by environment protection rules

# Cloud Build: Find pending build and approve
gcloud builds list --project=PROD_PROJECT --region=REGION --filter="status=PENDING"
gcloud builds approve BUILD_ID --project=PROD_PROJECT
```

---

## Troubleshooting CI/CD

| Issue | Solution |
|-------|----------|
| Terraform state locked | `terraform force-unlock LOCK_ID` in deployment/terraform/ |
| Cloud Build authorization pending | Use `github_actions` runner instead |
| GitHub Actions auth failed | Check Terraform completed successfully; re-run `terraform apply` |
| Terraform apply failed | Check GCP permissions and API enablement |
| Resource already exists | Use `terraform import` to import existing resources into state |
| Agent Engine deploy timeout | Deployments take 5-10 min; check status via `gh run view RUN_ID` |

### Monitoring CI/CD Deployments

```bash
# List recent workflow runs
gh run list --repo OWNER/REPO --limit 5

# View run details and job status
gh run view RUN_ID --repo OWNER/REPO

# View specific job logs (when complete)
gh run view --job=JOB_ID --repo OWNER/REPO --log

# Watch deployment in real-time
gh run watch RUN_ID --repo OWNER/REPO
```

---

## Testing Your Deployed Agent

After deployment, you can test your agent. The method depends on your deployment target.

### Getting Deployment Info

The deployment endpoint is stored in `deployment_metadata.json` after `make deploy` completes.

### Testing Agent Engine Deployment

Your agent is deployed to Vertex AI Agent Engine.

**Option 1: Using the Testing Notebook (Recommended)**

```bash
# Open the testing notebook
jupyter notebook notebooks/adk_app_testing.ipynb
```

The notebook auto-loads from `deployment_metadata.json` and provides:
- Remote testing via `vertexai.Client`
- Streaming queries with `async_stream_query`
- Feedback registration

**Option 2: Python Script**

```python
import json
import vertexai

# Load deployment info
with open("deployment_metadata.json") as f:
    engine_id = json.load(f)["remote_agent_engine_id"]

# Connect to agent
client = vertexai.Client(location="us-central1")
agent = client.agent_engines.get(name=engine_id)

# Send a message
async for event in agent.async_stream_query(message="Hello!", user_id="test"):
    print(event)
```

**Option 3: Using the Playground**

```bash
make playground
# Open http://localhost:8000 in your browser
```

### Testing Cloud Run Deployment

Your agent is deployed to Cloud Run.

**Option 1: Using the Testing Notebook (Recommended)**

```bash
# Open the testing notebook
jupyter notebook notebooks/adk_app_testing.ipynb
```

**Option 2: Python Script**

```python
import json
import requests

SERVICE_URL = "YOUR_SERVICE_URL"  # From deployment_metadata.json
ID_TOKEN = !gcloud auth print-identity-token -q
headers = {"Content-Type": "application/json", "Authorization": f"Bearer {ID_TOKEN[0]}"}

# Step 1: Create a session
user_id = "test_user"
session_resp = requests.post(
    f"{SERVICE_URL}/apps/<your-agent-directory>/users/{user_id}/sessions",
    headers=headers,
    json={"state": {}}
)
session_id = session_resp.json()["id"]

# Step 2: Send a message
message_resp = requests.post(
    f"{SERVICE_URL}/run_sse",
    headers=headers,
    json={
        "app_name": "<your-agent-directory>",
        "user_id": user_id,
        "session_id": session_id,
        "new_message": {"role": "user", "parts": [{"text": "Hello!"}]},
        "streaming": True
    },
    stream=True
)

for line in message_resp.iter_lines():
    if line and line.decode().startswith("data: "):
        print(json.loads(line.decode()[6:]))
```

**Option 3: Using the Playground**

```bash
make playground
# Open http://localhost:8000 in your browser
```

### Deploying Frontend UI with IAP

For authenticated access to your UI (recommended for private-by-default deployments):

```bash
# Deploy frontend (builds on Cloud Build - avoids ARM/AMD64 mismatch on Apple Silicon)
gcloud run deploy SERVICE --source . --region REGION

# Enable IAP
gcloud beta run services update SERVICE --region REGION --iap

# Grant user access
gcloud beta iap web add-iam-policy-binding \
  --resource-type=cloud-run \
  --service=SERVICE \
  --region=REGION \
  --member=user:EMAIL \
  --role=roles/iap.httpsResourceAccessor
```

**Note:** Use `iap web add-iam-policy-binding` for IAP access, not `run services add-iam-policy-binding` (which is for `roles/run.invoker`).

---

## Testing A2A Protocol Agents

Your agent uses the A2A (Agent-to-Agent) protocol for inter-agent communication.

**Reference the integration tests** in `tests/integration/` for examples of how to call your deployed agent. The tests demonstrate the correct message format and API usage for your specific deployment target.

### A2A Protocol Common Mistakes

| Mistake | Symptom | Fix |
|---------|---------|-----|
| Using `content` instead of `text` | `Invalid message format` | Use `parts[].text`, not `parts[].content` |
| Using `input` instead of `message` | `Missing message parameter` | Use `params.message`, not `params.input` |
| Missing `messageId` | `ValidationError` | Include `message.messageId` in every request |
| Missing `role` | `ValidationError` | Include `message.role` (usually "user") |

### A2A Protocol Key Details

- Protocol Version: 0.3.0
- Transport: JSON-RPC 2.0
- Required fields: `task_id`, `message.messageId`, `message.role`, `message.parts`
- Part structure: `{text: "...", mimeType: "text/plain"}`

### Testing approaches vary by deployment

- **Agent Engine**: Use the testing notebook or Python SDK (see integration tests)
- **Cloud Run**: Use curl with identity token or the testing notebook

### Example: Testing A2A agent on Cloud Run

```bash
# Get your service URL from deployment output or Cloud Console
SERVICE_URL="https://your-service-url.run.app"

# Send a test message using A2A protocol
curl -X POST \
  -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "message/send",
    "params": {
      "task_id": "test-task-001",
      "message": {
        "messageId": "msg-001",
        "role": "user",
        "parts": [
          {
            "text": "Your test query here",
            "mimeType": "text/plain"
          }
        ]
      }
    },
    "id": "req-1"
  }' \
  "$SERVICE_URL/a2a/<your-agent-directory>"

# Get the agent card (describes capabilities)
curl -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  "$SERVICE_URL/a2a/<your-agent-directory>/.well-known/agent-card.json"
```

---

## Running Load Tests

To run load tests against your deployed agent:

```bash
make load-test
```

This uses Locust to simulate multiple concurrent users.

---

## Advanced: Batch & Event Processing

### When to Use Batch/Event Processing

Your agent currently runs as an interactive service. However, many use cases require processing large volumes of data asynchronously:

**Batch Processing:**
- **BigQuery Remote Functions**: Process millions of rows with Gemini (e.g., `SELECT analyze(customer_data) FROM customers`)
- **Data Pipeline Integration**: Trigger agent analysis from Dataflow, Spark, or other batch systems

**Event-Driven Processing:**
- **Pub/Sub**: React to events in real-time (e.g., order processing, fraud detection)
- **Eventarc**: Trigger on GCP events (e.g., new file in Cloud Storage)
- **Webhooks**: Accept HTTP callbacks from external systems

### Adding an /invoke Endpoint

Add an `/invoke` endpoint to your agent's `fast_api_app.py` for batch/event processing. The endpoint auto-detects the input format (BigQuery Remote Function, Pub/Sub, Eventarc, or direct HTTP).

**Core pattern:** Create a `run_agent` helper using `Runner` + `InMemorySessionService` for stateless processing, with a semaphore for concurrency control. Then route by request shape:

```python
@app.post("/invoke")
async def invoke(request: Dict[str, Any]):
    if "calls" in request:        # BigQuery: {"calls": [[row1], [row2]]}
        results = await asyncio.gather(*[run_agent(f"Analyze: {row}") for row in request["calls"]])
        return {"replies": results}
    if "message" in request:      # Pub/Sub: {"message": {"data": "base64..."}}
        payload = base64.b64decode(request["message"]["data"]).decode()
        return {"status": "success", "result": await run_agent(payload)}
    if "type" in request:         # Eventarc: {"type": "google.cloud...", "data": {...}}
        return {"status": "success", "result": await run_agent(str(request["data"]))}
    if "input" in request:        # Direct HTTP: {"input": "prompt"}
        return {"status": "success", "result": await run_agent(request["input"])}
```

**Test locally** with `make local-backend`, then curl each format:
```bash
# BigQuery
curl -X POST http://localhost:8000/invoke -H "Content-Type: application/json" \
  -d '{"calls": [["test input 1"], ["test input 2"]]}'
# Direct
curl -X POST http://localhost:8000/invoke -H "Content-Type: application/json" \
  -d '{"input": "your prompt here"}'
```

**Connect to GCP services:**
```bash
# Pub/Sub push subscription
gcloud pubsub subscriptions create my-sub --topic=my-topic \
    --push-endpoint=https://<your-service-name>.run.app/invoke
# Eventarc trigger
gcloud eventarc triggers create my-trigger \
    --destination-run-service=<your-service-name> \
    --destination-run-path=/invoke \
    --event-filters="type=google.cloud.storage.object.v1.finalized"
```

**Production tips:** Use semaphores to limit concurrent Gemini calls (avoid 429s), set Cloud Run `--max-instances`, and return per-row errors instead of failing entire batches. See [reference implementation](https://github.com/richardhe-fundamenta/practical-gcp-examples/blob/main/bq-remote-function-agent/customer-advisor/app/fast_api_app.py) for production patterns.
