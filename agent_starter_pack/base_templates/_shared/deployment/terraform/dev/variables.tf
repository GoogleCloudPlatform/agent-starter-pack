# Copyright 2026 Google LLC
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

variable "dev_project_id" {
  type        = string
  description = "**Dev** Google Cloud Project ID for resource deployment."
}

variable "region" {
  type        = string
  description = "Google Cloud region for resource deployment."
  default     = "us-central1"
}

variable "telemetry_logs_filter" {
  type        = string
  description = "Log Sink filter for capturing telemetry data. Captures logs with the `traceloop.association.properties.log_type` attribute set to `tracing`."
{%- if cookiecutter.is_adk %}
  default     = "labels.service_name=\"{{cookiecutter.project_name}}\" labels.type=\"agent_telemetry\""
{%- else %}
  default     = "jsonPayload.attributes.\"traceloop.association.properties.log_type\"=\"tracing\" jsonPayload.resource.attributes.\"service.name\"=\"{{cookiecutter.project_name}}\""
{%- endif %}
}

variable "feedback_logs_filter" {
  type        = string
  description = "Log Sink filter for capturing feedback data. Captures logs where the `log_type` field is `feedback`."
  default     = "jsonPayload.log_type=\"feedback\" jsonPayload.service_name=\"{{cookiecutter.project_name}}\""
}

variable "app_sa_roles" {
  description = "List of roles to assign to the application service account"
  type        = list(string)
  default = [

    "roles/aiplatform.user",
{%- if cookiecutter.datastore_type == "vertex_ai_search" %}
    "roles/discoveryengine.editor",
{%- endif %}
    "roles/logging.logWriter",
    "roles/cloudtrace.agent",
    "roles/storage.admin",
    "roles/serviceusage.serviceUsageConsumer",
{%- if cookiecutter.session_type == "cloud_sql" %}
    "roles/cloudsql.client",
    "roles/secretmanager.secretAccessor",
{%- endif %}
{%- if cookiecutter.bq_analytics %}
    "roles/bigquery.dataOwner",
    "roles/bigquery.jobUser",
{%- endif %}
  ]
}
