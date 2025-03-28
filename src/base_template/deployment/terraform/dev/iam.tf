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
  project_ids = {
    dev = var.dev_project_id
  }
}


# Get the project number for the dev project
data "google_project" "dev_project" {
  project_id = var.dev_project_id
}

# Grant Storage Object Creator role to default compute service account
resource "google_project_iam_member" "default_compute_sa_storage_object_creator" {
  project    = var.dev_project_id
  role       = "roles/cloudbuild.builds.builder"
  member     = "serviceAccount:${data.google_project.dev_project.number}-compute@developer.gserviceaccount.com"
  depends_on = [resource.google_project_service.services]
}

{% if cookiecutter.deployment_target == 'cloud_run' %}
resource "google_service_account" "cloud_run_app_sa" {
  account_id   = "${var.project_name}-cr"
  display_name = "${var.project_name} Cloud Run App Service Account"
  project      = var.dev_project_id
  depends_on   = [resource.google_project_service.services]
}

# Grant Cloud Run SA the required permissions to run the application
resource "google_project_iam_member" "cloud_run_app_sa_roles" {
  for_each = {
    for pair in setproduct(keys(local.project_ids), var.cloud_run_app_roles) :
    join(",", pair) => {
      project = local.project_ids[pair[0]]
      role    = pair[1]
    }
  }

  project    = each.value.project
  role       = each.value.role
  member     = "serviceAccount:${google_service_account.cloud_run_app_sa.email}"
  depends_on = [resource.google_project_service.services]
}
{% elif cookiecutter.deployment_target == 'agent_engine' %}
# Grant required permissions to Vertex AI service account
resource "google_project_iam_member" "vertex_ai_sa_permissions" {
  for_each = {
    for pair in setproduct(keys(local.project_ids), var.agentengine_sa_roles) :
    join(",", pair) => pair[1]
  }

  project = var.dev_project_id
  role    = each.value
  member  = google_project_service_identity.vertex_sa.member
  depends_on = [resource.google_project_service.services]
}
{% endif %}
{% if cookiecutter.data_ingestion %}
# Service account to run Vertex AI pipeline
resource "google_service_account" "vertexai_pipeline_app_sa" {
  for_each = local.project_ids

  account_id   = "${var.project_name}-rag"
  display_name = "Vertex AI Pipeline app SA"
  project      = each.value
  depends_on   = [resource.google_project_service.services]
}

resource "google_project_iam_member" "vertexai_pipeline_sa_roles" {
  for_each = {
    for pair in setproduct(keys(local.project_ids), var.pipelines_roles) :
    join(",", pair) => {
      project = local.project_ids[pair[0]]
      role    = pair[1]
    }
  }

  project    = each.value.project
  role       = each.value.role
  member     = "serviceAccount:${google_service_account.vertexai_pipeline_app_sa[split(",", each.key)[0]].email}"
  depends_on = [resource.google_project_service.services]
}
{% endif %}
