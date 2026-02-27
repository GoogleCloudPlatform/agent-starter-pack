{% if cookiecutter.cicd_runner == 'github_actions' %}
{% if cookiecutter.data_ingestion and cookiecutter.datastore_type == "vertex_ai_vector_search" %}
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

resource "github_actions_variable" "vector_search_collection_id" {
  repository    = var.repository_name
  variable_name = "VECTOR_SEARCH_COLLECTION_ID"
  value         = var.vector_search_collection_id
  depends_on    = [github_repository.repo]
}

resource "github_actions_variable" "vector_search_location" {
  repository    = var.repository_name
  variable_name = "VECTOR_SEARCH_LOCATION"
  value         = var.vector_search_location
  depends_on    = [github_repository.repo]
}
{% endif %}
{% endif %}
