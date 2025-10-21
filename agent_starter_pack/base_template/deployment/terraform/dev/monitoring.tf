# Copyright 2025 Google LLC
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


locals {
  monitoring_metric_prefix = replace(var.project_name, "-", "_")
}

# ------------------------------------------------------------------------------
# Universal log-based metrics (all agents, all platforms)
# ------------------------------------------------------------------------------

# Agent operation count - tracks all agent operations
resource "google_logging_metric" "agent_operation_count" {
  project = var.dev_project_id
  name    = "${local.monitoring_metric_prefix}_agent_operation_count"

  filter = <<-EOT
    labels.service_name="${var.project_name}"
    labels.type="agent_telemetry"
    jsonPayload.attributes.agent_operation_type:*
  EOT

  metric_descriptor {
    metric_kind  = "DELTA"
    value_type   = "INT64"
    unit         = "1"
    display_name = "${var.project_name} operation count"

    labels {
      key         = "operation_type"
      value_type  = "STRING"
      description = "Agent operation type"
    }
  }

  label_extractors = {
    "operation_type" = "EXTRACT(jsonPayload.attributes.agent_operation_type)"
  }

  depends_on = [resource.google_project_service.services]
}

# Agent error count with categorization - tracks errors by category
resource "google_logging_metric" "agent_error_categorized" {
  project = var.dev_project_id
  name    = "${local.monitoring_metric_prefix}_agent_error_categorized"

  filter = <<-EOT
    labels.service_name="${var.project_name}"
    labels.type="agent_telemetry"
    jsonPayload.attributes.agent_error_category:*
  EOT

  metric_descriptor {
    metric_kind  = "DELTA"
    value_type   = "INT64"
    unit         = "1"
    display_name = "${var.project_name} error count by category"

    labels {
      key         = "error_category"
      value_type  = "STRING"
      description = "Agent error category (LLM_FAILURE, TOOL_FAILURE, RETRIEVER_FAILURE, etc.)"
    }
  }

  label_extractors = {
    "error_category" = "EXTRACT(jsonPayload.attributes.agent_error_category)"
  }

  depends_on = [resource.google_project_service.services]
}

{% if cookiecutter.agent_name == 'agentic_rag' %}
# ------------------------------------------------------------------------------
# Retriever-specific metrics (Agentic RAG agents only)
# ------------------------------------------------------------------------------

# Retriever latency metric - P50/P95/P99 retrieval performance
resource "google_logging_metric" "agent_retriever_latency" {
  project = var.dev_project_id
  name    = "${local.monitoring_metric_prefix}_agent_retriever_latency_ms"

  filter = <<-EOT
    labels.service_name="${var.project_name}"
    labels.type="agent_telemetry"
    jsonPayload.attributes.agent_retriever_latency_ms:*
  EOT

  metric_descriptor {
    metric_kind  = "DELTA"
    value_type   = "DISTRIBUTION"
    unit         = "ms"
    display_name = "${var.project_name} retriever latency"

    labels {
      key         = "operation_type"
      value_type  = "STRING"
      description = "Agent operation type"
    }
  }

  value_extractor = "EXTRACT(jsonPayload.attributes.agent_retriever_latency_ms)"

  bucket_options {
    explicit_buckets {
      bounds = [0, 10, 50, 100, 250, 500, 1000, 2000, 5000, 10000]
    }
  }

  label_extractors = {
    "operation_type" = "EXTRACT(jsonPayload.attributes.agent_operation_type)"
  }

  depends_on = [resource.google_project_service.services]
}

# Retriever document count metric - tracks number of documents retrieved
resource "google_logging_metric" "agent_retriever_document_count" {
  project = var.dev_project_id
  name    = "${local.monitoring_metric_prefix}_agent_retriever_document_count"

  filter = <<-EOT
    labels.service_name="${var.project_name}"
    labels.type="agent_telemetry"
    jsonPayload.attributes.agent_retriever_document_count:*
  EOT

  metric_descriptor {
    metric_kind  = "DELTA"
    value_type   = "DISTRIBUTION"
    unit         = "1"
    display_name = "${var.project_name} retriever document count"

    labels {
      key         = "operation_type"
      value_type  = "STRING"
      description = "Agent operation type"
    }
  }

  value_extractor = "EXTRACT(jsonPayload.attributes.agent_retriever_document_count)"

  bucket_options {
    explicit_buckets {
      bounds = [0, 1, 5, 10, 20, 50, 100]
    }
  }

  label_extractors = {
    "operation_type" = "EXTRACT(jsonPayload.attributes.agent_operation_type)"
  }

  depends_on = [resource.google_project_service.services]
}

# Alert when retriever latency P99 exceeds threshold
resource "google_monitoring_alert_policy" "agent_retriever_latency_high" {
  project      = var.dev_project_id
  display_name = "${var.project_name} - High Retriever Latency (P99 > ${var.retriever_latency_p99_threshold_ms}ms)"

  combiner = "OR"

  conditions {
    display_name = "Retriever latency P99 > ${var.retriever_latency_p99_threshold_ms}ms (5 minute window)"

    condition_monitoring_query_language {
      query = <<-EOT
fetch global
| metric 'logging.googleapis.com/user/${local.monitoring_metric_prefix}_agent_retriever_latency_ms'
| align delta(5m)
| group_by [], [value_percentile: percentile(value, 99)]
| condition value_percentile > cast_units(${var.retriever_latency_p99_threshold_ms}, "ms")
EOT
      duration = "0s"
      trigger {
        count = 1
      }
    }
  }

  notification_channels = var.alert_notification_email != "" ? [google_monitoring_notification_channel.email[0].id] : []

  alert_strategy {
    auto_close = "1800s"
  }

  documentation {
    content   = "Retriever latency P99 for ${var.project_name} exceeded ${var.retriever_latency_p99_threshold_ms}ms. Check retriever spans in Cloud Trace for slow queries or large document retrievals."
    mime_type = "text/markdown"
  }

  depends_on = [
    google_logging_metric.agent_retriever_latency,
    resource.google_project_service.services
  ]
}
{% endif %}

{% if cookiecutter.deployment_target == 'agent_engine' %}
# ------------------------------------------------------------------------------
# Agent Engine (Reasoning Engine) Platform Metrics & Dashboard
# ------------------------------------------------------------------------------

# Alert on high P95 latency (native Reasoning Engine metric)
resource "google_monitoring_alert_policy" "high_latency" {
  project      = var.dev_project_id
  display_name = "${var.project_name} - High P95 Latency"

  combiner = "OR"

  conditions {
    display_name = "P95 latency > ${var.latency_alert_threshold_ms}ms"

    condition_threshold {
      filter = <<-EOT
        resource.type = "aiplatform.googleapis.com/ReasoningEngine"
        metric.type = "aiplatform.googleapis.com/reasoning_engine/request_latencies"
      EOT

      duration   = "60s"
      comparison = "COMPARISON_GT"

      threshold_value = var.latency_alert_threshold_ms

      aggregations {
        alignment_period     = "300s"
        per_series_aligner   = "ALIGN_DELTA"
        cross_series_reducer = "REDUCE_PERCENTILE_95"
        group_by_fields      = ["resource.reasoning_engine_id"]
      }
    }
  }

  notification_channels = var.alert_notification_email != "" ? [google_monitoring_notification_channel.email[0].id] : []

  alert_strategy {
    auto_close = "1800s"
  }

  documentation {
    content   = "P95 request latency for ${var.project_name} agent has exceeded ${var.latency_alert_threshold_ms}ms. This means 5% of requests are taking longer than this threshold."
    mime_type = "text/markdown"
  }

  depends_on = [resource.google_project_service.services]
}

# Alert on high error rate (log-based metric)
resource "google_monitoring_alert_policy" "high_error_rate" {
  project      = var.dev_project_id
  display_name = "${var.project_name} - High Error Rate"

  combiner = "OR"

  conditions {
    display_name = "Error count > ${var.error_rate_alert_threshold} in 5min"

    condition_threshold {
      filter = <<-EOT
        resource.type = "global"
        metric.type = "logging.googleapis.com/user/${local.monitoring_metric_prefix}_agent_error_categorized"
      EOT

      duration   = "0s"
      comparison = "COMPARISON_GT"

      threshold_value = var.error_rate_alert_threshold

      aggregations {
        alignment_period   = "300s"
        per_series_aligner = "ALIGN_SUM"
        cross_series_reducer = "REDUCE_SUM"
        group_by_fields      = []
      }
    }
  }

  notification_channels = var.alert_notification_email != "" ? [google_monitoring_notification_channel.email[0].id] : []

  alert_strategy {
    auto_close = "1800s"
  }

  documentation {
    content   = "Error rate for ${var.project_name} agent exceeded ${var.error_rate_alert_threshold} errors in the past five minutes. Check logs for error details."
    mime_type = "text/markdown"
  }

  depends_on = [google_logging_metric.agent_error_categorized, resource.google_project_service.services]
}

# Monitoring dashboard for Agent Engine
resource "google_monitoring_dashboard" "reasoning_engine_observability" {
  project        = var.dev_project_id
  dashboard_json = jsonencode({
    displayName = "Reasoning Engine - ${var.project_name}"
    mosaicLayout = {
      columns = 12
      tiles = concat([
        # Chart 1: Request Count
        {
          width  = 6
          height = 4
          widget = {
            title = "Request Count"
            xyChart = {
              dataSets = [{
                timeSeriesQuery = {
                  timeSeriesFilter = {
                    filter = "resource.type=\"aiplatform.googleapis.com/ReasoningEngine\" metric.type=\"aiplatform.googleapis.com/reasoning_engine/request_count\""
                    aggregation = {
                      alignmentPeriod    = "60s"
                      perSeriesAligner   = "ALIGN_RATE"
                      crossSeriesReducer = "REDUCE_SUM"
                      groupByFields      = ["resource.reasoning_engine_id"]
                    }
                  }
                }
                plotType         = "LINE"
                targetAxis       = "Y1"
                legendTemplate   = "Requests/sec"
              }]
              yAxis = {
                label = "requests/sec"
                scale = "LINEAR"
              }
            }
          }
        },
        # Chart 2: Request Latency (P50/P95/P99)
        {
          xPos   = 6
          width  = 6
          height = 4
          widget = {
            title = "Request Latency (P50/P95/P99)"
            xyChart = {
              dataSets = [
                {
                  timeSeriesQuery = {
                    timeSeriesFilter = {
                      filter = "resource.type=\"aiplatform.googleapis.com/ReasoningEngine\" metric.type=\"aiplatform.googleapis.com/reasoning_engine/request_latencies\""
                      aggregation = {
                        alignmentPeriod    = "60s"
                        perSeriesAligner   = "ALIGN_DELTA"
                        crossSeriesReducer = "REDUCE_PERCENTILE_50"
                        groupByFields      = ["resource.reasoning_engine_id"]
                      }
                    }
                  }
                  plotType         = "LINE"
                  targetAxis       = "Y1"
                  legendTemplate   = "P50"
                },
                {
                  timeSeriesQuery = {
                    timeSeriesFilter = {
                      filter = "resource.type=\"aiplatform.googleapis.com/ReasoningEngine\" metric.type=\"aiplatform.googleapis.com/reasoning_engine/request_latencies\""
                      aggregation = {
                        alignmentPeriod    = "60s"
                        perSeriesAligner   = "ALIGN_DELTA"
                        crossSeriesReducer = "REDUCE_PERCENTILE_95"
                        groupByFields      = ["resource.reasoning_engine_id"]
                      }
                    }
                  }
                  plotType         = "LINE"
                  targetAxis       = "Y1"
                  legendTemplate   = "P95"
                },
                {
                  timeSeriesQuery = {
                    timeSeriesFilter = {
                      filter = "resource.type=\"aiplatform.googleapis.com/ReasoningEngine\" metric.type=\"aiplatform.googleapis.com/reasoning_engine/request_latencies\""
                      aggregation = {
                        alignmentPeriod    = "60s"
                        perSeriesAligner   = "ALIGN_DELTA"
                        crossSeriesReducer = "REDUCE_PERCENTILE_99"
                        groupByFields      = ["resource.reasoning_engine_id"]
                      }
                    }
                  }
                  plotType         = "LINE"
                  targetAxis       = "Y1"
                  legendTemplate   = "P99"
                }
              ]
              yAxis = {
                label = "milliseconds"
                scale = "LINEAR"
              }
            }
          }
        },
        # Chart 3: CPU Allocation
        {
          yPos   = 4
          width  = 6
          height = 4
          widget = {
            title = "CPU Allocation"
            xyChart = {
              dataSets = [{
                timeSeriesQuery = {
                  timeSeriesFilter = {
                    filter = "resource.type=\"aiplatform.googleapis.com/ReasoningEngine\" metric.type=\"aiplatform.googleapis.com/reasoning_engine/cpu/allocation_time\""
                    aggregation = {
                      alignmentPeriod    = "60s"
                      perSeriesAligner   = "ALIGN_RATE"
                      crossSeriesReducer = "REDUCE_SUM"
                      groupByFields      = ["resource.reasoning_engine_id"]
                    }
                  }
                }
                plotType         = "LINE"
                targetAxis       = "Y1"
                legendTemplate   = "CPU seconds"
              }]
              yAxis = {
                label = "CPU seconds/sec"
                scale = "LINEAR"
              }
            }
          }
        },
        # Chart 4: Memory Allocation
        {
          xPos   = 6
          yPos   = 4
          width  = 6
          height = 4
          widget = {
            title = "Memory Allocation"
            xyChart = {
              dataSets = [{
                timeSeriesQuery = {
                  timeSeriesFilter = {
                    filter = "resource.type=\"aiplatform.googleapis.com/ReasoningEngine\" metric.type=\"aiplatform.googleapis.com/reasoning_engine/memory/allocation_time\""
                    aggregation = {
                      alignmentPeriod    = "60s"
                      perSeriesAligner   = "ALIGN_RATE"
                      crossSeriesReducer = "REDUCE_SUM"
                      groupByFields      = ["resource.reasoning_engine_id"]
                    }
                  }
                }
                plotType         = "LINE"
                targetAxis       = "Y1"
                legendTemplate   = "GiBy-sec"
              }]
              yAxis = {
                label = "GiBy-sec/sec"
                scale = "LINEAR"
              }
            }
          }
        },
        # Chart 5: Agent Errors by Category
        {
          yPos   = 8
          width  = 12
          height = 4
          widget = {
            title = "Agent Errors by Category"
            xyChart = {
              dataSets = [{
                timeSeriesQuery = {
                  timeSeriesFilter = {
                    filter = "resource.type=\"global\" metric.type=\"logging.googleapis.com/user/${local.monitoring_metric_prefix}_agent_error_categorized\""
                    aggregation = {
                      alignmentPeriod    = "60s"
                      perSeriesAligner   = "ALIGN_RATE"
                      crossSeriesReducer = "REDUCE_SUM"
                      groupByFields      = ["metric.label.error_category"]
                    }
                  }
                }
                plotType         = "STACKED_AREA"
                targetAxis       = "Y1"
                legendTemplate   = "$${metric.label.error_category}"
              }]
              yAxis = {
                label = "errors/sec"
                scale = "LINEAR"
              }
            }
          }
        }
      ],
{% if cookiecutter.agent_name == 'agentic_rag' %}
      # Additional retriever charts for Agentic RAG
      [
        # Chart 6: Agent Retriever Latency (P50/P95/P99)
        {
          yPos   = 12
          width  = 12
          height = 4
          widget = {
            title = "Agent Retriever Latency (P50/P95/P99)"
            xyChart = {
              dataSets = [
                {
                  timeSeriesQuery = {
                    timeSeriesFilter = {
                      filter = "resource.type=\"global\" metric.type=\"logging.googleapis.com/user/${local.monitoring_metric_prefix}_agent_retriever_latency_ms\""
                      aggregation = {
                        alignmentPeriod    = "60s"
                        perSeriesAligner   = "ALIGN_DELTA"
                        crossSeriesReducer = "REDUCE_PERCENTILE_50"
                      }
                    }
                  }
                  plotType         = "LINE"
                  targetAxis       = "Y1"
                  legendTemplate   = "P50"
                },
                {
                  timeSeriesQuery = {
                    timeSeriesFilter = {
                      filter = "resource.type=\"global\" metric.type=\"logging.googleapis.com/user/${local.monitoring_metric_prefix}_agent_retriever_latency_ms\""
                      aggregation = {
                        alignmentPeriod    = "60s"
                        perSeriesAligner   = "ALIGN_DELTA"
                        crossSeriesReducer = "REDUCE_PERCENTILE_95"
                      }
                    }
                  }
                  plotType         = "LINE"
                  targetAxis       = "Y1"
                  legendTemplate   = "P95"
                },
                {
                  timeSeriesQuery = {
                    timeSeriesFilter = {
                      filter = "resource.type=\"global\" metric.type=\"logging.googleapis.com/user/${local.monitoring_metric_prefix}_agent_retriever_latency_ms\""
                      aggregation = {
                        alignmentPeriod    = "60s"
                        perSeriesAligner   = "ALIGN_DELTA"
                        crossSeriesReducer = "REDUCE_PERCENTILE_99"
                      }
                    }
                  }
                  plotType         = "LINE"
                  targetAxis       = "Y1"
                  legendTemplate   = "P99"
                }
              ]
              yAxis = {
                label = "milliseconds"
                scale = "LINEAR"
              }
            }
          }
        },
        # Chart 7: Documents Retrieved per Call
        {
          yPos   = 16
          width  = 6
          height = 4
          widget = {
            title = "Documents Retrieved per Call"
            xyChart = {
              dataSets = [{
                timeSeriesQuery = {
                  timeSeriesFilter = {
                    filter = "resource.type=\"global\" metric.type=\"logging.googleapis.com/user/${local.monitoring_metric_prefix}_agent_retriever_document_count\""
                    aggregation = {
                      alignmentPeriod    = "60s"
                      perSeriesAligner   = "ALIGN_DELTA"
                      crossSeriesReducer = "REDUCE_PERCENTILE_50"
                    }
                  }
                }
                plotType         = "LINE"
                targetAxis       = "Y1"
                legendTemplate   = "Median docs"
              }]
              yAxis = {
                label = "documents"
                scale = "LINEAR"
              }
            }
          }
        }
      ]
{% else %}
      []
{% endif %}
      )
    }
  })

  depends_on = [
    google_logging_metric.agent_error_categorized,
    resource.google_project_service.services
  ]
}
{% endif %}

{% if cookiecutter.deployment_target == 'cloud_run' %}
# ------------------------------------------------------------------------------
# Cloud Run Platform Alerts
# ------------------------------------------------------------------------------

# Alert on high P95 latency (Cloud Run native metric)
resource "google_monitoring_alert_policy" "high_latency_cloud_run" {
  project      = var.dev_project_id
  display_name = "${var.project_name} - High P95 Latency (Cloud Run)"

  combiner = "OR"

  conditions {
    display_name = "P95 latency > ${var.latency_alert_threshold_ms}ms"

    condition_threshold {
      filter = "resource.type=\"cloud_run_revision\" AND metric.type=\"run.googleapis.com/request_latencies\" AND resource.label.service_name=\"${var.project_name}\""

      aggregations {
        alignment_period     = "300s"
        per_series_aligner   = "ALIGN_DELTA"
        cross_series_reducer = "REDUCE_PERCENTILE_95"
        group_by_fields      = ["resource.service_name"]
      }

      comparison      = "COMPARISON_GT"
      threshold_value = var.latency_alert_threshold_ms
      duration        = "60s"
    }
  }

  notification_channels = var.alert_notification_email != "" ? [google_monitoring_notification_channel.email[0].id] : []

  alert_strategy {
    auto_close = "1800s"
  }

  documentation {
    content   = "P95 request latency for ${var.project_name} (Cloud Run) exceeded ${var.latency_alert_threshold_ms}ms. Check Cloud Run metrics and logs for slow requests."
    mime_type = "text/markdown"
  }

  depends_on = [resource.google_project_service.services]
}

# Alert on high error rate (5xx responses from Cloud Run)
resource "google_monitoring_alert_policy" "high_error_rate_cloud_run" {
  project      = var.dev_project_id
  display_name = "${var.project_name} - High Error Rate (Cloud Run)"

  combiner = "OR"

  conditions {
    display_name = "5xx error count > ${var.error_rate_alert_threshold} in 5min"

    condition_threshold {
      filter = "resource.type=\"cloud_run_revision\" AND metric.type=\"run.googleapis.com/request_count\" AND metric.label.response_code_class=\"5xx\" AND resource.label.service_name=\"${var.project_name}\""

      # Note: Using ALIGN_SUM to count total errors in the 300s window.
      # Do not use ALIGN_RATE here as it would convert to errors/second.
      aggregations {
        alignment_period   = "300s"
        per_series_aligner = "ALIGN_SUM"
      }

      comparison      = "COMPARISON_GT"
      threshold_value = var.error_rate_alert_threshold
      duration        = "0s"
    }
  }

  notification_channels = var.alert_notification_email != "" ? [google_monitoring_notification_channel.email[0].id] : []

  alert_strategy {
    auto_close = "1800s"
  }

  documentation {
    content   = "5xx error count for ${var.project_name} (Cloud Run) exceeded ${var.error_rate_alert_threshold} errors in the past five minutes. Check Cloud Run logs for error details."
    mime_type = "text/markdown"
  }

  depends_on = [resource.google_project_service.services]
}

# Alert when agent errors occur (log-based)
resource "google_monitoring_alert_policy" "agent_errors" {
  project      = var.dev_project_id
  display_name = "${var.project_name} - Agent Errors Detected"

  combiner = "OR"

  conditions {
    display_name = "Agent error count > ${var.agent_error_rate_threshold_per_sec}/sec"

    condition_threshold {
      filter = "resource.type=\"global\" AND metric.type=\"logging.googleapis.com/user/${local.monitoring_metric_prefix}_agent_error_categorized\""

      aggregations {
        alignment_period   = "300s"
        per_series_aligner = "ALIGN_RATE"
      }

      comparison      = "COMPARISON_GT"
      threshold_value = var.agent_error_rate_threshold_per_sec
      duration        = "0s"
    }
  }

  notification_channels = var.alert_notification_email != "" ? [google_monitoring_notification_channel.email[0].id] : []

  alert_strategy {
    auto_close = "1800s"
  }

  documentation {
    content   = "Agent errors detected for ${var.project_name}. Check logs filtered by labels.service_name=${var.project_name} and agent.error.category to identify error types."
    mime_type = "text/markdown"
  }

  depends_on = [
    google_logging_metric.agent_error_categorized,
    resource.google_project_service.services
  ]
}
{% endif %}

# ------------------------------------------------------------------------------
# Notification channel (universal)
# ------------------------------------------------------------------------------

resource "google_monitoring_notification_channel" "email" {
  count        = var.alert_notification_email != "" ? 1 : 0
  project      = var.dev_project_id
  display_name = "${var.project_name} Alert Email"
  type         = "email"

  labels = {
    email_address = var.alert_notification_email
  }

  enabled    = true
  depends_on = [resource.google_project_service.services]
}
