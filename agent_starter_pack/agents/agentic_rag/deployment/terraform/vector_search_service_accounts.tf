{% if cookiecutter.data_ingestion and cookiecutter.datastore_type == "vertex_ai_vector_search" %}
# Service account to run Vertex AI pipeline
resource "google_service_account" "vertexai_pipeline_app_sa" {
  for_each = local.deploy_project_ids

  account_id   = "${var.project_name}-rag"
  display_name = "Vertex AI Pipeline app SA"
  project      = each.value
  depends_on   = [resource.google_project_service.cicd_services, resource.google_project_service.deploy_project_services]
}
{% endif %}
