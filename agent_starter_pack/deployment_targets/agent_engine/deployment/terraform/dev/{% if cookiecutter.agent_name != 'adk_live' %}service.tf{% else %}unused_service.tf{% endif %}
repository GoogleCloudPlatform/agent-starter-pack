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

# Read base64-encoded dummy source tarball from GCS for initial Agent Engine creation
# CI/CD pipelines will update with actual source code after creation
# Note: The file is already base64-encoded to avoid binary corruption when reading via Terraform
data "google_storage_bucket_object_content" "dummy_source_b64" {
  name   = "dummy/source-b64.txt"
  bucket = "agent-starter-pack"
}

resource "google_vertex_ai_reasoning_engine" "app" {
  display_name = var.project_name
  description  = "Agent deployed via Terraform"
  region       = var.region
  project      = var.dev_project_id

  spec {
{%- if cookiecutter.is_adk %}
    agent_framework = "google-adk"
{%- else %}
    agent_framework = "custom"
{%- endif %}
    service_account = google_service_account.app_sa.email

    deployment_spec {
      min_instances         = 1
      max_instances         = 10
      container_concurrency = 9

      resource_limits = {
        cpu    = "4"
        memory = "8Gi"
      }

      env {
        name  = "LOGS_BUCKET_NAME"
        value = google_storage_bucket.logs_data_bucket.name
      }

      env {
        name  = "OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT"
        value = "true"
      }

      env {
        name  = "GOOGLE_CLOUD_AGENT_ENGINE_ENABLE_TELEMETRY"
        value = "true"
      }
{%- if cookiecutter.data_ingestion %}
{%- if cookiecutter.datastore_type == "vertex_ai_search" %}

      env {
        name  = "DATA_STORE_ID"
        value = resource.google_discovery_engine_data_store.data_store_dev.data_store_id
      }

      env {
        name  = "DATA_STORE_REGION"
        value = var.data_store_region
      }
{%- elif cookiecutter.datastore_type == "vertex_ai_vector_search" %}

      env {
        name  = "VECTOR_SEARCH_INDEX"
        value = resource.google_vertex_ai_index.vector_search_index.id
      }

      env {
        name  = "VECTOR_SEARCH_INDEX_ENDPOINT"
        value = resource.google_vertex_ai_index_endpoint.vector_search_index_endpoint.id
      }

      env {
        name  = "VECTOR_SEARCH_BUCKET"
        value = "gs://${resource.google_storage_bucket.data_ingestion_PIPELINE_GCS_ROOT.name}"
      }
{%- endif %}
{%- endif %}
    }

    source_code_spec {
      inline_source {
        source_archive = trimspace(data.google_storage_bucket_object_content.dummy_source_b64.content)
      }

      python_spec {
        entrypoint_module  = "app.agent_engine_app"
        entrypoint_object  = "agent_engine"
        requirements_file  = "app/app_utils/.requirements.txt"
        version            = "3.12"
      }
    }
  }

  # This lifecycle block prevents Terraform from overwriting the source code when it's
  # updated by Agent Engine deployments outside of Terraform (e.g., via CI/CD pipelines)
  lifecycle {
    ignore_changes = [
      spec[0].source_code_spec,
    ]
  }

  # Make dependencies conditional to avoid errors.
  depends_on = [google_project_service.services]
}
