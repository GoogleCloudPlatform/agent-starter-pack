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

provider "github" {
  owner = var.repository_owner
}

# Try to get existing repo
data "github_repository" "existing_repo" {
  count = var.create_repository ? 0 : 1
  full_name = "${var.repository_owner}/${var.repository_name}"
}

# Only create GitHub repo if create_repository is true
resource "github_repository" "repo" {
  count       = var.create_repository ? 1 : 0
  name        = var.repository_name
  description = "Repository created with goo.gle/agent-starter-pack"
  visibility  = "private"

  has_issues      = true
  has_wiki        = false
  has_projects    = false
  has_downloads   = false

  allow_merge_commit = true
  allow_squash_merge = true
  allow_rebase_merge = true
  
  auto_init = false
}

{% if cookiecutter.cicd_runner == 'github_actions' %}
resource "github_actions_variable" "gcp_project_number" {
  repository    = var.repository_name
  variable_name = "GCP_PROJECT_NUMBER"
  value         = data.google_project.cicd_project.number
  depends_on    = [github_repository.repo]
}

resource "github_actions_secret" "wif_pool_id" {
  repository      = var.repository_name
  secret_name     = "WIF_POOL_ID"
  plaintext_value = google_iam_workload_identity_pool.github_pool.workload_identity_pool_id
  depends_on      = [github_repository.repo, data.github_repository.existing_repo]
}

resource "github_actions_secret" "wif_provider_id" {
  repository      = var.repository_name
  secret_name     = "WIF_PROVIDER_ID"
  plaintext_value = google_iam_workload_identity_pool_provider.github_provider.workload_identity_pool_provider_id
  depends_on      = [github_repository.repo, data.github_repository.existing_repo]
}

resource "github_actions_secret" "gcp_service_account" {
  repository      = var.repository_name
  secret_name     = "GCP_SERVICE_ACCOUNT"
  plaintext_value = google_service_account.cicd_runner_sa.email
  depends_on      = [github_repository.repo, data.github_repository.existing_repo]
}

resource "github_actions_variable" "staging_project_id" {
  repository    = var.repository_name
  variable_name = "STAGING_PROJECT_ID"
  value         = var.staging_project_id
  depends_on    = [github_repository.repo]
}

resource "github_actions_variable" "prod_project_id" {
  repository    = var.repository_name
  variable_name = "PROD_PROJECT_ID"
  value         = var.prod_project_id
  depends_on    = [github_repository.repo]
}

resource "github_actions_variable" "region" {
  repository    = var.repository_name
  variable_name = "REGION"
  value         = var.region
  depends_on    = [github_repository.repo]
}

resource "github_actions_variable" "cicd_project_id" {
  repository    = var.repository_name
  variable_name = "CICD_PROJECT_ID"
  value         = var.cicd_runner_project_id
  depends_on    = [github_repository.repo]
}

resource "github_actions_variable" "app_sa_email_staging" {
  repository    = var.repository_name
  variable_name = "APP_SA_EMAIL_STAGING"
  value         = google_service_account.app_sa["staging"].email
  depends_on    = [github_repository.repo]
}

resource "github_actions_variable" "app_sa_email_prod" {
  repository    = var.repository_name
  variable_name = "APP_SA_EMAIL_PROD"
  value         = google_service_account.app_sa["prod"].email
  depends_on    = [github_repository.repo]
}

resource "github_actions_variable" "app_service_account_staging" {
  repository    = var.repository_name
  variable_name = "APP_SERVICE_ACCOUNT_STAGING"
  value         = google_service_account.app_sa["staging"].email
  depends_on    = [github_repository.repo]
}

resource "github_actions_variable" "app_service_account_prod" {
  repository    = var.repository_name
  variable_name = "APP_SERVICE_ACCOUNT_PROD"
  value         = google_service_account.app_sa["prod"].email
  depends_on    = [github_repository.repo]
}

resource "github_actions_variable" "logs_bucket_name_staging" {
  repository    = var.repository_name
  variable_name = "LOGS_BUCKET_NAME_STAGING"
  value         = google_storage_bucket.logs_data_bucket[var.staging_project_id].name
  depends_on    = [github_repository.repo]
}

resource "github_actions_variable" "logs_bucket_name_prod" {
  repository    = var.repository_name
  variable_name = "LOGS_BUCKET_NAME_PROD"
  value         = google_storage_bucket.logs_data_bucket[var.prod_project_id].name
  depends_on    = [github_repository.repo]
}

{% if cookiecutter.deployment_target == 'cloud_run' %}
resource "github_actions_variable" "container_name" {
  repository    = var.repository_name
  variable_name = "CONTAINER_NAME"
  value         = var.project_name
  depends_on    = [github_repository.repo]
}

resource "github_actions_variable" "artifact_registry_repo_name" {
  repository    = var.repository_name
  variable_name = "ARTIFACT_REGISTRY_REPO_NAME"
  value         = google_artifact_registry_repository.repo-artifacts-genai.repository_id
  depends_on    = [github_repository.repo]
}
{% endif %}

{% if cookiecutter.data_ingestion %}
resource "github_actions_variable" "pipeline_gcs_root_staging" {
  repository    = var.repository_name
  variable_name = "PIPELINE_GCS_ROOT_STAGING"
  value         = "gs://${google_storage_bucket.data_ingestion_pipeline_gcs_root["staging"].name}"
  depends_on    = [github_repository.repo]
}

resource "github_actions_variable" "pipeline_gcs_root_prod" {
  repository    = var.repository_name
  variable_name = "PIPELINE_GCS_ROOT_PROD"
  value         = "gs://${google_storage_bucket.data_ingestion_pipeline_gcs_root["prod"].name}"
  depends_on    = [github_repository.repo]
}

resource "github_actions_variable" "pipeline_sa_email_staging" {
  repository    = var.repository_name
  variable_name = "PIPELINE_SA_EMAIL_STAGING"
  value         = google_service_account.vertexai_pipeline_app_sa["staging"].email
  depends_on    = [github_repository.repo]
}

resource "github_actions_variable" "pipeline_sa_email_prod" {
  repository    = var.repository_name
  variable_name = "PIPELINE_SA_EMAIL_PROD"
  value         = google_service_account.vertexai_pipeline_app_sa["prod"].email
  depends_on    = [github_repository.repo]
}

resource "github_actions_variable" "pipeline_name" {
  repository    = var.repository_name
  variable_name = "PIPELINE_NAME"
  value         = var.project_name
  depends_on    = [github_repository.repo]
}

resource "github_actions_variable" "pipeline_cron_schedule" {
  repository    = var.repository_name
  variable_name = "PIPELINE_CRON_SCHEDULE"
  value         = var.pipeline_cron_schedule
  depends_on    = [github_repository.repo]
}

{% if cookiecutter.datastore_type == "vertex_ai_search" %}
resource "github_actions_variable" "data_store_id_staging" {
  repository    = var.repository_name
  variable_name = "DATA_STORE_ID_STAGING"
  value         = google_discovery_engine_data_store.data_store_staging.data_store_id
  depends_on    = [github_repository.repo]
}

resource "github_actions_variable" "data_store_id_prod" {
  repository    = var.repository_name
  variable_name = "DATA_STORE_ID_PROD"
  value         = google_discovery_engine_data_store.data_store_prod.data_store_id
  depends_on    = [github_repository.repo]
}

resource "github_actions_variable" "data_store_region" {
  repository    = var.repository_name
  variable_name = "DATA_STORE_REGION"
  value         = var.data_store_region
  depends_on    = [github_repository.repo]
}
{% elif cookiecutter.datastore_type == "vertex_ai_vector_search" %}
resource "github_actions_variable" "vector_search_index_staging" {
  repository    = var.repository_name
  variable_name = "VECTOR_SEARCH_INDEX_STAGING"
  value         = google_vertex_ai_index.vector_search_index_staging.id
  depends_on    = [github_repository.repo]
}

resource "github_actions_variable" "vector_search_index_prod" {
  repository    = var.repository_name
  variable_name = "VECTOR_SEARCH_INDEX_PROD"
  value         = google_vertex_ai_index.vector_search_index_prod.id
  depends_on    = [github_repository.repo]
}

resource "github_actions_variable" "vector_search_index_endpoint_staging" {
  repository    = var.repository_name
  variable_name = "VECTOR_SEARCH_INDEX_ENDPOINT_STAGING"
  value         = google_vertex_ai_index_endpoint.vector_search_index_endpoint_staging.id
  depends_on    = [github_repository.repo]
}

resource "github_actions_variable" "vector_search_index_endpoint_prod" {
  repository    = var.repository_name
  variable_name = "VECTOR_SEARCH_INDEX_ENDPOINT_PROD"
  value         = google_vertex_ai_index_endpoint.vector_search_index_endpoint_prod.id
  depends_on    = [github_repository.repo]
}

resource "github_actions_variable" "vector_search_bucket_staging" {
  repository    = var.repository_name
  variable_name = "VECTOR_SEARCH_BUCKET_STAGING"
  value         = google_storage_bucket.vector_search_data_bucket["staging"].url
  depends_on    = [github_repository.repo]
}

resource "github_actions_variable" "vector_search_bucket_prod" {
  repository    = var.repository_name
  variable_name = "VECTOR_SEARCH_BUCKET_PROD"
  value         = google_storage_bucket.vector_search_data_bucket["prod"].url
  depends_on    = [github_repository.repo]
}
{% endif %}
{% endif %}

resource "github_repository_environment" "production_environment" {
  repository  = var.repository_name
  environment = "production"
  depends_on  = [github_repository.repo, data.github_repository.existing_repo]

  deployment_branch_policy {
    protected_branches     = false
    custom_branch_policies = true
  }
}
{% else %}

# Reference existing GitHub PAT secret created by gcloud CLI
data "google_secret_manager_secret" "github_pat" {
  project   = var.cicd_runner_project_id
  secret_id = var.github_pat_secret_id
}

# Get CICD project data for Cloud Build service account
data "google_project" "cicd_project" {
  project_id = var.cicd_runner_project_id
}

# Grant Cloud Build service account access to GitHub PAT secret
resource "google_secret_manager_secret_iam_member" "cloudbuild_secret_accessor" {
  project   = var.cicd_runner_project_id
  secret_id = data.google_secret_manager_secret.github_pat.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:service-${data.google_project.cicd_project.number}@gcp-sa-cloudbuild.iam.gserviceaccount.com"
  depends_on = [resource.google_project_service.cicd_services]
}

# Create the GitHub connection (fallback for manual Terraform usage)
resource "google_cloudbuildv2_connection" "github_connection" {
  count      = var.create_cb_connection ? 0 : 1
  project    = var.cicd_runner_project_id
  location   = var.region
  name       = var.host_connection_name

  github_config {
    app_installation_id = var.github_app_installation_id
    authorizer_credential {
      oauth_token_secret_version = "${data.google_secret_manager_secret.github_pat.id}/versions/latest"
    }
  }
  depends_on = [
    resource.google_project_service.cicd_services,
    resource.google_project_service.deploy_project_services,
    resource.google_secret_manager_secret_iam_member.cloudbuild_secret_accessor
  ]
}


resource "google_cloudbuildv2_repository" "repo" {
  project  = var.cicd_runner_project_id
  location = var.region
  name     = var.repository_name
  
  # Use existing connection ID when it exists, otherwise use the created connection
  parent_connection = var.create_cb_connection ? "projects/${var.cicd_runner_project_id}/locations/${var.region}/connections/${var.host_connection_name}" : google_cloudbuildv2_connection.github_connection[0].id
  remote_uri       = "https://github.com/${var.repository_owner}/${var.repository_name}.git"
  depends_on = [
    resource.google_project_service.cicd_services,
    resource.google_project_service.deploy_project_services,
    data.github_repository.existing_repo,
    github_repository.repo,
    google_cloudbuildv2_connection.github_connection,
  ]
}
{% endif %}