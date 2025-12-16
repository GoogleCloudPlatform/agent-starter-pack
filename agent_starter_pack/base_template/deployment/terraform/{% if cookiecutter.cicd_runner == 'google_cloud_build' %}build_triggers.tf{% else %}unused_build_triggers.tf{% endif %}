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

# a. Create PR checks trigger
resource "google_cloudbuild_trigger" "pr_checks" {
  name            = "pr-${var.project_name}"
  project         = var.cicd_runner_project_id
  location        = var.region
  description     = "Trigger for PR checks"
  service_account = resource.google_service_account.cicd_runner_sa.id

  repository_event_config {
    repository = "projects/${var.cicd_runner_project_id}/locations/${var.region}/connections/${var.host_connection_name}/repositories/${var.repository_name}"
    pull_request {
      branch = "main"
    }
  }

  filename = ".cloudbuild/pr_checks.yaml"
  included_files = [
    "{{cookiecutter.agent_directory}}/**",
    "data_ingestion/**",
    "tests/**",
    "deployment/**",
    "uv.lock",
  {% if cookiecutter.data_ingestion %}
    "data_ingestion/**",
  {% endif %}
  ]
  include_build_logs = "INCLUDE_BUILD_LOGS_WITH_STATUS"
  depends_on = [
    resource.google_project_service.cicd_services, 
    resource.google_project_service.deploy_project_services, 
    google_cloudbuildv2_connection.github_connection, 
    google_cloudbuildv2_repository.repo
  ]
}

# b. Create CD pipeline trigger
resource "google_cloudbuild_trigger" "cd_pipeline" {
  name            = "cd-${var.project_name}"
  project         = var.cicd_runner_project_id
  location        = var.region
  service_account = resource.google_service_account.cicd_runner_sa.id
  description     = "Trigger for CD pipeline"

  repository_event_config {
    repository = "projects/${var.cicd_runner_project_id}/locations/${var.region}/connections/${var.host_connection_name}/repositories/${var.repository_name}"
    push {
      branch = "main"
    }
  }

  filename = ".cloudbuild/staging.yaml"
  included_files = [
    "{{cookiecutter.agent_directory}}/**",
    "data_ingestion/**",
    "tests/**",
    "deployment/**",
    "uv.lock"
  ]
  include_build_logs = "INCLUDE_BUILD_LOGS_WITH_STATUS"
  substitutions = {
    _STAGING_PROJECT_ID            = var.staging_project_id
    _LOGS_BUCKET_NAME_STAGING      = resource.google_storage_bucket.logs_data_bucket[var.staging_project_id].name
    _APP_SERVICE_ACCOUNT_STAGING   = google_service_account.app_sa["staging"].email
    _REGION                        = var.region
{%- if cookiecutter.deployment_target == 'cloud_run' %}
    _CONTAINER_NAME                = var.project_name
    _ARTIFACT_REGISTRY_REPO_NAME   = resource.google_artifact_registry_repository.repo-artifacts-genai.repository_id
{%- elif cookiecutter.deployment_target == 'agent_engine' %}
{%- endif %}
{%- if cookiecutter.data_ingestion %}
    _PIPELINE_GCS_ROOT_STAGING     = "gs://${resource.google_storage_bucket.data_ingestion_pipeline_gcs_root["staging"].name}"
    _PIPELINE_SA_EMAIL_STAGING             = resource.google_service_account.vertexai_pipeline_app_sa["staging"].email
    _PIPELINE_CRON_SCHEDULE        = var.pipeline_cron_schedule
{%- if cookiecutter.datastore_type == "vertex_ai_search" %}
    _DATA_STORE_ID_STAGING         = resource.google_discovery_engine_data_store.data_store_staging.data_store_id
    _DATA_STORE_REGION             = var.data_store_region
{%- elif cookiecutter.datastore_type == "vertex_ai_vector_search" %}
    _VECTOR_SEARCH_INDEX_STAGING   = resource.google_vertex_ai_index.vector_search_index_staging.id
    _VECTOR_SEARCH_INDEX_ENDPOINT_STAGING = resource.google_vertex_ai_index_endpoint.vector_search_index_endpoint_staging.id
    _VECTOR_SEARCH_BUCKET_STAGING  = resource.google_storage_bucket.vector_search_data_bucket["staging"].url
{%- endif %}
{%- endif %}
    # Your other CD Pipeline substitutions
  }
  depends_on = [
    resource.google_project_service.cicd_services, 
    resource.google_project_service.deploy_project_services, 
    google_cloudbuildv2_connection.github_connection, 
    google_cloudbuildv2_repository.repo
  ]

}

# c. Create Deploy to production trigger
resource "google_cloudbuild_trigger" "deploy_to_prod_pipeline" {
  name            = "deploy-${var.project_name}"
  project         = var.cicd_runner_project_id
  location        = var.region
  description     = "Trigger for deployment to production"
  service_account = resource.google_service_account.cicd_runner_sa.id
  repository_event_config {
    repository = "projects/${var.cicd_runner_project_id}/locations/${var.region}/connections/${var.host_connection_name}/repositories/${var.repository_name}"
  }
  filename = ".cloudbuild/deploy-to-prod.yaml"
  include_build_logs = "INCLUDE_BUILD_LOGS_WITH_STATUS"
  approval_config {
    approval_required = true
  }
  substitutions = {
    _PROD_PROJECT_ID             = var.prod_project_id
    _LOGS_BUCKET_NAME_PROD       = resource.google_storage_bucket.logs_data_bucket[var.prod_project_id].name
    _APP_SERVICE_ACCOUNT_PROD    = google_service_account.app_sa["prod"].email
    _REGION                      = var.region
{%- if cookiecutter.deployment_target == 'cloud_run' %}
    _CONTAINER_NAME              = var.project_name
    _ARTIFACT_REGISTRY_REPO_NAME = resource.google_artifact_registry_repository.repo-artifacts-genai.repository_id
{%- elif cookiecutter.deployment_target == 'agent_engine' %}
{%- endif %}
{%- if cookiecutter.data_ingestion %}
    _PIPELINE_GCS_ROOT_PROD        = "gs://${resource.google_storage_bucket.data_ingestion_pipeline_gcs_root["prod"].name}"
    _PIPELINE_SA_EMAIL_PROD             = resource.google_service_account.vertexai_pipeline_app_sa["prod"].email
    _PIPELINE_CRON_SCHEDULE        = var.pipeline_cron_schedule
{%- if cookiecutter.datastore_type == "vertex_ai_search" %}
    _DATA_STORE_ID_PROD            = resource.google_discovery_engine_data_store.data_store_prod.data_store_id
    _DATA_STORE_REGION             = var.data_store_region
{%- elif cookiecutter.datastore_type == "vertex_ai_vector_search" %}
    _VECTOR_SEARCH_INDEX_PROD      = resource.google_vertex_ai_index.vector_search_index_prod.id
    _VECTOR_SEARCH_INDEX_ENDPOINT_PROD = resource.google_vertex_ai_index_endpoint.vector_search_index_endpoint_prod.id
    _VECTOR_SEARCH_BUCKET_PROD     = resource.google_storage_bucket.vector_search_data_bucket["prod"].url
{%- endif %}
{%- endif %}
    # Your other Deploy to Prod Pipeline substitutions
  }
  depends_on = [
    resource.google_project_service.cicd_services, 
    resource.google_project_service.deploy_project_services, 
    google_cloudbuildv2_connection.github_connection, 
    google_cloudbuildv2_repository.repo
  ]

}
