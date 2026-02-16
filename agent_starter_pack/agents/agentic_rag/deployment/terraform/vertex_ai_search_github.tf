{% if cookiecutter.cicd_runner == 'github_actions' %}
{% if cookiecutter.data_ingestion and cookiecutter.datastore_type == "vertex_ai_search" %}
resource "github_actions_variable" "data_store_id_staging" {
  repository    = var.repository_name
  variable_name = "DATA_STORE_ID_STAGING"
  value         = data.external.data_store_id_staging.result.data_store_id
  depends_on    = [github_repository.repo]
}

resource "github_actions_variable" "data_store_id_prod" {
  repository    = var.repository_name
  variable_name = "DATA_STORE_ID_PROD"
  value         = data.external.data_store_id_prod.result.data_store_id
  depends_on    = [github_repository.repo]
}

resource "github_actions_variable" "data_store_region" {
  repository    = var.repository_name
  variable_name = "DATA_STORE_REGION"
  value         = var.data_store_region
  depends_on    = [github_repository.repo]
}
{% endif %}
{% endif %}
