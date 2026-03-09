{% if cookiecutter.data_ingestion and cookiecutter.datastore_type == "vertex_ai_vector_search" %}
output "vector_search_collection_id" {
  description = "Vector Search collection ID"
  value       = var.vector_search_collection_id
}

output "pipeline_service_account_emails" {
  description = "Pipeline service account emails by environment"
  value       = { for k, v in google_service_account.vertexai_pipeline_app_sa : k => v.email }
}

output "pipeline_gcs_bucket_names" {
  description = "Pipeline GCS bucket names by environment"
  value       = { for k, v in google_storage_bucket.data_ingestion_pipeline_gcs_root : k => v.name }
}
{% elif cookiecutter.datastore_type == "vertex_ai_search" %}
output "data_store_id_staging" {
  description = "Data store ID for staging environment"
  value       = data.external.data_store_id_staging.result.data_store_id
}

output "data_store_id_prod" {
  description = "Data store ID for prod environment"
  value       = data.external.data_store_id_prod.result.data_store_id
}

output "search_engine_ids" {
  description = "Search engine IDs by environment"
  value = {
    staging = google_discovery_engine_search_engine.search_engine_staging.engine_id
    prod    = google_discovery_engine_search_engine.search_engine_prod.engine_id
  }
}

output "docs_bucket_names" {
  description = "Document bucket names by environment"
  value       = { for k, v in google_storage_bucket.docs_bucket : k => v.name }
}
{% endif %}
