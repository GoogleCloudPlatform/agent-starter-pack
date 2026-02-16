{% if cookiecutter.data_ingestion and cookiecutter.datastore_type == "vertex_ai_vector_search" %}
resource "google_storage_bucket" "data_ingestion_pipeline_gcs_root" {
  for_each                    = local.deploy_project_ids
  name                        = "${each.value}-${var.project_name}-rag"
  location                    = var.region
  project                     = each.value
  uniform_bucket_level_access = true
  force_destroy               = true

  depends_on = [resource.google_project_service.cicd_services, resource.google_project_service.deploy_project_services]
}

# Set up Vector Search 2.0 Collection for staging
resource "null_resource" "vector_search_collection_staging" {
  triggers = {
    project_id    = var.staging_project_id
    location      = var.vector_search_location
    collection_id = var.vector_search_collection_id
    scripts_dir   = "${path.module}/scripts"
  }

  provisioner "local-exec" {
    command = "uv run ${path.module}/scripts/setup_vector_search_collection.py ${var.staging_project_id} ${var.vector_search_location} ${var.vector_search_collection_id}"
  }

  provisioner "local-exec" {
    when    = destroy
    command = "uv run ${self.triggers.scripts_dir}/delete_vector_search_collection.py ${self.triggers.project_id} ${self.triggers.location} ${self.triggers.collection_id}"
  }

  depends_on = [resource.google_project_service.cicd_services, resource.google_project_service.deploy_project_services]
}

# Set up Vector Search 2.0 Collection for prod
resource "null_resource" "vector_search_collection_prod" {
  triggers = {
    project_id    = var.prod_project_id
    location      = var.vector_search_location
    collection_id = var.vector_search_collection_id
    scripts_dir   = "${path.module}/scripts"
  }

  provisioner "local-exec" {
    command = "uv run ${path.module}/scripts/setup_vector_search_collection.py ${var.prod_project_id} ${var.vector_search_location} ${var.vector_search_collection_id}"
  }

  provisioner "local-exec" {
    when    = destroy
    command = "uv run ${self.triggers.scripts_dir}/delete_vector_search_collection.py ${self.triggers.project_id} ${self.triggers.location} ${self.triggers.collection_id}"
  }

  depends_on = [resource.google_project_service.cicd_services, resource.google_project_service.deploy_project_services]
}

{% endif %}
