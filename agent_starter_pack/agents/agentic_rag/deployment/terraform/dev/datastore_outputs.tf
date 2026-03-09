{% if cookiecutter.data_ingestion and cookiecutter.datastore_type == "vertex_ai_vector_search" %}
output "vector_search_collection_id" {
  description = "Vector Search collection ID"
  value       = var.vector_search_collection_id
}

output "pipeline_gcs_bucket_name" {
  description = "Pipeline GCS bucket name"
  value       = google_storage_bucket.data_ingestion_PIPELINE_GCS_ROOT.name
}
{% elif cookiecutter.datastore_type == "vertex_ai_search" %}
output "data_store_id" {
  description = "Data store ID for dev environment"
  value       = data.external.data_store_id_dev.result.data_store_id
}

output "search_engine_id" {
  description = "Search engine ID"
  value       = google_discovery_engine_search_engine.search_engine_dev.engine_id
}

output "docs_bucket_name" {
  description = "Document bucket name"
  value       = google_storage_bucket.docs_bucket.name
}
{% endif %}
