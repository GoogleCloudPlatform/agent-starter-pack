# Project name used for resource naming
project_name = "{{ cookiecutter.project_name | replace('_', '-') }}"

# Your Dev Google Cloud project id
dev_project_id = "your-dev-project-id"

# The Google Cloud region you will use to deploy the infrastructure
region = "us-central1"

{%- if cookiecutter.data_ingestion %}
{%- if cookiecutter.datastore_type == "vertex_ai_search" %}
# The value can only be one of "global", "us" and "eu".
data_store_region = "us"
{%- elif cookiecutter.datastore_type == "vertex_ai_vector_search" %}
vector_search_shard_size = "SHARD_SIZE_SMALL"
vector_search_machine_type = "e2-standard-2"
vector_search_min_replica_count = 1
vector_search_max_replica_count = 1
{%- endif %}
{%- endif %}

# ------------------------------------------------------------------------------
# Monitoring and Alerting Configuration
# ------------------------------------------------------------------------------

# Email address for alert notifications (leave empty for console-only alerts)
alert_notification_email = "{{ cookiecutter.alert_notification_email }}"

# Alert thresholds (uncomment to override defaults)
# latency_alert_threshold_ms = 3000           # P95 latency threshold in milliseconds
# error_rate_alert_threshold = 10             # Error count per 5-minute window
# retriever_latency_p99_threshold_ms = 10000  # P99 retriever latency in milliseconds
# agent_error_rate_threshold_per_sec = 0.5    # Agent error rate threshold (errors/sec)
