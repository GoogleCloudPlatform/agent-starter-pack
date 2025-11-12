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

# BigQuery dataset for telemetry external tables
resource "google_bigquery_dataset" "telemetry_dataset" {
  for_each      = local.deploy_project_ids
  project       = each.value
  dataset_id    = replace("${var.project_name}_telemetry", "-", "_")
  friendly_name = "${var.project_name} Telemetry"
  location      = var.region
  description   = "Dataset for GenAI telemetry data stored in GCS"
  depends_on    = [resource.google_project_service.cicd_services, resource.google_project_service.deploy_project_services]
}

# BigQuery connection for accessing GCS telemetry data
resource "google_bigquery_connection" "genai_telemetry_connection" {
  for_each      = local.deploy_project_ids
  project       = each.value
  location      = var.region
  connection_id = "${var.project_name}-genai-telemetry"
  friendly_name = "${var.project_name} GenAI Telemetry Connection"

  cloud_resource {}

  depends_on = [resource.google_project_service.cicd_services, resource.google_project_service.deploy_project_services]
}

# Wait for the BigQuery connection service account to propagate in IAM
resource "time_sleep" "wait_for_bq_connection_sa" {
  for_each = local.deploy_project_ids

  create_duration = "10s"

  depends_on = [google_bigquery_connection.genai_telemetry_connection]
}

# Grant the BigQuery connection service account access to read from the logs bucket
resource "google_storage_bucket_iam_member" "telemetry_connection_access" {
  for_each = local.deploy_project_ids
  bucket   = google_storage_bucket.logs_data_bucket[each.value].name
  role     = "roles/storage.objectViewer"
  member   = "serviceAccount:${google_bigquery_connection.genai_telemetry_connection[each.key].cloud_resource[0].service_account_id}"

  depends_on = [time_sleep.wait_for_bq_connection_sa]
}

# External table for GenAI telemetry JSONL files
resource "google_bigquery_table" "genai_telemetry_external" {
  for_each   = local.deploy_project_ids
  project    = each.value
  dataset_id = google_bigquery_dataset.telemetry_dataset[each.key].dataset_id
  table_id   = "genai_telemetry_raw"

  schema = jsonencode([
    { name = "timestamp", type = "TIMESTAMP", mode = "NULLABLE" },
    { name = "name", type = "STRING", mode = "NULLABLE" },
    { name = "kind", type = "STRING", mode = "NULLABLE" },
    { name = "trace_id", type = "STRING", mode = "NULLABLE" },
    { name = "span_id", type = "STRING", mode = "NULLABLE" },
    { name = "parent_span_id", type = "STRING", mode = "NULLABLE" },
    { name = "resource", type = "JSON", mode = "NULLABLE" },
    { name = "attributes", type = "JSON", mode = "NULLABLE" }
  ])

  external_data_configuration {
    autodetect            = false
    ignore_unknown_values = true
    source_format         = "NEWLINE_DELIMITED_JSON"
    connection_id         = google_bigquery_connection.genai_telemetry_connection[each.key].name

    source_uris = [
      "gs://${google_storage_bucket.logs_data_bucket[each.value].name}/genai-telemetry/*"
    ]
  }

  depends_on = [
    google_storage_bucket.logs_data_bucket,
    google_bigquery_connection.genai_telemetry_connection,
    google_storage_bucket_iam_member.telemetry_connection_access
  ]
}

# # View on top of log sink table for easier querying
# resource "google_bigquery_table" "genai_telemetry_view" {
#   for_each   = local.deploy_project_ids
#   project    = each.value
#   dataset_id = google_bigquery_dataset.telemetry_dataset[each.key].dataset_id
#   table_id   = "genai_telemetry"
#
#   view {
#     query = <<-SQL
#       SELECT
#         timestamp,
#         insert_id,
#         labels,
#         trace,
#         span_id,
#         log_name,
#         STRING(labels.gen_ai_input_messages_ref) AS messages_ref_uri,
#         STRING(labels.gen_ai_output_message_ref) AS output_ref_uri
#       FROM `${each.value}.${google_bigquery_dataset.telemetry_dataset[each.key].dataset_id}._AllLogs`
#       WHERE log_name = 'projects/${each.value}/logs/gen_ai.client.inference.operation.details'
#     SQL
#     use_legacy_sql = false
#   }
#
#   depends_on = [google_logging_project_sink.genai_logs_to_bigquery]
# }

# Log sink for Gen AI operation logs from Cloud Logging
resource "google_logging_project_sink" "genai_logs_to_bigquery" {
  for_each    = local.deploy_project_ids
  name        = "${var.project_name}-genai-logs"
  project     = each.value
  destination = "bigquery.googleapis.com/projects/${each.value}/datasets/${google_bigquery_dataset.telemetry_dataset[each.key].dataset_id}"
  filter      = "log_name=\"projects/${each.value}/logs/gen_ai.client.inference.operation.details\" AND resource.labels.service_namespace=\"${var.project_name}\""

  bigquery_options {
    use_partitioned_tables = true
  }

  unique_writer_identity = true
  depends_on             = [google_bigquery_dataset.telemetry_dataset]
}

# Grant log sink service account permission to write to BigQuery
resource "google_project_iam_member" "genai_logs_bigquery_writer" {
  for_each = local.deploy_project_ids
  project  = each.value
  role     = "roles/bigquery.dataEditor"
  member   = google_logging_project_sink.genai_logs_to_bigquery[each.key].writer_identity
}

# Feedback dataset for user feedback logs
resource "google_bigquery_dataset" "feedback_dataset" {
  for_each      = local.deploy_project_ids
  project       = each.value
  dataset_id    = replace("${var.project_name}_feedback", "-", "_")
  friendly_name = "${var.project_name} Feedback"
  location      = var.region
  description   = "Dataset for user feedback data from Cloud Logging"
  depends_on    = [resource.google_project_service.cicd_services, resource.google_project_service.deploy_project_services]
}

# Log sink for user feedback logs
resource "google_logging_project_sink" "feedback_logs_to_bigquery" {
  for_each    = local.deploy_project_ids
  name        = "${var.project_name}-feedback"
  project     = each.value
  destination = "bigquery.googleapis.com/projects/${each.value}/datasets/${google_bigquery_dataset.feedback_dataset[each.key].dataset_id}"
  filter      = var.feedback_logs_filter

  bigquery_options {
    use_partitioned_tables = true
  }

  unique_writer_identity = true
  depends_on             = [google_bigquery_dataset.feedback_dataset]
}

# Grant feedback log sink service account permission to write to BigQuery
resource "google_project_iam_member" "feedback_logs_bigquery_writer" {
  for_each = local.deploy_project_ids
  project  = each.value
  role     = "roles/bigquery.dataEditor"
  member   = google_logging_project_sink.feedback_logs_to_bigquery[each.key].writer_identity
}
