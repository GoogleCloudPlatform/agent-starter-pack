{% if cookiecutter.data_ingestion and cookiecutter.datastore_type == "vertex_ai_vector_search" %}

variable "pipelines_roles" {
  description = "List of roles to assign to the Vertex AI runner service account"
  type        = list(string)
  default = [
    "roles/storage.admin",
    "roles/run.invoker",
    "roles/aiplatform.user",
    "roles/discoveryengine.admin",
    "roles/logging.logWriter",
    "roles/artifactregistry.writer",
    "roles/bigquery.dataEditor",
    "roles/bigquery.jobUser",
    "roles/bigquery.readSessionUser",
    "roles/bigquery.connectionAdmin",
    "roles/resourcemanager.projectIamAdmin"
  ]
}

variable "vector_search_location" {
  type        = string
  description = "The location for the Vector Search 2.0 Collection."
  default     = "us-central1"
}

variable "vector_search_collection_id" {
  type        = string
  description = "The ID for the Vector Search 2.0 Collection."
  default     = "{{cookiecutter.project_name}}-collection"
}
{% endif %}
