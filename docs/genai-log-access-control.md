# GenAI Telemetry Log Access Control

## Overview

The Agent Starter Pack automatically captures GenAI telemetry events (user messages, system prompts, model completions) to both BigQuery and Cloud Logging. To control who can view these sensitive logs, the Terraform configuration creates a dedicated **log view** that restricts access to GenAI telemetry data.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ _Default Log Bucket (global)                                │
│                                                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Log View: {project-name}-genai-telemetry            │   │
│  │ Filter: logName=~"gen_ai\\." AND                    │   │
│  │         resource.labels.namespace="{project-name}"  │   │
│  │                                                       │   │
│  │ IAM: roles/logging.viewAccessor                     │   │
│  │      → Grant to specific users/groups               │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                               │
│  Default views (_AllLogs, _Default) still show all logs     │
└─────────────────────────────────────────────────────────────┘
```

## Access Control

### Granting Access to GenAI Logs

To grant a user/group access to GenAI telemetry logs, uncomment and modify the IAM binding in `deployment/terraform/log_sinks.tf`:

```terraform
resource "google_logging_log_view_iam_member" "genai_telemetry_viewer" {
  for_each = local.deploy_project_ids
  project  = each.value
  location = "global"
  bucket   = google_logging_project_bucket_config.default_bucket[each.key].bucket_id
  name     = google_logging_log_view.genai_telemetry_view[each.key].name
  role     = "roles/logging.viewAccessor"
  member   = "user:analyst@example.com"  # Change to your user/group
}
```

### Restricting Access (Hiding from Most Users)

**Important:** Log views do NOT restrict users who already have `roles/logging.viewer` or project-level `roles/logging.viewAccessor`. These roles bypass log view restrictions.

To fully restrict GenAI logs from general users, add a log exclusion:

```terraform
resource "google_logging_project_exclusion" "exclude_genai_from_default" {
  for_each = local.deploy_project_ids
  name     = "exclude-genai-telemetry"
  project  = each.value
  filter   = var.telemetry_logs_filter
}
```

With exclusions enabled:
- GenAI logs are **excluded** from default bucket views (_AllLogs, _Default)
- GenAI logs are **still exported** to BigQuery (controlled by dataset IAM)
- Only users with BigQuery `roles/bigquery.dataViewer` can query them

## Resources Created

| Resource | Purpose |
|----------|---------|
| `google_logging_project_bucket_config.default_bucket` | Manages _Default bucket retention (30 days) |
| `google_logging_log_view.genai_telemetry_view` | Filtered view showing only GenAI telemetry logs |
| `google_logging_log_view_iam_member` (optional) | Grants specific users access to the log view |
| `google_logging_project_exclusion` (optional) | Hides GenAI logs from default views |

## Use Cases

### Scenario 1: Data Analysts Need GenAI Logs
Grant `roles/logging.viewAccessor` on the log view resource (not project-level).

### Scenario 2: Hide GenAI Logs from All Users
Enable log exclusion. Logs remain in BigQuery for authorized analysts.

### Scenario 3: Team-Based Access
Create separate log views per team with different filters, grant team-specific IAM bindings.

## Viewing Logs

**Via Logs Explorer:**
1. Go to Logs Explorer → Select scope → **Log view** dropdown
2. Choose `{project-name}-genai-telemetry`
3. View filtered GenAI events (user messages, system prompts, model completions)

**Via BigQuery:**
```sql
SELECT timestamp, jsonPayload.content, resource.labels.namespace
FROM `{project-id}_telemetry.*`
WHERE resource.labels.namespace = "{project-name}"
LIMIT 100
```
