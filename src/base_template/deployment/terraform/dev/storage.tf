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

provider "google" {
  region = var.region
  user_project_override = true
}

resource "google_storage_bucket" "logs_data_bucket" {
  name                        = "${var.dev_project_id}-${var.project_name}-logs-data"
  location                    = var.region
  project                     = var.dev_project_id
  uniform_bucket_level_access = true

  depends_on = [resource.google_project_service.services]
}

{% if cookiecutter.data_ingestion %}
resource "google_storage_bucket" "data_ingestion_PIPELINE_GCS_ROOT" {
  name                        = "${var.dev_project_id}-${var.project_name}-rag"
  location                    = var.region
  project                     = var.dev_project_id
  uniform_bucket_level_access = true
  force_destroy               = true

  depends_on = [resource.google_project_service.services]
}

{% if cookiecutter.datastore_type == "vertex_ai_search" %}
resource "google_discovery_engine_data_store" "data_store_dev" {
  location                    = var.data_store_region
  project                     = var.dev_project_id
  data_store_id               = "${var.project_name}-datastore"
  display_name                = "${var.project_name}-datastore"
  industry_vertical           = "GENERIC"
  content_config              = "NO_CONTENT"
  solution_types              = ["SOLUTION_TYPE_SEARCH"]
  create_advanced_site_search = false
  provider                    = google.dev_billing_override
  depends_on             = [resource.google_project_service.services]
}

resource "google_discovery_engine_search_engine" "search_engine_dev" {
  project        = var.dev_project_id
  engine_id      = "${var.project_name}-search"
  collection_id  = "default_collection"
  location       = google_discovery_engine_data_store.data_store_dev.location
  display_name   = "Search Engine App Staging"
  data_store_ids = [google_discovery_engine_data_store.data_store_dev.data_store_id]
  search_engine_config {
    search_tier = "SEARCH_TIER_ENTERPRISE"
  }
  provider      = google.dev_billing_override
}
{% elif cookiecutter.datastore_type == "vertex_ai_vector_search" %}
resource "google_vertex_ai_index" "vector_search_index" {
  project = var.dev_project_id
  region = var.region
  display_name = "${var.project_name}-vector-search"
  description = "vector search index for test"
  metadata {
    config {
      dimensions = var.vector_search_embedding_size
      distance_measure_type = "DOT_PRODUCT_DISTANCE"
      approximate_neighbors_count = var.vector_search_approximate_neighbors_count
      shard_size = var.vector_search_shard_size
      algorithm_config {
        tree_ah_config {
        }
      }
    }
  }
  index_update_method = "STREAM_UPDATE"
}

resource "google_vertex_ai_index_endpoint" "vector_search_index_endpoint" {
  project      = var.dev_project_id
  region       = var.region
  display_name = "${var.project_name}-vector-search-endpoint"
  public_endpoint_enabled = true
  depends_on = [google_vertex_ai_index.vector_search_index]
}

resource "google_vertex_ai_index_endpoint_deployed_index" "vector_search_index_deployment" {
    index_endpoint = google_vertex_ai_index_endpoint.vector_search_index_endpoint.id
    index = google_vertex_ai_index.vector_search_index.id
    deployed_index_id = replace("${var.project_name}_deployed_index", "-", "_")
    dedicated_resources {
      machine_spec {
        machine_type = var.vector_search_machine_type
      }
      min_replica_count = var.vector_search_min_replica_count
      max_replica_count = var.vector_search_max_replica_count
    }
    depends_on = [
      google_vertex_ai_index.vector_search_index,
      google_vertex_ai_index_endpoint.vector_search_index_endpoint
    ]
}

resource "google_storage_bucket" "vector_search_data_bucket" {
  name                        = "${var.dev_project_id}-${var.project_name}-vs"
  location                    = var.region
  project                     = var.dev_project_id
  uniform_bucket_level_access = true
  force_destroy               = true

  depends_on = [resource.google_project_service.services]
}
{% endif %}
{% endif %}
