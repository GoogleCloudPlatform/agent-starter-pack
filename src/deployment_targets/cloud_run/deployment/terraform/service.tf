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

# Get project information to access the project number
data "google_project" "project" {
  for_each = local.db_projects_to_create

  project_id = local.deploy_project_ids[each.key]
}

resource "google_cloud_run_v2_service" "app_staging" {  
  name                = var.project_name
  location            = var.region
  project             = var.staging_project_id
  deletion_protection = false
  ingress             = "INGRESS_TRAFFIC_ALL"

  template {
    containers {
      # Placeholder, will be replaced by the CI/CD pipeline
      image = "us-docker.pkg.dev/cloudrun/container/hello"

      resources {
        limits = {
          cpu    = "4"
          memory = "8Gi"
        }
        cpu_idle = false
      }
{%- if cookiecutter.data_ingestion %}
{%- if cookiecutter.datastore_type == "vertex_ai_search" %}

      env {
        name  = "DATA_STORE_ID"
        value = resource.google_discovery_engine_data_store.data_store_staging.data_store_id
      }

      env {
        name  = "DATA_STORE_REGION"
        value = var.data_store_region
      }
{%- elif cookiecutter.datastore_type == "vertex_ai_vector_search" %}
      env {
        name  = "VECTOR_SEARCH_INDEX"
        value = resource.google_vertex_ai_index.vector_search_index_staging.id
      }

      env {
        name  = "VECTOR_SEARCH_INDEX_ENDPOINT"
        value = resource.google_vertex_ai_index_endpoint.vector_search_index_endpoint_staging.id
      }

      env {
        name  = "VECTOR_SEARCH_BUCKET"
        value = resource.google_storage_bucket.vector_search_data_bucket["staging"].url
      }
{%- endif %}
{%- endif %}

      dynamic "env" {
        for_each = var.create_session_db ? [1] : []
        content {
          name  = "DB_HOST"
          value = google_alloydb_instance.session_db_instance["staging"].ip_address
        }
      }

      # Use a `dynamic` block for the DB password env var.
      # This block is only included if the database is created.
      dynamic "env" {
        for_each = var.create_session_db ? [1] : []
        content {
          name = "DB_PASS"
          value_source {
            secret_key_ref {
              secret  = google_secret_manager_secret.db_password["staging"].secret_id
              version = "latest"
            }
          }
        }
      }
    }

    service_account                = google_service_account.cloud_run_app_sa["staging"].email
    max_instance_request_concurrency = 40

    scaling {
      min_instance_count = 1
      max_instance_count = 10
    }

    session_affinity = true

    # dynamic block for VPC access
    dynamic "vpc_access" {
      for_each = var.create_session_db ? [1] : []
      content {
        network_interfaces {
          network    = google_compute_network.default["staging"].id
          subnetwork = google_compute_subnetwork.default["staging"].id
        }
      }
    }
  }

  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }

  # This lifecycle block prevents Terraform from overwriting the container image when it's
  # updated by Cloud Run deployments outside of Terraform (e.g., via CI/CD pipelines)
  lifecycle {
    ignore_changes = [
      template[0].containers[0].image,
    ]
  }

  # Make dependencies conditional to avoid errors.
  depends_on = [google_project_service.deploy_project_services]
}

resource "google_cloud_run_v2_service" "app_prod" {  
  name                = var.project_name
  location            = var.region
  project             = var.prod_project_id
  deletion_protection = false
  ingress             = "INGRESS_TRAFFIC_ALL"

  template {
    containers {
      # Placeholder, will be replaced by the CI/CD pipeline
      image = "us-docker.pkg.dev/cloudrun/container/hello"

      resources {
        limits = {
          cpu    = "4"
          memory = "8Gi"
        }
        cpu_idle = false
      }
{%- if cookiecutter.data_ingestion %}
{%- if cookiecutter.datastore_type == "vertex_ai_search" %}

      env {
        name  = "DATA_STORE_ID"
        value = resource.google_discovery_engine_data_store.data_store_prod.data_store_id
      }

      env {
        name  = "DATA_STORE_REGION"
        value = var.data_store_region
      }
{%- elif cookiecutter.datastore_type == "vertex_ai_vector_search" %}
      env {
        name  = "VECTOR_SEARCH_INDEX"
        value = resource.google_vertex_ai_index.vector_search_index_prod.id
      }

      env {
        name  = "VECTOR_SEARCH_INDEX_ENDPOINT"
        value = resource.google_vertex_ai_index_endpoint.vector_search_index_endpoint_prod.id
      }

      env {
        name  = "VECTOR_SEARCH_BUCKET"
        value = resource.google_storage_bucket.vector_search_data_bucket["prod"].url
      }
{%- endif %}
{%- endif %}

      dynamic "env" {
        for_each = var.create_session_db ? [1] : []
        content {
          name  = "DB_HOST"
          value = google_alloydb_instance.session_db_instance["prod"].ip_address
        }
      }

      # Use a `dynamic` block for the DB password env var.
      # This block is only included if the database is created.
      dynamic "env" {
        for_each = var.create_session_db ? [1] : []
        content {
          name = "DB_PASS"
          value_source {
            secret_key_ref {
              secret  = google_secret_manager_secret.db_password["prod"].secret_id
              version = "latest"
            }
          }
        }
      }
    }

    service_account                = google_service_account.cloud_run_app_sa["prod"].email
    max_instance_request_concurrency = 40

    scaling {
      min_instance_count = 1
      max_instance_count = 10
    }

    session_affinity = true

    # dynamic block for VPC access
    dynamic "vpc_access" {
      for_each = var.create_session_db ? [1] : []
      content {
        network_interfaces {
          network    = google_compute_network.default["prod"].id
          subnetwork = google_compute_subnetwork.default["prod"].id
        }
      }
    }
  }

  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }

  # This lifecycle block prevents Terraform from overwriting the container image when it's
  # updated by Cloud Run deployments outside of Terraform (e.g., via CI/CD pipelines)
  lifecycle {
    ignore_changes = [
      template[0].containers[0].image,
    ]
  }

  # Make dependencies conditional to avoid errors.
  depends_on = [google_project_service.deploy_project_services]
}
