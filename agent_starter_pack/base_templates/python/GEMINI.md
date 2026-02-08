# Coding Agent Guide

**If your context window is limited:** Read this Table of Contents, then fetch only the sections you need.

## Table of Contents
{%- if cookiecutter.is_adk %}

### Part 1: ADK Cheatsheet
1. [Core Concepts & Project Structure](#1-core-concepts--project-structure)
2. [Agent Definitions (`LlmAgent`)](#2-agent-definitions-llmagent)
3. [Orchestration with Workflow Agents](#3-orchestration-with-workflow-agents)
4. [Multi-Agent Systems & Communication](#4-multi-agent-systems--communication)
5. [Building Custom Agents (`BaseAgent`)](#5-building-custom-agents-baseagent)
6. [Models Configuration](#6-models-configuration)
7. [Tools: The Agent's Capabilities](#7-tools-the-agents-capabilities)
8. [Context, State, and Memory](#8-context-state-and-memory)
9. [Callbacks](#9-callbacks)

### Part 2: Development Workflow
{%- else %}

### Development Workflow
{%- endif %}
- [DESIGN_SPEC.md - Your Primary Reference](#designspecmd---your-primary-reference)
- [Phase 1: Understand the Spec](#phase-1-understand-the-spec)
- [Phase 2: Build and Implement](#phase-2-build-and-implement)
- [Phase 3: The Evaluation Loop](#phase-3-the-evaluation-loop-main-iteration-phase)
- [Phase 4: Pre-Deployment Tests](#phase-4-pre-deployment-tests)
- [Phase 5: Deploy to Dev](#phase-5-deploy-to-dev-environment)
- [Phase 6: Production Deployment](#phase-6-production-deployment---choose-your-path)
- [Development Commands](#development-commands)
- [Operational Guidelines](#operational-guidelines-for-coding-agents)

---
{%- if cookiecutter.is_adk %}

{{ cookiecutter.adk_cheatsheet }}

For further reading on ADK, see: https://google.github.io/adk-docs/llms.txt
{%- endif %}

---

# Agentic Development Workflow

## DESIGN_SPEC.md - Your Primary Reference

**IMPORTANT**: If `DESIGN_SPEC.md` exists in this project, it is your primary source of truth.

Read it FIRST to understand:
- Functional requirements and capabilities
- Success criteria and quality thresholds
- Agent behavior constraints
- Expected tools and integrations

**The spec is your contract.** All implementation decisions should align with it. When in doubt, refer back to DESIGN_SPEC.md.

## Phase 1: Understand the Spec

Before writing any code:
1. Read `DESIGN_SPEC.md` thoroughly
2. Identify the core capabilities required
3. Note any constraints or things the agent should NOT do
4. Understand success criteria for evaluation

## Phase 2: Build and Implement

Implement the agent logic:

1. Write/modify code in `{{cookiecutter.agent_directory}}/`
2. Use `make playground` for interactive testing during development
3. Iterate on the implementation based on user feedback

## Phase 3: The Evaluation Loop (Main Iteration Phase)
{%- if cookiecutter.is_adk and not cookiecutter.is_adk_live %}

This is where most iteration happens. Work with the user to:

1. **Start small**: Begin with 1-2 sample eval cases, not a full suite
2. Run evaluations: `make eval`
3. Discuss results with the user
4. Fix issues and iterate on the core cases first
5. Only after core cases pass, add edge cases and new scenarios
6. Adjust prompts, tools, or agent logic based on results
7. Repeat until quality thresholds are met

**Why start small?** Too many eval cases at the beginning creates noise. Get 1-2 core cases passing first to validate your agent works, then expand coverage.

```bash
make eval
```

Review the output:
- `tool_trajectory_avg_score`: Are the right tools called in order?
- `response_match_score`: Do responses match expected patterns?

**Expect 5-10+ iterations here** as you refine the agent with the user.

### LLM-as-a-Judge Evaluation (Recommended)

For high-quality evaluations, use LLM-based metrics that judge response quality semantically.

**Running with custom config:**
```bash
uv run adk eval ./app <path_to_evalset.json> --config_file_path=<path_to_config.json>
```

Or use the Makefile:
```bash
make eval EVALSET=tests/eval/evalsets/my_evalset.json
```

**Configuration Schema (`test_config.json`):**

**CRITICAL:** The JSON configuration for rubrics **must use camelCase** (not snake_case).

```json
{
  "criteria": {
    "tool_trajectory_avg_score": 1.0,
    "final_response_match_v2": 0.8,
    "rubric_based_final_response_quality_v1": {
      "threshold": 0.8,
      "rubrics": [
        {
          "rubricId": "professionalism",
          "rubricContent": { "textProperty": "The response must be professional and helpful." }
        },
        {
          "rubricId": "safety",
          "rubricContent": { "textProperty": "The agent must NEVER book without asking for confirmation." }
        }
      ]
    }
  }
}
```

**EvalSet Schema (`evalset.json`):**
```json
{
  "eval_set_id": "my_eval_set",
  "eval_cases": [
    {
      "eval_id": "search_test",
      "conversation": [
        {
          "user_content": { "parts": [{ "text": "Find a flight to NYC" }] },
          "final_response": {
            "role": "model",
            "parts": [{ "text": "I found a flight for $500. Want to book?" }]
          },
          "intermediate_data": {
            "tool_uses": [
              { "name": "search_flights", "args": { "destination": "NYC" } }
            ]
          }
        }
      ],
      "session_input": { "app_name": "my_app", "user_id": "user_1", "state": {} }
    }
  ]
}
```

**Key Metrics:**

| Metric | Purpose |
|--------|---------|
| `tool_trajectory_avg_score` | Ensures the right tools were called in the right order |
| `final_response_match_v2` | Uses LLM to check if agent's answer matches ground truth semantically |
| `rubric_based_final_response_quality_v1` | Judges agent against custom rules (tone, safety, confirmation) |
| `hallucinations_v1` | Ensures agent's response is grounded in tool output |

For complete metric definitions, see: `site-packages/google/adk/evaluation/eval_metrics.py`

**Prefer Rubrics over Semantic Matches:**

For complex outputs like executive digests or multi-part responses, `final_response_match_v2` is often too sensitive. `rubric_based_final_response_quality_v1` is far superior because it judges specific qualities (tone, citations, strategic relevance) rather than comparing against a static string.

**The Proactivity Trajectory Gap:**

LLMs are often "too helpful" and will perform extra actions. For example, an agent might call `google_search` immediately after `save_preferences` even when not asked. This causes `tool_trajectory_avg_score` failures. Solutions:
- Include ALL tools the agent might call in your expected trajectory
- Use extremely strict instructions: "Stop after calling save_preferences. Do NOT search."
- Use rubric-based evaluation instead of trajectory matching

**Multi-turn conversations require tool_uses for ALL turns:**

The `tool_trajectory_avg_score` uses EXACT matching. If you don't specify expected tool calls for intermediate turns, the evaluation will fail even if the agent called the right tools.

```json
{
  "conversation": [
    {
      "invocation_id": "inv_1",
      "user_content": { "parts": [{"text": "Find me a flight from NYC to London on 2026-06-01"}] },
      "intermediate_data": {
        "tool_uses": [
          { "name": "search_flights", "args": {"origin": "NYC", "destination": "LON", "departure_date": "2026-06-01"} }
        ]
      }
    },
    {
      "invocation_id": "inv_2",
      "user_content": { "parts": [{"text": "Book the first option for Elias (elias@example.com)"}] },
      "intermediate_data": {
        "tool_uses": [
          { "name": "get_flight_price", "args": {"flight_offer": {"id": "1", "price": {"total": "500.00"}}} }
        ]
      }
    },
    {
      "invocation_id": "inv_3",
      "user_content": { "parts": [{"text": "Yes, confirm the booking"}] },
      "final_response": { "role": "model", "parts": [{"text": "Booking confirmed! Reference: ABC123"}] },
      "intermediate_data": {
        "tool_uses": [
          { "name": "book_flight", "args": {"passenger_name": "Elias", "email": "elias@example.com"} }
        ]
      }
    }
  ]
}
```

**Common eval failure causes:**
- Missing `tool_uses` in intermediate turns → trajectory score fails
- Agent mentions data not in tool output → `hallucinations_v1` fails
- Response not explicit enough → `rubric_based` score drops

**The `before_agent_callback` Pattern (State Initialization):**

Always use a callback to initialize session state variables used in your instruction template (like `{user_preferences}`). This prevents `KeyError` crashes on the first turn before the user has provided data:

```python
async def initialize_state(callback_context: CallbackContext) -> None:
    """Initialize session state with defaults if not present."""
    state = callback_context.state
    if "user_preferences" not in state:
        state["user_preferences"] = {}
    if "feedback_history" not in state:
        state["feedback_history"] = []

root_agent = Agent(
    name="my_agent",
    before_agent_callback=initialize_state,
    instruction="Based on preferences: {user_preferences}...",
    ...
)
```

**Eval-State Overrides (Type Mismatch Danger):**

Be careful with `session_input.state` in your evalset.json. It overrides Python-level initialization and can introduce type errors:

```json
// WRONG - initializes feedback_history as a string, breaks .append()
"state": { "feedback_history": "" }

// CORRECT - matches the Python type (list)
"state": { "feedback_history": [] }
```

This can cause cryptic errors like `AttributeError: 'str' object has no attribute 'append'` in your tool logic.

### Evaluation Gotchas

**App name must match directory name:**
The `App` object's `name` parameter MUST match the directory containing your agent. If your agent is in the `app/` directory, use `name="app"`:

```python
# ✅ CORRECT - matches the "app" directory
app = App(root_agent=root_agent, name="app")

# ❌ WRONG - causes "Session not found" errors
app = App(root_agent=root_agent, name="flight_booking_assistant")
```

If names don't match, you'll get: `Session not found... The runner is configured with app name "X", but the root agent was loaded from ".../app"`

**Evaluating Agents with `google_search` (IMPORTANT):**

`google_search` is NOT a regular tool - it's a **model-internal grounding feature**:

```python
# How google_search works internally:
llm_request.config.tools.append(
    types.Tool(google_search=types.GoogleSearch())  # Injected into model config
)
```

**Key behavior:**
- Custom tools (`save_preferences`, `save_feedback`) → appear as `function_call` in trajectory ✓
- `google_search` → NEVER appears in trajectory ✗ (happens inside the model)
- Search results come back as `grounding_metadata`, not function call/response events

**BUT the evaluator STILL detects it** at the session level:
```json
{
  "error_code": "UNEXPECTED_TOOL_CALL",
  "error_message": "Unexpected tool call: google_search"
}
```

This causes `tool_trajectory_avg_score` to ALWAYS fail for agents using `google_search`.

**Metric compatibility for `google_search` agents:**

| Metric | Usable? | Why |
|--------|---------|-----|
| `tool_trajectory_avg_score` | NO | Always fails due to unexpected google_search |
| `response_match_score` | Maybe | Unreliable for dynamic news content |
| `rubric_based_final_response_quality_v1` | YES | Evaluates output quality semantically |
| `final_response_match_v2` | Maybe | Works for stable expected outputs |

**Evalset best practices for `google_search` agents:**

```json
{
  "eval_id": "news_digest_test",
  "conversation": [{
    "user_content": { "parts": [{"text": "Give me my news digest."}] }
    // NO intermediate_data.tool_uses for google_search - it won't match anyway
  }]
}
```

For custom tools alongside google_search, still include them (but NOT google_search):
```json
{
  "intermediate_data": {
    "tool_uses": [
      { "name": "save_feedback" }  // Custom tools work fine
      // Do NOT include google_search here
    ]
  }
}
```

**Config for `google_search` agents:**

```json
{
  "criteria": {
    // REMOVE this - incompatible with google_search:
    // "tool_trajectory_avg_score": 1.0,

    // Use rubric-based evaluation instead:
    "rubric_based_final_response_quality_v1": {
      "threshold": 0.6,
      "rubrics": [
        { "rubricId": "has_citations", "rubricContent": { "textProperty": "Response includes source citations or references" } },
        { "rubricId": "relevance", "rubricContent": { "textProperty": "Response directly addresses the user's query" } }
      ]
    }
  }
}
```

**Bottom line:** `google_search` is a model feature, not a function tool. You cannot test it with trajectory matching. Use rubric-based LLM-as-judge evaluation to verify the agent produces grounded, cited responses.

**ADK Built-in Tools: Trajectory Behavior Reference**

This applies to ALL Gemini model-internal tools, not just `google_search`:

**Model-Internal Tools (DON'T appear in trajectory):**

| Tool | Type | In Trajectory? | Eval Strategy |
|------|------|----------------|---------------|
| `google_search` | `types.GoogleSearch()` | ❌ No | Rubric-based |
| `google_search_retrieval` | `types.GoogleSearchRetrieval()` | ❌ No | Rubric-based |
| `BuiltInCodeExecutor` | `types.CodeExecution()` | ❌ No | Check output |
| `VertexAiSearchTool` | `types.Retrieval()` | ❌ No | Rubric-based |
| `url_context` | Model-internal | ❌ No | Rubric-based |

These inject into `llm_request.config.tools` as model capabilities:
```python
types.Tool(google_search=types.GoogleSearch())
types.Tool(code_execution=types.ToolCodeExecution())
types.Tool(retrieval=types.Retrieval(...))
```

**Function-Based Tools (DO appear in trajectory):**

| Tool | Type | In Trajectory? | Eval Strategy |
|------|------|----------------|---------------|
| `load_web_page` | FunctionTool | ✅ Yes | `tool_trajectory_avg_score` works |
| Custom tools | FunctionTool | ✅ Yes | `tool_trajectory_avg_score` works |
| AgentTool | Wrapped agent | ✅ Yes | `tool_trajectory_avg_score` works |

These generate `function_call` and `function_response` events:
```python
types.Tool(function_declarations=[...])
```

**Quick Reference - Can I use `tool_trajectory_avg_score`?**
- `google_search` → NO (model-internal)
- `code_executor` → NO (model-internal)
- `VertexAiSearchTool` → NO (model-internal)
- `load_web_page` → YES (FunctionTool)
- Custom functions → YES (FunctionTool)

**Rule of Thumb:**
- If a tool provides grounding/retrieval/execution capabilities built into Gemini → model-internal, won't appear in trajectory
- If it's a Python function you can call → appears in trajectory, can test with `tool_trajectory_avg_score`

**When mixing both types** (e.g., `google_search` + `save_preferences`):
1. Remove `tool_trajectory_avg_score` entirely, OR
2. Only test function-based tools in `tool_uses` and accept the trajectory will be incomplete

**Model thinking mode may bypass tools:**
Models with "thinking" enabled may decide they have sufficient information and skip tool calls. Use `tool_config` with `mode="ANY"` to force tool usage, or switch to a non-thinking model like `gemini-2.0-flash` for predictable tool calling.

**Sub-agents need instances, not function references:**
When using multi-agent systems with `sub_agents`, you must pass **Agent instances**, not factory function references.

```python
# ❌ WRONG - This fails with ValidationError
sub_agents=[
    create_lead_qualifier,   # Function reference - FAILS!
    create_product_matcher,  # Function reference - FAILS!
]

# ✅ CORRECT - Call the factories to get instances
sub_agents=[
    create_lead_qualifier(),   # Instance - WORKS
    create_product_matcher(),  # Instance - WORKS
]
```

**Root cause**: ADK's pydantic validation expects `BaseAgent` instances, not callables. The error message is:
`ValidationError: Input should be a valid dictionary or instance of BaseAgent`

When using `SequentialAgent` with sub-agents that may be reused, create each sub-agent via a factory function (not module-level instances) to avoid "agent already has a parent" errors:

```python
def create_researcher():
    return Agent(name="researcher", ...)

root_agent = SequentialAgent(
    sub_agents=[create_researcher(), create_analyst()],  # Note: calling the functions!
    ...
)
```

**A2A handoffs pass data between agents:**
When using multi-agent systems (SequentialAgent), data flows between sub-agents through the conversation history and context. To ensure proper handoffs:

```python
# Lead Qualifier agent should include score in response
def create_lead_qualifier():
    return Agent(
        name="lead_qualifier",
        instruction="Score leads 1-100. ALWAYS include the score in your response: 'Lead score: XX/100'",
        ...
    )

# Product Matcher receives the score via conversation context
def create_product_matcher():
    return Agent(
        name="product_matcher",
        instruction="Recommend products based on the lead score from the previous agent.",
        ...
    )
```

Verify handoffs in eval by checking that sub-agents reference data from previous agents in their responses.

**Mock mode for external APIs:**
When your agent calls external APIs, add mock mode so evals can run without real credentials:
```python
def call_external_api(query: str) -> dict:
    api_key = os.environ.get("EXTERNAL_API_KEY", "")
    if not api_key or api_key == "dummy_key":
        return {"status": "success", "data": "mock_response"}
    # Real API call here
```
{%- if cookiecutter.session_type == "cloud_sql" %}

**Session persistence testing (Cloud SQL):**
When using Cloud SQL for sessions, add test cases that verify session resume functionality:

```json
{
  "test_case": "session_resume",
  "description": "Verify agent remembers context from previous conversation",
  "steps": [
    {
      "input": "Qualify lead #123",
      "expected_response_contains": ["score", "qualified"]
    },
    {
      "input": "What products did you recommend for this lead?",
      "new_session": false,
      "expected_response_contains": ["products", "lead #123"]
    }
  ]
}
```

Key testing principles:
- Test same session_id across multiple requests
- Verify agent recalls previous conversation details
- Test session isolation (different session_id = no shared context)
- Verify database persistence survives service restarts
{%- endif %}
{%- else %}

For this agent type, use manual testing via `make playground` and verify against DESIGN_SPEC.md requirements. Iterate with the user until the agent behaves correctly.
{%- endif %}
{%- if cookiecutter.requires_data_ingestion %}

## Phase 3.5: Data Ingestion (RAG Agents Only)

**CRITICAL**: Before deploying a RAG agent, you MUST ingest data into the vector store.

### Data Ingestion Setup

1. **Prepare Sample Documents**: Create or obtain 3-5 sample documents relevant to your agent's domain (PDFs, text files, etc.)
2. **Upload to GCS**: Place documents in a GCS bucket
3. **Set Up Infrastructure**: Run `make setup-dev-env` to provision the vector store (Vertex AI Search or Vector Search)
4. **Run Data Ingestion**: Execute `make data-ingestion` to process and index documents

```bash
# Example workflow
make setup-dev-env  # Provisions vector store infrastructure
make data-ingestion # Processes documents and creates embeddings
```

### Data Ingestion Best Practices

- **Test with Real Data**: Use documents representative of production data
- **Verify Indexing**: After ingestion, test retrieval with sample queries via `make playground`
- **Citation Format**: Ensure your agent includes document sources in responses (e.g., "[Document Name, p.3]")
- **Chunking Strategy**: Default is 512 tokens with 50-token overlap; adjust in `data_ingestion/` if needed
- **Wait for Indexing**: Vector stores may take 2-5 minutes to fully index after ingestion

### RAG-Specific Evaluation Criteria

When evaluating RAG agents, add these additional test cases:

- **Citation Accuracy**: Responses include correct document references
- **Out-of-Scope Handling**: Agent refuses questions outside indexed knowledge
- **Multi-Document Synthesis**: Agent combines information from multiple sources
- **No Results Found**: Agent admits when no relevant documents exist

See `tests/eval/evalsets/basic.evalset.json` for examples.
{%- endif %}

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

**Secret Manager (for API credentials):**

Instead of passing sensitive keys as environment variables (which can be logged or visible in console), use GCP Secret Manager.

**1. Store secrets via gcloud:**
```bash
# Create the secret
echo -n "YOUR_API_KEY" | gcloud secrets create MY_SECRET_NAME --data-file=-

# Update an existing secret
echo -n "NEW_API_KEY" | gcloud secrets versions add MY_SECRET_NAME --data-file=-
```

**2. Grant access (IAM):**
The agent's service account needs the `Secret Manager Secret Accessor` role:
```bash
PROJECT_ID=$(gcloud config get-value project)
PROJECT_NUMBER=$(gcloud projects list --filter="project_id:$PROJECT_ID" --format="value(project_number)")
SA_EMAIL="service-$PROJECT_NUMBER@gcp-sa-aiplatform-re.iam.gserviceaccount.com"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SA_EMAIL" \
    --role="roles/secretmanager.secretAccessor"
```
{%- if cookiecutter.deployment_target == "agent_engine" %}

**3. Use secrets in deployment (Agent Engine):**

Pass secrets during deployment with `--set-secrets`. Note: `make deploy` doesn't support secrets, so run deploy.py directly:
```bash
uv run python -m {{cookiecutter.agent_directory}}.app_utils.deploy --set-secrets "API_KEY=my-api-key,DB_PASS=db-password:2"
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
{%- elif cookiecutter.deployment_target == "cloud_run" %}

**3. Use secrets in deployment (Cloud Run):**

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
{%- endif %}

## Phase 4: Pre-Deployment Tests

Once evaluation thresholds are met, run tests before deployment:

```bash
make test
```

If tests fail, fix issues and run again until all tests pass.

## Phase 5: Deploy to Dev Environment

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

## Phase 6: Production Deployment - Choose Your Path

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
- Teams requiring staging → production promotion
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
- Safe staging → production promotion
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

### After CI/CD Setup: Activating the Pipeline

**IMPORTANT**: `setup-cicd` creates infrastructure but doesn't deploy the agent automatically.

Terraform automatically configures all required GitHub secrets and variables (WIF credentials, project IDs, service accounts, etc.). No manual configuration needed.

#### Step 1: Commit and Push

```bash
git add . && git commit -m "Initial agent implementation"
git push origin main
```

#### Step 2: Monitor Deployment

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

### Troubleshooting CI/CD

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

## Development Commands

| Command | Purpose |
|---------|---------|
| `make playground` | Interactive local testing |
| `make test` | Run unit and integration tests |
{%- if cookiecutter.is_adk and not cookiecutter.is_adk_live %}
| `make eval` | Run evaluation against evalsets |
| `make eval-all` | Run all evalsets |
{%- endif %}
| `make lint` | Check code quality |
| `make setup-dev-env` | Set up dev infrastructure (Terraform) |
| `make deploy` | Deploy to dev (requires human approval) |

## Testing Your Deployed Agent

After deployment, you can test your agent. The method depends on your deployment target.

### Getting Deployment Info

The deployment endpoint is stored in `deployment_metadata.json` after `make deploy` completes.

{%- if cookiecutter.deployment_target == "agent_engine" %}

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

{%- elif cookiecutter.deployment_target == "cloud_run" %}

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
    f"{SERVICE_URL}/apps/{{cookiecutter.agent_directory}}/users/{user_id}/sessions",
    headers=headers,
    json={"state": {}}
)
session_id = session_resp.json()["id"]

# Step 2: Send a message
message_resp = requests.post(
    f"{SERVICE_URL}/run_sse",
    headers=headers,
    json={
        "app_name": "{{cookiecutter.agent_directory}}",
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
{%- if cookiecutter.is_adk and cookiecutter.session_type == "cloud_sql" %}

### Testing Cloud SQL Session Persistence

Your agent uses Cloud SQL (PostgreSQL) for session storage. To verify sessions persist correctly:

**1. Test Session Creation and Resume:**

```bash
# First request - create session and have a conversation
curl -X POST $SERVICE_URL/run \
  -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  -H "Content-Type: application/json" \
  -d '{"input": "Qualify lead #123"}' | jq -r '.session_id'

# Save the session_id from the response, then test resume:
curl -X POST $SERVICE_URL/run \
  -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  -H "Content-Type: application/json" \
  -d '{"input": "What was the lead score?", "session_id": "SESSION_ID_FROM_ABOVE"}'
```

The agent should recall details from the first conversation.

**2. Verify Cloud SQL Connection:**

```bash
# Check Cloud Run service logs for successful DB connection
gcloud run services logs read {{cookiecutter.project_name}} \
  --project={{cookiecutter.dev_project_id}} \
  --region={{cookiecutter.region}} \
  --limit=50 | grep -i "database\|cloud_sql"

# Verify Cloud SQL instance is running
gcloud sql instances describe {{cookiecutter.project_name}}-db-dev \
  --project={{cookiecutter.dev_project_id}}
```

**3. Common Cloud SQL Issues:**

| Issue | Symptom | Resolution |
|-------|---------|------------|
| Connection timeout | `Connection refused` errors | Check Cloud SQL instance is in same region as Cloud Run |
| IAM auth failed | `Login failed` errors | Verify service account has `roles/cloudsql.client` |
| Session not found | `Session does not exist` | Verify session_id matches and DB tables were created |
| Volume mount failed | `cloudsql volume not found` | Check terraform applied Cloud SQL volume configuration |

{%- endif %}

{%- endif %}
{%- if cookiecutter.is_a2a %}

### Testing A2A Protocol Agents

Your agent uses the A2A (Agent-to-Agent) protocol for inter-agent communication.

**Reference the integration tests** in `tests/integration/` for examples of how to call your deployed agent. The tests demonstrate the correct message format and API usage for your specific deployment target.

**A2A Protocol Common Mistakes:**

| Mistake | Symptom | Fix |
|---------|---------|-----|
| Using `content` instead of `text` | `Invalid message format` | Use `parts[].text`, not `parts[].content` |
| Using `input` instead of `message` | `Missing message parameter` | Use `params.message`, not `params.input` |
| Missing `messageId` | `ValidationError` | Include `message.messageId` in every request |
| Missing `role` | `ValidationError` | Include `message.role` (usually "user") |

**A2A Protocol Key Details:**
- Protocol Version: 0.3.0
- Transport: JSON-RPC 2.0
- Required fields: `task_id`, `message.messageId`, `message.role`, `message.parts`
- Part structure: `{text: "...", mimeType: "text/plain"}`

**Testing approaches vary by deployment:**
- **Agent Engine**: Use the testing notebook or Python SDK (see integration tests)
- **Cloud Run**: Use curl with identity token or the testing notebook

**Example: Testing A2A agent on Cloud Run:**

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
  "$SERVICE_URL/a2a/app"

# Get the agent card (describes capabilities)
curl -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  "$SERVICE_URL/a2a/app/.well-known/agent-card.json"
```
{%- endif %}

### Running Load Tests

To run load tests against your deployed agent:

```bash
make load-test
```

This uses Locust to simulate multiple concurrent users.
{%- if cookiecutter.is_adk and not cookiecutter.is_adk_live %}

## Adding Evaluation Cases

To improve evaluation coverage:

1. Add cases to `tests/eval/evalsets/basic.evalset.json`
2. Each case should test a capability from DESIGN_SPEC.md
3. Include expected tool calls in `intermediate_data.tool_uses`
4. Run `make eval` to verify
{%- endif %}

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

To enable batch/event processing, add an `/invoke` endpoint to your FastAPI app that auto-detects the input format:

```python
# Add to {{cookiecutter.agent_directory}}/fast_api_app.py

from typing import List, Any, Dict
import asyncio
import base64
import json
from pydantic import BaseModel

# Request/Response models for different sources
class BQResponse(BaseModel):
    replies: List[str]

# Concurrency control (module-level for reuse)
MAX_CONCURRENT = 10
semaphore = asyncio.Semaphore(MAX_CONCURRENT)


async def run_agent(prompt: str) -> str:
    """Run the agent with concurrency control.

    Uses Runner + InMemorySessionService for stateless batch processing.
    Each invocation creates a fresh session (no conversation history).
    """
    async with semaphore:
        try:
            from {{cookiecutter.agent_directory}}.agent import root_agent
            from google.adk.runners import Runner
            from google.adk.sessions import InMemorySessionService
            from google.genai import types as genai_types

            # Create ephemeral session for this request
            session_service = InMemorySessionService()
            await session_service.create_session(
                app_name="app", user_id="invoke_user", session_id="invoke_session"
            )
            runner = Runner(
                agent=root_agent, app_name="app", session_service=session_service
            )

            # Run agent and collect final response
            final_response = ""
            async for event in runner.run_async(
                user_id="invoke_user",
                session_id="invoke_session",
                new_message=genai_types.Content(
                    role="user",
                    parts=[genai_types.Part.from_text(text=prompt)]
                ),
            ):
                if event.is_final_response() and event.content and event.content.parts:
                    final_response = event.content.parts[0].text
            return final_response
        except Exception as e:
            return json.dumps({"error": str(e)})


@app.post("/invoke")
async def invoke(request: Dict[str, Any]):
    """
    Universal endpoint that auto-detects input format and routes accordingly.

    Supported formats:
    - BigQuery Remote Function: {"calls": [[row1], [row2], ...]}
    - Pub/Sub Push: {"message": {"data": "base64...", "attributes": {...}}}
    - Eventarc: {"data": {...}, "type": "google.cloud.storage.object.v1.finalized"}
    - Direct HTTP: {"input": "your prompt here"}
    """

    # === BigQuery Remote Function ===
    # Format: {"calls": [[col1, col2], [col1, col2], ...]}
    if "calls" in request:
        async def process_row(row_data: List[Any]) -> str:
            prompt = f"Analyze: {row_data}"
            return await run_agent(prompt)

        results = await asyncio.gather(
            *[process_row(row) for row in request["calls"]]
        )
        return BQResponse(replies=results)

    # === Pub/Sub Push Subscription ===
    # Format: {"message": {"data": "base64...", "attributes": {...}}, "subscription": "..."}
    if "message" in request:
        message = request["message"]
        # Decode base64 data
        data_b64 = message.get("data", "")
        try:
            data = base64.b64decode(data_b64).decode("utf-8")
            payload = json.loads(data)
        except Exception:
            payload = data_b64  # Use raw if not JSON

        attributes = message.get("attributes", {})
        prompt = f"Process event: {payload}\nAttributes: {attributes}"

        result = await run_agent(prompt)

        # Pub/Sub expects 2xx response to acknowledge
        return {"status": "success", "result": result}

    # === Eventarc (Cloud Events) ===
    # Format: {"data": {...}, "type": "google.cloud.storage.object.v1.finalized", ...}
    if "type" in request and request.get("type", "").startswith("google.cloud."):
        event_type = request["type"]
        event_data = request.get("data", {})

        # Example: Cloud Storage event
        if "storage" in event_type:
            bucket = event_data.get("bucket", "unknown")
            name = event_data.get("name", "unknown")
            prompt = f"Process file event: gs://{bucket}/{name}\nEvent type: {event_type}"
        else:
            prompt = f"Process GCP event: {event_type}\nData: {event_data}"

        result = await run_agent(prompt)
        return {"status": "success", "result": result}

    # === Direct HTTP / Webhook ===
    # Format: {"input": "your prompt"} or {"prompt": "your prompt"}
    if "input" in request or "prompt" in request:
        prompt = request.get("input") or request.get("prompt")
        result = await run_agent(prompt)
        return {"status": "success", "result": result}

    # Unknown format
    return {"status": "error", "message": "Unknown request format", "received_keys": list(request.keys())}
```

### Local Testing (Before Deployment)

**IMPORTANT:** Always test the `/invoke` endpoint locally before deploying. Unlike interactive chatbots, batch/event processing is harder to debug in production.

```bash
# Start local backend (default port 8000)
make local-backend

# Or specify a custom port (useful for parallel development)
make local-backend PORT=8081
```

**Test BigQuery batch format:**
```bash
curl -X POST http://localhost:8000/invoke \
  -H "Content-Type: application/json" \
  -d '{"calls": [["test input 1"], ["test input 2"]]}'
```

**Test Pub/Sub format (with base64 encoding):**
```bash
DATA=$(echo -n '{"key": "value"}' | base64)
curl -X POST http://localhost:8000/invoke \
  -H "Content-Type: application/json" \
  -d "{\"message\": {\"data\": \"$DATA\"}}"
```

**Test Eventarc format:**
```bash
curl -X POST http://localhost:8000/invoke \
  -H "Content-Type: application/json" \
  -d '{
    "type": "google.cloud.storage.object.v1.finalized",
    "data": {"bucket": "my-bucket", "name": "file.pdf"}
  }'
```

**What to verify:**
- Correct format detection (check which branch handles your request)
- Expected response format (`{"replies": [...]}` for BQ, `{"status": "success"}` for events)
- Tool calls in logs (for side-effect mode)
- Error handling for malformed inputs

### Integration Examples

**BigQuery Remote Function:**
```sql
-- Create connection (one-time setup)
CREATE EXTERNAL CONNECTION `project.region.bq_connection`
OPTIONS (cloud_resource_id="//cloudresourcemanager.googleapis.com/projects/PROJECT_ID");

-- Create remote function
CREATE FUNCTION dataset.analyze_customer(data STRING)
RETURNS STRING
REMOTE WITH CONNECTION `project.region.bq_connection`
OPTIONS (endpoint = 'https://{{cookiecutter.project_name}}.run.app/invoke');

-- Process millions of rows
SELECT customer_id, dataset.analyze_customer(customer_data) AS analysis
FROM customers;
```

**Pub/Sub Push Subscription:**
```bash
# Create push subscription pointing to /invoke
gcloud pubsub subscriptions create my-subscription \
    --topic=my-topic \
    --push-endpoint=https://{{cookiecutter.project_name}}.run.app/invoke
```

**Eventarc Trigger:**
```bash
# Trigger on Cloud Storage events
gcloud eventarc triggers create storage-trigger \
    --destination-run-service={{cookiecutter.project_name}} \
    --destination-run-path=/invoke \
    --event-filters="type=google.cloud.storage.object.v1.finalized" \
    --event-filters="bucket=my-bucket"
```

### Production Considerations

**Rate Limiting & Retry:**
- Use semaphores to limit concurrent Gemini calls (avoid 429 errors)
- Implement exponential backoff for transient failures
- For BigQuery: Raise `TransientError` on 429s to trigger automatic retries

**Error Handling:**
- Return per-row errors as JSON objects, don't fail entire batch
- Log errors with trace IDs for debugging
- Monitor error rates via Cloud Logging/Monitoring

**Cost Control:**
- Set Cloud Run `--max-instances` to cap concurrent executions
- Monitor Gemini API usage and set budget alerts
- Test with small batches before running on production data

### Reference Implementation

See complete production example with chunking, error handling, and monitoring:
https://github.com/richardhe-fundamenta/practical-gcp-examples/blob/main/bq-remote-function-agent/customer-advisor/app/fast_api_app.py

**Key patterns from reference:**
- Async processing with semaphore throttling (`MAX_CONCURRENT_ROWS = 10`)
- Chunk batching for memory efficiency (`CHUNK_SIZE = 10`)
- Transient vs permanent error classification

- Structured output extraction from agent responses

---

## Operational Guidelines for Coding Agents

These guidelines are essential for working on this project effectively.

### Principle 1: Code Preservation & Isolation

When executing code modifications, your paramount objective is surgical precision. You **must alter only the code segments directly targeted** by the user's request, while **strictly preserving all surrounding and unrelated code.**

**Mandatory Pre-Execution Verification:**

Before finalizing any code replacement, verify:

1.  **Target Identification:** Clearly define the exact lines or expressions to be changed, based *solely* on the user's explicit instructions.
2.  **Preservation Check:** Ensure all code, configuration values (e.g., `model`, `version`, `api_key`), comments, and formatting *outside* the identified target remain identical.

**Example:**

*   **User Request:** "Change the agent's instruction to be a recipe suggester."
*   **Original Code:**
    ```python
    root_agent = Agent(
        name="root_agent",
        model="gemini-3-flash-preview",
        instruction="You are a helpful AI assistant."
    )
    ```
*   **Incorrect (VIOLATION):**
    ```python
    root_agent = Agent(
        name="recipe_suggester",
        model="gemini-1.5-flash",  # UNINTENDED - model was not requested to change
        instruction="You are a recipe suggester."
    )
    ```
*   **Correct (COMPLIANT):**
    ```python
    root_agent = Agent(
        name="recipe_suggester",  # OK, related to new purpose
        model="gemini-3-flash-preview",  # PRESERVED
        instruction="You are a recipe suggester."  # OK, the direct target
    )
    ```

**Critical:** Always prioritize the integrity of existing code over rewriting entire blocks.

### Principle 2: Execution Best Practices

*   **Model Selection - CRITICAL:**
    *   **NEVER change the model unless explicitly asked.** If the code uses `gemini-3-flash-preview`, keep it as `gemini-3-flash-preview`. Do NOT "upgrade" or "fix" model names.
    *   When creating NEW agents (not modifying existing), use Gemini 3 series: `gemini-3-flash-preview`, `gemini-3-pro-preview`.
    *   Do NOT use older models (`gemini-2.0-flash`, `gemini-1.5-flash`, etc.) unless the user explicitly requests them.

*   **Location Matters More Than Model:**
    *   If a model returns a 404, it's almost always a `GOOGLE_CLOUD_LOCATION` issue (e.g., needing `global` instead of `us-central1`).
    *   Changing the model name to "fix" a 404 is a violation - fix the location instead.
    *   Some models (like `gemini-3-flash-preview`) require specific locations. Check the error message for hints.

*   **ADK Built-in Tool Imports (Precision Required):**
    *   ADK built-in tools require surgical imports to get the tool instance, not the module:
    ```python
    # CORRECT - imports the tool instance
    from google.adk.tools.load_web_page import load_web_page

    # WRONG - imports the module, not the tool
    from google.adk.tools import load_web_page
    ```
    *   Pass the imported tool directly to `tools=[load_web_page]`, not `tools=[load_web_page.load_web_page]`.

*   **Running Python Commands:**
    *   Always use `uv` to execute Python commands (e.g., `uv run python script.py`)
    *   Run `make install` before executing scripts
    *   Consult `Makefile` and `README.md` for available commands

*   **Troubleshooting:**
    *   **Check the ADK cheatsheet in this file first** - it covers most common patterns
    *   **Need more depth?** Use `get_docs` for full documentation:
        ```
        get_docs(action="search", source="adk", query="your error or concept")
        get_docs(action="read", source="adk", doc="tools-custom/mcp-tools")
        get_docs(action="read", source="asp", doc="guide/troubleshooting")
        ```
    *   For framework questions (ADK, LangGraph) or GCP products (Cloud Run), check official documentation
    *   When encountering persistent errors, a targeted Google Search often finds solutions faster

*   **Breaking Infinite Loops:**
    *   **Stop immediately** if you see the same error 3+ times in a row
    *   **Don't retry failed operations** - fix the root cause first
    *   **RED FLAGS**: Lock IDs incrementing, names appending v5→v6→v7, "I'll try one more time" repeatedly
    *   **State conflicts** (Error 409: Resource already exists): Import existing resources with `terraform import` instead of retrying creation
    *   **Tool bugs**: Fix source code bugs before continuing - don't work around them
    *   **When stuck**: Run underlying commands directly (e.g., `terraform` CLI) instead of calling problematic tools
