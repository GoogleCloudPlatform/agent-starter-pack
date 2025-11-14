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
  for_each      = local.deploy_project_ids
  project       = each.value
  dataset_id    = replace("${var.project_name}_feedback", "-", "_")
  friendly_name = "${var.project_name}_feedback"
  location      = var.region
  depends_on    = [resource.google_project_service.cicd_services, resource.google_project_service.deploy_project_services]
}

resource "google_bigquery_dataset" "telemetry_logs_dataset" {
  for_each      = local.deploy_project_ids
  project       = each.value
  dataset_id    = replace("${var.project_name}_telemetry", "-", "_")
  friendly_name = "${var.project_name}_telemetry"
  location      = var.region
  depends_on    = [resource.google_project_service.cicd_services, resource.google_project_service.deploy_project_services]
}

resource "google_logging_project_sink" "feedback_export_to_bigquery" {
  for_each = local.deploy_project_ids

  name        = "${var.project_name}_feedback"
  project     = each.value
  destination = "bigquery.googleapis.com/projects/${each.value}/datasets/${google_bigquery_dataset.feedback_dataset[each.key].dataset_id}"
  filter      = var.feedback_logs_filter

  bigquery_options {
    use_partitioned_tables = true
  }

  unique_writer_identity = true
  depends_on             = [google_bigquery_dataset.feedback_dataset]
}

resource "google_logging_project_sink" "log_export_to_bigquery" {
  for_each = local.deploy_project_ids

  name        = "${var.project_name}_telemetry"
  project     = each.value
  destination = "bigquery.googleapis.com/projects/${each.value}/datasets/${google_bigquery_dataset.telemetry_logs_dataset[each.key].dataset_id}"
  filter      = var.telemetry_logs_filter

  bigquery_options {
    use_partitioned_tables = true
  }

  unique_writer_identity = true
  depends_on             = [google_bigquery_dataset.telemetry_logs_dataset]
}

resource "google_project_iam_member" "bigquery_data_editor" {
  for_each = local.deploy_project_ids

  project = each.value
  role    = "roles/bigquery.dataEditor"
  member  = google_logging_project_sink.log_export_to_bigquery[each.key].writer_identity
}

resource "google_project_iam_member" "feedback_bigquery_data_editor" {
  for_each = local.deploy_project_ids

  project = each.value
  role    = "roles/bigquery.dataEditor"
  member  = google_logging_project_sink.feedback_export_to_bigquery[each.key].writer_identity
}

# Custom log bucket for GenAI telemetry logs
resource "google_logging_project_bucket_config" "genai_telemetry_bucket" {
  for_each       = local.deploy_project_ids
  project        = each.value
  location       = "global"
  bucket_id      = "${var.project_name}-genai-telemetry"
  retention_days = 30
  description    = "Log bucket for GenAI telemetry events with restricted access"
}

# Sink to route GenAI logs to the custom bucket
resource "google_logging_project_sink" "genai_to_custom_bucket" {
  for_each    = local.deploy_project_ids
  name        = "${var.project_name}-genai-to-bucket"
  project     = each.value
  destination = "logging.googleapis.com/${google_logging_project_bucket_config.genai_telemetry_bucket[each.key].id}"
  filter      = var.telemetry_logs_filter
}

# Project-level exclusion to prevent GenAI logs from going to _Default bucket
resource "google_logging_project_exclusion" "exclude_genai_from_default" {
  for_each    = local.deploy_project_ids
  name        = "${var.project_name}-exclude-genai-from-default"
  project     = each.value
  description = "Exclude GenAI telemetry logs from _Default bucket. Logs are routed to custom bucket instead."
  filter      = var.telemetry_logs_filter
}

# Log view for GenAI telemetry events on the custom bucket
resource "google_logging_log_view" "genai_telemetry_view" {
  for_each    = local.deploy_project_ids
  name        = "${var.project_name}-genai-telemetry"
  bucket      = google_logging_project_bucket_config.genai_telemetry_bucket[each.key].id
  description = "View for GenAI telemetry events (user messages, system prompts, model completions) for ${var.project_name}"
  # View filter uses source() since bucket already contains only GenAI logs via sink
  filter      = "source(\"projects/${each.value}\")"
}

# Example: Grant a user/group access to the GenAI telemetry log view
# Uncomment and modify to grant specific users access to GenAI telemetry logs
#
# resource "google_logging_log_view_iam_member" "genai_telemetry_viewer" {
#   for_each = local.deploy_project_ids
#   project  = each.value
#   location = "global"
#   bucket   = google_logging_project_bucket_config.genai_telemetry_bucket[each.key].bucket_id
#   name     = google_logging_log_view.genai_telemetry_view[each.key].name
#   role     = "roles/logging.viewAccessor"
#   member   = "user:example@example.com"  # Change to your user/group/service account
# }
