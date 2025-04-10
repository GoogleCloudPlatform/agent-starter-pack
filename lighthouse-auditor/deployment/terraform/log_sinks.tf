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

resource "google_project_iam_member" "bigquery_data_editor" {
  for_each = local.deploy_project_ids

  project = each.value
  role    = "roles/bigquery.dataEditor"
  member  = module.log_export_to_bigquery[each.key].writer_identity
}

resource "google_bigquery_dataset" "feedback_dataset" {
  for_each      = local.deploy_project_ids
  project       = each.value
  dataset_id    = replace("${var.project_name}_feedback", "-", "_")
  friendly_name = "${var.project_name}_feedback"
  location      = var.region
  depends_on    = [resource.google_project_service.cicd_services, resource.google_project_service.shared_services]
}

resource "google_bigquery_dataset" "telemetry_logs_dataset" {
  for_each      = local.deploy_project_ids
  project       = each.value
  dataset_id    = replace("${var.project_name}_telemetry", "-", "_")
  friendly_name = "${var.project_name}_telemetry"
  location      = var.region
  depends_on    = [resource.google_project_service.cicd_services, resource.google_project_service.shared_services]
}

module "log_export_to_bigquery" {
  for_each = local.deploy_project_ids

  source  = "terraform-google-modules/log-export/google"
  version = "10.0.0"

  log_sink_name          = "${var.project_name}_telemetry"
  parent_resource_type   = "project"
  parent_resource_id     = each.value
  destination_uri        = "bigquery.googleapis.com/projects/${each.value}/datasets/${google_bigquery_dataset.telemetry_logs_dataset[each.key].dataset_id}"
  filter                 = var.telemetry_logs_filter
  bigquery_options       = { use_partitioned_tables = true }
  unique_writer_identity = true
  depends_on             = [google_bigquery_dataset.telemetry_logs_dataset]
}

module "feedback_export_to_bigquery" {
  for_each = local.deploy_project_ids

  source                 = "terraform-google-modules/log-export/google"
  version                = "10.0.0"
  log_sink_name          = "${var.project_name}_feedback"
  parent_resource_type   = "project"
  parent_resource_id     = each.value
  destination_uri        = "bigquery.googleapis.com/projects/${each.value}/datasets/${google_bigquery_dataset.feedback_dataset[each.key].dataset_id}"
  filter                 = var.feedback_logs_filter
  bigquery_options       = { use_partitioned_tables = true }
  unique_writer_identity = true
  depends_on             = [google_bigquery_dataset.feedback_dataset]
}
