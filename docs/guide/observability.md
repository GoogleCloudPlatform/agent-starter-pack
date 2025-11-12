# Monitoring and Observability

![monitoring_flow](https://storage.googleapis.com/github-repo/generative-ai/sample-apps/e2e-gen-ai-app-starter-pack/monitoring_flow.png)

### GenAI Telemetry Capture

Templated agents utilize [OpenTelemetry GenAI instrumentation](https://opentelemetry.io/docs/specs/semconv/gen-ai/) for comprehensive observability. The framework automatically captures and exports GenAI telemetry data to Google Cloud Storage in JSONL format.

### How It Works

The telemetry setup (`app/app_utils/telemetry.py`) configures environment variables that enable:

- **GenAI Event Capture**: Records model interactions, token usage, and performance metrics
- **GCS Upload**: Automatically uploads telemetry data to a dedicated GCS bucket in JSONL format
- **Resource Attribution**: Tags events with service namespace and version for filtering

**Deployment-Specific Configuration:**
- **Default**: Message content capture is set to `NO_CONTENT` (privacy-preserving)
- **Agent Engine Deployment**: Overridden to `true` to enable message visibility in the Agent Engine UI

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

### Looker Studio Dashboard

Once the data is available in BigQuery, you can use it to populate a [Looker Studio dashboard](https://lookerstudio.google.com/c/reporting/46b35167-b38b-4e44-bd37-701ef4307418/page/tEnnC).

This dashboard template provides a starting point for building custom visualizations on top of the captured telemetry data.

### Configuration

Telemetry behavior can be customized via environment variables:

- `LOGS_BUCKET_NAME`: Override default bucket name (set by CI/CD to logs bucket)
- `GENAI_TELEMETRY_PATH`: Override default path within bucket (default: `genai-telemetry`)
- `OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT`: Control message content capture
  - Default: `NO_CONTENT` (privacy-preserving)
  - Agent Engine deployment: Overridden to `true` for UI visibility

**Environment Variables** (set automatically):
- `GOOGLE_CLOUD_AGENT_ENGINE_ENABLE_TELEMETRY=true`
- `OTEL_INSTRUMENTATION_GENAI_UPLOAD_FORMAT=jsonl`
- `OTEL_INSTRUMENTATION_GENAI_COMPLETION_HOOK=upload`
- `OTEL_SEMCONV_STABILITY_OPT_IN=gen_ai_latest_experimental`

## Disclaimer

**Note:** The templated agents are designed to enable *your* use-case observability in your Google Cloud Project. Google Cloud does not log, monitor, or otherwise access any data generated from the deployed resources. See the [Google Cloud Service Terms](https://cloud.google.com/terms/service-terms) for more details.
