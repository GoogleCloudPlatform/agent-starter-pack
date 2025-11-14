# GenAI Telemetry Log Access Control

## Overview

The Agent Starter Pack automatically captures GenAI telemetry events (user messages, system prompts, model completions) to both BigQuery and Cloud Logging. To control who can view these sensitive logs, the Terraform configuration creates a dedicated **log view** that restricts access to GenAI telemetry data.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ Custom Log Bucket: {project-name}-genai-telemetry           │
│                                                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Log View: {project-name}-genai-telemetry            │   │
│  │ Filter: source("projects/{project-id}")             │   │
│  │ (Bucket already filtered by sink)                   │   │
│  │                                                       │   │
│  │ IAM: roles/logging.viewAccessor                     │   │
│  │      → Grant to specific users/groups               │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                               │
│  GenAI logs routed here via log sink with exclusion         │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ _Default Log Bucket (global)                                │
│                                                               │
│  All logs EXCEPT GenAI telemetry (excluded by sink)         │
│  Users with roles/logging.viewer can see these logs         │
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
  bucket   = google_logging_project_bucket_config.genai_telemetry_bucket[each.key].bucket_id
  name     = google_logging_log_view.genai_telemetry_view[each.key].name
  role     = "roles/logging.viewAccessor"
  member   = "user:analyst@example.com"  # Change to your user/group
}
```

### Restricting Access (Hiding from Most Users)

**Solution:** GenAI logs are automatically routed to a **separate custom log bucket** and excluded from the _Default bucket.

This approach:
- GenAI logs go to `{project-name}-genai-telemetry` bucket (not _Default)
- Users with `roles/logging.viewer` **cannot** see GenAI logs (they're not in _Default bucket)
- GenAI logs are **still exported** to BigQuery (controlled by dataset IAM)
- Only users with `roles/logging.viewAccessor` on the log view OR BigQuery access can see them

GenAI logs are excluded from _Default bucket using a project-level exclusion:

```terraform
# Sink routes GenAI logs to custom bucket
resource "google_logging_project_sink" "genai_to_custom_bucket" {
  destination = "logging.googleapis.com/...genai-telemetry"
  filter      = var.telemetry_logs_filter
}

# Project-level exclusion prevents GenAI logs from _Default bucket
resource "google_logging_project_exclusion" "exclude_genai_from_default" {
  name        = "${var.project_name}-exclude-genai-from-default"
  description = "Exclude GenAI telemetry logs from _Default bucket. Logs are routed to custom bucket instead."
  filter      = var.telemetry_logs_filter
}
```

## Resources Created

| Resource | Purpose |
|----------|---------|
| `google_logging_project_bucket_config.genai_telemetry_bucket` | Custom log bucket for GenAI logs (30 day retention) |
| `google_logging_project_sink.genai_to_custom_bucket` | Routes GenAI logs to custom bucket |
| `google_logging_project_exclusion.exclude_genai_from_default` | Prevents GenAI logs from going to _Default bucket |
| `google_logging_log_view.genai_telemetry_view` | View on custom bucket showing GenAI telemetry logs |
| `google_logging_log_view_iam_member` (optional) | Grants specific users access to the log view |

## Use Cases

### Scenario 1: Data Analysts Need GenAI Logs
Grant `roles/logging.viewAccessor` on the log view resource (not project-level) OR grant BigQuery access.

### Scenario 2: Hide GenAI Logs from Most Users (Default)
GenAI logs are automatically in a separate bucket. Users with `roles/logging.viewer` won't see them.

### Scenario 3: Team-Based Access
Create separate log views on the custom bucket with different filters, grant team-specific IAM bindings.

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
