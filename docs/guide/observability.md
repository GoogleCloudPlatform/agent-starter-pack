# Monitoring and Observability

![monitoring_flow](https://storage.googleapis.com/github-repo/generative-ai/sample-apps/e2e-gen-ai-app-starter-pack/monitoring_flow.png)

## Overview

Templated agents utilize [OpenTelemetry GenAI instrumentation](https://opentelemetry.io/docs/specs/semconv/gen-ai/) for comprehensive observability. The framework automatically captures and exports GenAI telemetry data to Google Cloud Storage in JSONL format, making it available for analysis via BigQuery.

## How It Works

The telemetry setup (`app/app_utils/telemetry.py`) configures environment variables that enable:

- **GenAI Event Capture**: Records model interactions, token usage, and performance metrics
- **GCS Upload**: Automatically uploads telemetry data to a dedicated GCS bucket in JSONL format
- **Resource Attribution**: Tags events with service namespace and version for filtering

**Telemetry is opt-in and configured automatically:**
- **Cloud Run deployments**: Enabled by default with `NO_CONTENT` (privacy-preserving, no prompt/response content)
- **Agent Engine deployments**: Enabled by default with full message content for UI visibility
- **Local development**: Disabled by default (no `LOGS_BUCKET_NAME` set)

## Testing in Development

After deploying to your development environment, verify that telemetry is working correctly:

### 1. Deploy and Generate Test Traffic

```bash
# Deploy to dev project
gcloud config set project YOUR_DEV_PROJECT_ID
make deploy

# Make a few test requests to your agent
# (use your agent's endpoint - Cloud Run URL or Agent Engine)
```

### 2. Verify GCS Upload

Check that telemetry data is being written to GCS:

```bash
# Set your project variables
PROJECT_ID="your-dev-project-id"
PROJECT_NAME="your-project-name"

# List telemetry files in GCS
gsutil ls gs://${PROJECT_ID}-${PROJECT_NAME}-logs/completions/

# View a sample telemetry file
gsutil cat gs://${PROJECT_ID}-${PROJECT_NAME}-logs/completions/$(gsutil ls gs://${PROJECT_ID}-${PROJECT_NAME}-logs/completions/ | head -1)
```

### 3. Verify Cloud Logging Bucket

Check that the dedicated Cloud Logging bucket was created:

```bash
# Describe the telemetry logging bucket
gcloud logging buckets describe ${PROJECT_NAME}-genai-telemetry \
  --location=us-central1 \
  --project=${PROJECT_ID}
```

### 4. Query Telemetry in BigQuery

Verify that BigQuery can read the telemetry data:

```bash
# Query recent completions
bq query --use_legacy_sql=false \
  "SELECT * FROM \`${PROJECT_ID}.${PROJECT_NAME}_telemetry.completions\` LIMIT 10"

# Query GenAI operation logs from Cloud Logging
bq query --use_legacy_sql=false \
  "SELECT timestamp, jsonPayload FROM \`${PROJECT_ID}.${PROJECT_NAME}_genai_telemetry_logs._AllLogs\` LIMIT 10"
```

### Troubleshooting

If telemetry is not appearing:

1. **Check bucket permissions**: Ensure the service account has `storage.objectCreator` role on the logs bucket
2. **Verify environment variables**: Check that `LOGS_BUCKET_NAME` is set in your deployment
3. **Check application logs**: Look for telemetry setup warnings in Cloud Logging
4. **Confirm BigQuery tables exist**: Run `bq ls ${PROJECT_NAME}_telemetry` to list tables

### Storage Architecture

Telemetry data is stored in the existing logs bucket:
- **Bucket**: `{project_id}-{project_name}-logs`
- **Path**: `gs://{bucket}/genai-telemetry/`
- **Format**: Newline-delimited JSON (JSONL) for efficient querying

The telemetry setup gracefully handles permission errors - if bucket creation fails, the application continues without blocking, logging a warning instead.

### Querying Telemetry Data

Telemetry data is accessible through BigQuery, configured via Terraform in `deployment/terraform/bigquery_external.tf`:

1. **Telemetry View**: `{project_name}_telemetry.genai_telemetry`
   - Flattened view with extracted JSON fields for easier querying
   - Built on top of external table that reads GCS directly
   - No data duplication - queries GCS in real-time
   - Pre-extracted fields: `service_namespace`, `model`, `input_tokens`, `output_tokens`, etc.

2. **Raw External Table**: `{project_name}_telemetry.genai_telemetry_raw`
   - Direct access to raw JSONL data
   - Use this for custom queries or schema exploration

3. **Feedback Data**: Feedback logs can be queried from `_AllLogs` in Cloud Logging
   - Filter: `jsonPayload.log_type="feedback"`

### Example Queries

**Query recent telemetry events:**
```sql
SELECT
  timestamp,
  service_namespace,
  service_version,
  model,
  operation_name,
  input_tokens,
  output_tokens
FROM `{project_id}.{project_name}_telemetry.genai_telemetry`
WHERE timestamp > TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 HOUR)
ORDER BY timestamp DESC
LIMIT 100;
```

**Analyze token usage by model:**
```sql
SELECT
  model,
  service_namespace,
  COUNT(*) as request_count,
  SUM(input_tokens) as total_input_tokens,
  SUM(output_tokens) as total_output_tokens,
  AVG(input_tokens) as avg_input_tokens,
  AVG(output_tokens) as avg_output_tokens
FROM `{project_id}.{project_name}_telemetry.genai_telemetry`
WHERE timestamp > TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 24 HOUR)
  AND input_tokens IS NOT NULL
GROUP BY model, service_namespace
ORDER BY total_input_tokens DESC;
```

**Track requests by version:**
```sql
SELECT
  service_version,
  DATE(timestamp) as date,
  COUNT(*) as request_count,
  SUM(input_tokens + output_tokens) as total_tokens
FROM `{project_id}.{project_name}_telemetry.genai_telemetry`
WHERE timestamp > TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
GROUP BY service_version, date
ORDER BY date DESC, service_version;
```

## Advanced: Custom Visualization

For teams that want visual dashboards, you can connect your BigQuery telemetry data to visualization tools like [Looker Studio](https://lookerstudio.google.com/), [Data Studio](https://datastudio.google.com/), or other BI tools that support BigQuery as a data source.

**To create a custom dashboard:**

1. Connect your BI tool to BigQuery
2. Point to your project's BigQuery telemetry tables:
   - `{project_id}.{project_name}_telemetry.completions` - Message content and token data
   - `{project_id}.{project_name}_genai_telemetry_logs._AllLogs` - GenAI operation logs
3. Build visualizations for key metrics like token usage, request volume, latency, and model performance

**Note:** For most use cases, querying telemetry data directly in BigQuery (see examples above) provides sufficient analytics capabilities.

## Configuration

Telemetry behavior can be customized via environment variables:

### Customization Options

- `LOGS_BUCKET_NAME`: GCS bucket for telemetry upload (automatically set by CI/CD and Terraform)
  - If not set, telemetry is disabled
- `GENAI_TELEMETRY_PATH`: Override default path within bucket (default: `completions`)
- `OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT`: Control telemetry enablement and message content capture
  - `false`: Telemetry disabled (default for local development)
  - `NO_CONTENT`: Telemetry enabled without prompt/response content (default for Cloud Run)
  - `true`: Telemetry enabled with full message content (default for Agent Engine)

### Disabling Telemetry

To disable telemetry collection, set the following environment variable in your deployment:

```bash
OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT=false
```

**For Cloud Run deployments**, add this to your service configuration:
```bash
gcloud run services update YOUR_SERVICE_NAME \
  --set-env-vars OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT=false \
  --region=YOUR_REGION
```

**For Agent Engine deployments**, add this to your environment variables in `app_utils/deploy.py` or set it in your deployment environment.

**For local development**, add this to your `.env` file or export it before running:
```bash
export OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT=false
make playground
```

### Automatically Set Variables

The following environment variables are configured automatically by the telemetry setup:

- `GOOGLE_CLOUD_AGENT_ENGINE_ENABLE_TELEMETRY=true`
- `OTEL_INSTRUMENTATION_GENAI_UPLOAD_FORMAT=jsonl`
- `OTEL_INSTRUMENTATION_GENAI_COMPLETION_HOOK=upload`
- `OTEL_SEMCONV_STABILITY_OPT_IN=gen_ai_latest_experimental`
- `OTEL_RESOURCE_ATTRIBUTES=service.namespace={project_name},service.version={commit_sha}`
- `OTEL_INSTRUMENTATION_GENAI_UPLOAD_BASE_PATH=gs://{bucket}/{path}`

## Disclaimer

**Note:** The templated agents are designed to enable *your* use-case observability in your Google Cloud Project. Google Cloud does not log, monitor, or otherwise access any data generated from the deployed resources. See the [Google Cloud Service Terms](https://cloud.google.com/terms/service-terms) for more details.
