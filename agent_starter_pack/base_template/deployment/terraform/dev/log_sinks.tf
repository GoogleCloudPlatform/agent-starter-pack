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

resource "google_bigquery_dataset" "feedback_dataset" {
  project       = var.dev_project_id
  dataset_id    = replace("${var.project_name}_feedback", "-", "_")
  friendly_name = "${var.project_name}_feedback"
  location      = var.region
  depends_on    = [resource.google_project_service.services]
}

resource "google_bigquery_dataset" "telemetry_logs_dataset" {
  project       = var.dev_project_id
  dataset_id    = replace("${var.project_name}_telemetry", "-", "_")
  friendly_name = "${var.project_name}_telemetry"
  location      = var.region
  depends_on    = [resource.google_project_service.services]
}

resource "google_logging_project_sink" "feedback_export_to_bigquery" {
  name        = "${var.project_name}_feedback"
  project     = var.dev_project_id
  destination = "bigquery.googleapis.com/projects/${var.dev_project_id}/datasets/${google_bigquery_dataset.feedback_dataset.dataset_id}"
  filter      = var.feedback_logs_filter

  bigquery_options {
    use_partitioned_tables = true
  }

  unique_writer_identity = true
  depends_on             = [google_bigquery_dataset.feedback_dataset]
}

resource "google_logging_project_sink" "log_export_to_bigquery" {
  name        = "${var.project_name}_telemetry"
  project     = var.dev_project_id
  destination = "bigquery.googleapis.com/projects/${var.dev_project_id}/datasets/${google_bigquery_dataset.telemetry_logs_dataset.dataset_id}"
  filter      = var.telemetry_logs_filter

  bigquery_options {
    use_partitioned_tables = true
  }

  unique_writer_identity = true
  depends_on             = [google_bigquery_dataset.telemetry_logs_dataset]
}

resource "google_project_iam_member" "bigquery_data_editor" {
  project = var.dev_project_id
  role    = "roles/bigquery.dataEditor"
  member  = google_logging_project_sink.log_export_to_bigquery.writer_identity
}

resource "google_project_iam_member" "feedback_bigquery_data_editor" {
  project = var.dev_project_id
  role    = "roles/bigquery.dataEditor"
  member  = google_logging_project_sink.feedback_export_to_bigquery.writer_identity
}

# Log bucket configuration for the _Default bucket
resource "google_logging_project_bucket_config" "default_bucket" {
  project        = var.dev_project_id
  location       = "global"
  bucket_id      = "_Default"
  retention_days = 30
}

# Log view for GenAI telemetry events
resource "google_logging_log_view" "genai_telemetry_view" {
  name        = "${var.project_name}-genai-telemetry"
  bucket      = google_logging_project_bucket_config.default_bucket.id
  description = "View for GenAI telemetry events (user messages, system prompts, model completions) for ${var.project_name}"
  # Log views use source(), log_id(), and resource.type filters
  # Filter by project and resource type to capture GenAI telemetry logs
  filter      = "source(\"projects/${var.dev_project_id}\") AND resource.type = \"generic_task\""
}

# Example: Grant a user/group access to the GenAI telemetry log view
# Uncomment and modify to grant specific users access to GenAI telemetry logs
#
# resource "google_logging_log_view_iam_member" "genai_telemetry_viewer" {
#   project  = var.dev_project_id
#   location = "global"
#   bucket   = google_logging_project_bucket_config.default_bucket.bucket_id
#   name     = google_logging_log_view.genai_telemetry_view.name
#   role     = "roles/logging.viewAccessor"
#   member   = "user:example@example.com"  # Change to your user/group/service account
# }

# Exclude GenAI logs from default bucket views (_AllLogs, _Default)
# This prevents users with roles/logging.viewer from seeing GenAI telemetry logs
# Logs are still exported to BigQuery for authorized users
resource "google_logging_project_exclusion" "exclude_genai_from_default" {
  count       = var.exclude_genai_logs_from_default_bucket ? 1 : 0
  name        = "${var.project_name}-exclude-genai-telemetry"
  project     = var.dev_project_id
  description = "Exclude GenAI telemetry logs from _Default bucket. Logs are still exported to BigQuery."
  filter      = var.telemetry_logs_filter
}
