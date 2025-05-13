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

variable "project_name" {
  type        = string
  description = "Project name used as a base for resource naming"
  default     = "{{ cookiecutter.project_name | replace('_', '-') }}"
}

variable "prod_project_id" {
  type        = string
  description = "**Production** Google Cloud Project ID for resource deployment."
}

variable "staging_project_id" {
  type        = string
  description = "**Staging** Google Cloud Project ID for resource deployment."
}

variable "cicd_runner_project_id" {
  type        = string
  description = "Google Cloud Project ID where CI/CD pipelines will execute."
}

variable "region" {
  type        = string
  description = "Google Cloud region for resource deployment."
  default     = "us-central1"
}

variable "host_connection_name" {
  description = "Name of the host connection you created in Cloud Build"
  type        = string
}

variable "repository_name" {
  description = "Name of the repository you'd like to connect to Cloud Build"
  type        = string
}

variable "telemetry_logs_filter" {
  type        = string
  description = "Log Sink filter for capturing telemetry data. Captures logs with the `traceloop.association.properties.log_type` attribute set to `tracing`."
{%- if "adk" in cookiecutter.tags %}
  default     = "labels.service_name=\"{{cookiecutter.project_name}}\" labels.type=\"agent_telemetry\""
{%- else %}
  default     = "jsonPayload.attributes.\"traceloop.association.properties.log_type\"=\"tracing\" jsonPayload.resource.attributes.\"service.name\"=\"{{cookiecutter.project_name}}\""
{%- endif %}
}

variable "feedback_logs_filter" {
  type        = string
  description = "Log Sink filter for capturing feedback data. Captures logs where the `log_type` field is `feedback`."
  default     = "jsonPayload.log_type=\"feedback\""
}

{% if cookiecutter.deployment_target == 'cloud_run' %}
variable "cloud_run_app_roles" {
  description = "List of roles to assign to the Cloud Run app service account"
{% elif cookiecutter.deployment_target == 'agent_engine' %}
variable "agentengine_sa_roles" {
  description = "List of roles to assign to the Agent Engine service account"
{% endif %}
  type        = list(string)
  default = [
{%- if cookiecutter.deployment_target == 'cloud_run' %}
    "roles/run.invoker",
{%- endif %}
    "roles/aiplatform.user",
    "roles/discoveryengine.editor",
    "roles/logging.logWriter",
    "roles/cloudtrace.agent",
    "roles/storage.admin"
  ]
}

variable "cicd_roles" {
  description = "List of roles to assign to the CICD runner service account in the CICD project"
  type        = list(string)
  default = [
{%- if cookiecutter.deployment_target == 'cloud_run' %}
    "roles/run.invoker",
{%- endif %}
    "roles/storage.admin",
    "roles/aiplatform.user",
    "roles/discoveryengine.editor",
    "roles/logging.logWriter",
    "roles/cloudtrace.agent",
    "roles/artifactregistry.writer",
    "roles/cloudbuild.builds.builder"
  ]
}

variable "cicd_sa_deployment_required_roles" {
  description = "List of roles to assign to the CICD runner service account for the Staging and Prod projects."
  type        = list(string)
  default = [
{%- if cookiecutter.deployment_target == 'cloud_run' %}
    "roles/run.developer",
{%- endif %}    
    "roles/iam.serviceAccountUser",
    "roles/aiplatform.user",
    "roles/storage.admin"
  ]
}

{% if cookiecutter.data_ingestion %}

variable "pipeline_cron_schedule" {
  type        = string
  description = "Cron expression defining the schedule for automated data ingestion."
  default     = "0 0 * * 0" # Run at 00:00 UTC every Sunday
}

variable "pipelines_roles" {
  description = "List of roles to assign to the Vertex AI Pipelines service account"
  type        = list(string)
  default = [
    "roles/storage.admin",
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
{% if cookiecutter.datastore_type == "vertex_ai_search" %}
variable "data_store_region" {
  type        = string
  description = "Google Cloud region for resource deployment."
  default     = "us"
}
{% elif cookiecutter.datastore_type == "vertex_ai_vector_search" %}
variable "vector_search_embedding_size" {
  type = number
  description = "The number of dimensions for the embeddings."
  default = 768
}

variable "vector_search_approximate_neighbors_count" {
  type = number
  description = "The approximate number of neighbors to return."
  default = 150
}

variable "vector_search_min_replica_count" {
  type = number
  description = "The min replica count for vector search instance"
  default = 1
}

variable "vector_search_max_replica_count" {
  type = number
  description = "The max replica count for vector search instance"
  default = 1
}

variable "vector_search_shard_size" {
  description = "The shard size of the vector search instance"
  type = string
  default = "SHARD_SIZE_SMALL"
}

variable "vector_search_machine_type" {
  description = "The machine type for the vector search instance"
  type = string
  default = "e2-standard-2"
}
{% endif %}
{% endif %}
