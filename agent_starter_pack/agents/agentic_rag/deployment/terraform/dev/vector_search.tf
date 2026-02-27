{% if cookiecutter.data_ingestion and cookiecutter.datastore_type == "vertex_ai_vector_search" %}
resource "google_storage_bucket" "data_ingestion_PIPELINE_GCS_ROOT" {
  name                        = "${var.dev_project_id}-${var.project_name}-rag"
  location                    = var.region
  project                     = var.dev_project_id
  uniform_bucket_level_access = true
  force_destroy               = true

  depends_on = [resource.google_project_service.services]
}

# Set up Vector Search 2.0 Collection for dev
resource "null_resource" "vector_search_collection_dev" {
  triggers = {
    project_id    = var.dev_project_id
    location      = var.vector_search_location
    collection_id = var.vector_search_collection_id
    scripts_dir   = "${path.module}/../scripts"
  }

  provisioner "local-exec" {
    command = "uv run ${path.module}/../scripts/setup_vector_search_collection.py ${var.dev_project_id} ${var.vector_search_location} ${var.vector_search_collection_id}"
  }

  provisioner "local-exec" {
    when    = destroy
    command = "uv run ${self.triggers.scripts_dir}/delete_vector_search_collection.py ${self.triggers.project_id} ${self.triggers.location} ${self.triggers.collection_id}"
  }

  depends_on = [resource.google_project_service.services]
}
{% endif %}
