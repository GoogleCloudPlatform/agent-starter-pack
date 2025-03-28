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

# Data source to get project numbers
data "google_project" "projects" {
  for_each   = local.deploy_project_ids
  project_id = each.value
}

# 1. Assign roles for the CICD project
resource "google_project_iam_member" "cicd_project_roles" {
  for_each = toset(var.cicd_roles)

  project    = var.cicd_runner_project_id
  role       = each.value
  member     = "serviceAccount:${resource.google_service_account.cicd_runner_sa.email}"
  depends_on = [resource.google_project_service.cicd_services, resource.google_project_service.shared_services]

}

# 2. Assign roles for the other two projects (prod and staging)
resource "google_project_iam_member" "other_projects_roles" {
  for_each = {
    for pair in setproduct(keys(local.deploy_project_ids), var.cicd_sa_deployment_required_roles) :
    "${pair[0]}-${pair[1]}" => {
      project_id = local.deploy_project_ids[pair[0]]
      role       = pair[1]
    }
  }

  project    = each.value.project_id
  role       = each.value.role
  member     = "serviceAccount:${resource.google_service_account.cicd_runner_sa.email}"
  depends_on = [resource.google_project_service.cicd_services, resource.google_project_service.shared_services]
}
{% if cookiecutter.deployment_target == 'cloud_run' %}
# 3. Allow Cloud Run service SA to pull containers stored in the CICD project
resource "google_project_iam_member" "cicd_run_invoker_artifact_registry_reader" {
  for_each = local.deploy_project_ids
  project  = var.cicd_runner_project_id

  role       = "roles/artifactregistry.reader"
  member     = "serviceAccount:service-${data.google_project.projects[each.key].number}@serverless-robot-prod.iam.gserviceaccount.com"
  depends_on = [resource.google_project_service.cicd_services, resource.google_project_service.shared_services]

}

# 4. Grant Cloud Run SA the required permissions to run the application
resource "google_project_iam_member" "cloud_run_app_sa_roles" {
  for_each = {
    for pair in setproduct(keys(local.deploy_project_ids), var.cloud_run_app_roles) :
    join(",", pair) => {
      project = local.deploy_project_ids[pair[0]]
      role    = pair[1]
    }
  }

  project    = each.value.project
  role       = each.value.role
  member     = "serviceAccount:${google_service_account.cloud_run_app_sa[split(",", each.key)[0]].email}"
  depends_on = [resource.google_project_service.cicd_services, resource.google_project_service.shared_services]
}
{% elif cookiecutter.deployment_target == 'agent_engine' %}
resource "google_project_service_identity" "vertex_sa" {
  for_each = local.deploy_project_ids
  provider = google-beta
  project  = each.value
  service  = "aiplatform.googleapis.com"
}

# 3. Grant required permissions to Vertex AI Service Agent SA
resource "google_project_iam_member" "vertex_ai_sa_permissions" {
  for_each = {
    for pair in setproduct(keys(local.deploy_project_ids), var.agentengine_sa_roles) :
    "${pair[0]}_${pair[1]}" => {
      project = local.deploy_project_ids[pair[0]]
      role = pair[1]
    }
  }

  project     = each.value.project
  role        = each.value.role
  member      = "serviceAccount:service-${data.google_project.projects[split("_", each.key)[0]].number}@gcp-sa-aiplatform-re.iam.gserviceaccount.com"
  depends_on  = [resource.google_project_service.shared_services, resource.google_project_service_identity.vertex_sa]
}
{% endif %}

# Special assignment: Allow the CICD SA to create tokens
resource "google_service_account_iam_member" "cicd_run_invoker_token_creator" {
  service_account_id = google_service_account.cicd_runner_sa.name
  role               = "roles/iam.serviceAccountTokenCreator"
  member             = "serviceAccount:${resource.google_service_account.cicd_runner_sa.email}"
  depends_on         = [resource.google_project_service.cicd_services, resource.google_project_service.shared_services]
}
# Special assignment: Allow the CICD SA to impersonate himself for trigger creation
resource "google_service_account_iam_member" "cicd_run_invoker_account_user" {
  service_account_id = google_service_account.cicd_runner_sa.name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${resource.google_service_account.cicd_runner_sa.email}"
  depends_on         = [resource.google_project_service.cicd_services, resource.google_project_service.shared_services]
}

{%- if cookiecutter.data_ingestion %}
# Grant Vertex AI SA the required permissions to run the ingestion
resource "google_project_iam_member" "vertexai_pipeline_sa_roles" {
  for_each = {
    for pair in setproduct(keys(local.deploy_project_ids), var.pipelines_roles) :
    join(",", pair) => {
      project = local.deploy_project_ids[pair[0]]
      role    = pair[1]
    }
  }

  project    = each.value.project
  role       = each.value.role
  member     = "serviceAccount:${google_service_account.vertexai_pipeline_app_sa[split(",", each.key)[0]].email}"
  depends_on = [resource.google_project_service.cicd_services, resource.google_project_service.shared_services]
}
{%- endif %}
