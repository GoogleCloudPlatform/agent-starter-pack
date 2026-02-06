# BigQuery Agent Analytics Plugin

## Overview

The BigQuery Agent Analytics Plugin offers enhanced observability by logging detailed agent events directly to BigQuery. This enables rich, SQL-based analysis of agent behavior, interactions, and performance over time. This plugin replaces the legacy GCS/Cloud Logging-based prompt-response logging when enabled.

This is an **opt-in** feature, available for **ADK-based agents** only.

## When to Use

Enable this plugin when you need to:

*   **Use BigQuery's advanced LLM capabilities** for semantic analysis of your agents. For example, you could semantically group agent conversations, rank conversations, identify errors, or evaluate using an LLM as a judge. You can use BigQuery's functionalities like `AI.Search`, `AI.Score` and `AI.Generate_text` to achieve this.
*   **Utilize BigQuery's conversational analytics** to analyze your agents using another conversational agent, eliminating the need to write complex SQL queries manually.
*   **Create custom dashboards and reports** on agent performance, tool usage, and token consumption.
*   **Retain a structured, queryable history** of agent events for auditing, fine-tuning, or joining with other business data.
*   **Utilize GCS offloading** for large multimodal content within event logs.

Compared to the always-on [Cloud Trace telemetry](cloud-trace.md), this plugin provides more granular data in a structured table format, designed for offline analysis.

## Prerequisites

*   Agent Starter Pack project generated with an **ADK-based** agent template (e.g., `adk`, `adk_a2a`, `agentic_rag`).
*   `google-adk` version `>=1.21.0`. This is added automatically when you enable the plugin.
*   A Google Cloud project with the following APIs enabled (typically handled by Terraform):
    *   BigQuery API
    *   BigQuery Storage API

**Optional Prerequisites (required only if you have multimodal data to offload to GCS):**
*   Cloud Storage API
*   BigQuery Connection API

## Enabling the Plugin

To enable the BigQuery Agent Analytics Plugin, use the `--bq-analytics` flag during project creation:

```bash
uv run agent-starter-pack create your-agent-name \
  -a adk \
  -d cloud_run \
  --bq-analytics \
  --cicd-runner google_cloud_build
  # ... other options
```

This flag does two main things:

1.  Adjusts the Jinja templates to include the plugin initialization code in `app/agent.py` and configure environment variables in Terraform.
2.  Adds the `google-adk[bigquery-analytics]>=1.21.0` dependency to your project.

## Configuration

The plugin is configured within your `app/agent.py` file:

```python
# Example from template
from google.adk.plugins.bigquery_agent_analytics_plugin import (
    BigQueryAgentAnalyticsPlugin,
    BigQueryLoggerConfig,
)

# Configuration for the plugin
bq_config = BigQueryLoggerConfig(
    enabled=True, # Plugin is active
    gcs_bucket_name=os.environ.get("BQ_ANALYTICS_GCS_BUCKET"), # (Optional) For multimodal offloading
    connection_id=os.environ.get("BQ_ANALYTICS_CONNECTION_ID"), # (Optional) For GCS access from BQ
    log_multi_modal_content=True,
    max_content_length=500 * 1024, # Max inline text size before GCS offload
    table_id="agent_events_v2" # Default table name
)

# Plugin instance
bq_analytics_plugin = BigQueryAgentAnalyticsPlugin(
    project_id=os.environ.get("GOOGLE_CLOUD_PROJECT"),
    dataset_id=os.environ.get("BQ_ANALYTICS_DATASET_ID", "adk_agent_analytics"), # Terraform sets this
    table_id=bq_config.table_id,
    config=bq_config,
    location=os.environ.get("GOOGLE_CLOUD_LOCATION", "US"),
)

# Register the plugin with the App
app = App(
    name="{{ cookiecutter.project_name }}",
    root_agent=root_agent,
    plugins=[bq_analytics_plugin],
)
```

**Key `BigQueryLoggerConfig` Options:**

*   `enabled`: Toggles the plugin.
*   `gcs_bucket_name` **(Optional)**: GCS bucket for offloading large/binary content. Set by `BQ_ANALYTICS_GCS_BUCKET` env var from Terraform. Required only if you have multimodal data to offload.
*   `connection_id` **(Optional)**: Fully qualified BigQuery Connection ID (e.g., `us-central1.conn-id`) for GCS access. Set by `BQ_ANALYTICS_CONNECTION_ID` env var from Terraform. Required only if you have multimodal data to offload.
*   `log_multi_modal_content`: Whether to handle content parts and offload to GCS.
*   `max_content_length`: Threshold for offloading text parts to GCS.
*   `table_id`: Name of the BigQuery table to write to (defaults to `agent_events_v2`).
*   `event_allowlist` / `event_denylist`: Filter which event types are logged.
*   `batch_size`: Number of rows to batch before writing to BigQuery.

## Infrastructure

When deployed with Terraform (`make setup-dev-env`):

*   **Dataset:** A BigQuery dataset named `{project_name}_telemetry` is created. The `BQ_ANALYTICS_DATASET_ID` environment variable is set to this ID.
*   **GCS Bucket (Optional):** A bucket named `{project_id}-{project_name}-logs` is created for GCS offloading. The `BQ_ANALYTICS_GCS_BUCKET` env var is set to this name.
*   **BigQuery Connection (Optional):** A connection named `{project_name}-genai-telemetry` is created to allow BigQuery to read from the GCS bucket. The `BQ_ANALYTICS_CONNECTION_ID` env var is set to its fully qualified ID.
*   **Table:** The `agent_events_v2` table is **auto-created** by the plugin within the telemetry dataset on the first event.

## Schema Reference

The schema for the `agent_events_v2` table is maintained by the Agent Development Kit (ADK). To ensure you have the most up-to-date information and maintain a single source of truth, please refer to the [ADK Documentation](https://google.github.io/adk-docs/) for the official schema reference, or view it directly using the BigQuery schema viewer in the Google Cloud Console.

## Example Queries

Replace `YOUR_PROJECT_ID` and `YOUR_AGENT_NAME` accordingly.

**Recent Events:**
```sql
SELECT *
FROM `YOUR_PROJECT_ID.YOUR_AGENT_NAME_telemetry.agent_events_v2`
ORDER BY timestamp DESC
LIMIT 100;
```

**Tool Calls & Errors:**
```sql
SELECT
  timestamp,
  JSON_VALUE(content, '$.tool') AS tool_name,
  JSON_VALUE(content, '$.args') AS tool_args,
  status,
  error_message
FROM `YOUR_PROJECT_ID.YOUR_AGENT_NAME_telemetry.agent_events_v2`
WHERE event_type IN ('TOOL_COMPLETED', 'TOOL_ERROR')
ORDER BY timestamp DESC;
```

**LLM Token Usage:**
```sql
SELECT
  agent,
  JSON_VALUE(attributes, '$.model') AS model,
  SUM(CAST(JSON_VALUE(attributes, '$.usage_metadata.prompt') AS INT64)) AS total_prompt_tokens,
  SUM(CAST(JSON_VALUE(attributes, '$.usage_metadata.completion') AS INT64)) AS total_completion_tokens
FROM `YOUR_PROJECT_ID.YOUR_AGENT_NAME_telemetry.agent_events_v2`
WHERE event_type = 'LLM_RESPONSE'
  AND JSON_VALUE(attributes, '$.usage_metadata.prompt') IS NOT NULL
GROUP BY agent, model;
```

## Looker Studio Dashboard

To visualize your agent analytics, you can use the pre-built Looker Studio dashboard template:

*   **Template Link:** [go/agent-starter-pack-observability-dashboard](http://go/agent-starter-pack-observability-dashboard)
*   **Instructions:**
    1.  Open the link.
    2.  Click "Use Template".
    3.  Select your GCP project and the `YOUR_AGENT_NAME_telemetry` dataset as the data source.
    4.  Map the fields if prompted.
    5.  Explore the visualizations on agent usage, tool calls, token consumption, and errors.
```
