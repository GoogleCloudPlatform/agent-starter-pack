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
  for_each = local.deploy_project_ids

  project_id = local.deploy_project_ids[each.key]
}

{%- if "adk" in cookiecutter.tags and cookiecutter.session_type == "alloydb" %}

# VPC Network for AlloyDB
resource "google_compute_network" "default" {
  for_each = local.deploy_project_ids
  
  name                    = "${var.project_name}-alloydb-network"
  project                 = local.deploy_project_ids[each.key]
  auto_create_subnetworks = false
  
  depends_on = [google_project_service.deploy_project_services]
}

# Subnet for AlloyDB
resource "google_compute_subnetwork" "default" {
  for_each = local.deploy_project_ids
  
  name          = "${var.project_name}-alloydb-network"
  ip_cidr_range = "10.0.0.0/24"
  region        = var.region
  network       = google_compute_network.default[each.key].id
  project       = local.deploy_project_ids[each.key]

  # This is required for Cloud Run VPC connectors
  purpose       = "PRIVATE"

  private_ip_google_access = true
}

# Private IP allocation for AlloyDB
resource "google_compute_global_address" "private_ip_alloc" {
  for_each = local.deploy_project_ids
  
  name          = "${var.project_name}-private-ip"
  project       = local.deploy_project_ids[each.key]
  address_type  = "INTERNAL"
  purpose       = "VPC_PEERING"
  prefix_length = 16
  network       = google_compute_network.default[each.key].id

  depends_on = [google_project_service.deploy_project_services]
}

# VPC connection for AlloyDB
resource "google_service_networking_connection" "vpc_connection" {
  for_each = local.deploy_project_ids
  
  network                 = google_compute_network.default[each.key].id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.private_ip_alloc[each.key].name]
}

# AlloyDB Cluster
resource "google_alloydb_cluster" "session_db_cluster" {
  for_each = local.deploy_project_ids
  
  project         = local.deploy_project_ids[each.key]
  cluster_id      = "${var.project_name}-alloydb-cluster"
  location        = var.region
  deletion_policy = "FORCE"

  network_config {
    network = google_compute_network.default[each.key].id
  }

  depends_on = [
    google_service_networking_connection.vpc_connection
  ]
}

# AlloyDB Instance
resource "google_alloydb_instance" "session_db_instance" {
  for_each = local.deploy_project_ids
  
  cluster       = google_alloydb_cluster.session_db_cluster[each.key].name
  instance_id   = "${var.project_name}-alloydb-instance"
  instance_type = "PRIMARY"

  availability_type = "REGIONAL" # Regional redundancy

  machine_config {
    cpu_count = 2
  }
}

# Generate a random password for the database user
resource "random_password" "db_password" {
  for_each = local.deploy_project_ids
  
  length           = 16
  special          = true
  override_special = "!#$%&*()-_=+[]{}<>:?"
}

# Store the password in Secret Manager
resource "google_secret_manager_secret" "db_password" {
  for_each = local.deploy_project_ids
  
  project   = local.deploy_project_ids[each.key]
  secret_id = "${var.project_name}-db-password"

  replication {
    auto {}
  }

  depends_on = [google_project_service.deploy_project_services]
}

resource "google_secret_manager_secret_version" "db_password" {
  for_each = local.deploy_project_ids
  
  secret      = google_secret_manager_secret.db_password[each.key].id
  secret_data = random_password.db_password[each.key].result
}

resource "google_alloydb_user" "db_user" {
  for_each = local.deploy_project_ids
  
  cluster        = google_alloydb_cluster.session_db_cluster[each.key].name
  user_id        = "postgres"
  user_type      = "ALLOYDB_BUILT_IN"
  password       = random_password.db_password[each.key].result
  database_roles = ["alloydbsuperuser"]

  depends_on = [google_alloydb_instance.session_db_instance]
}

{%- endif %}

resource "google_cloud_run_v2_service" "app_staging" {  
  name                = var.project_name
  location            = var.region
  project             = var.staging_project_id
  deletion_protection = false
  ingress             = "INGRESS_TRAFFIC_ALL"
  labels = {
{%- if "adk" in cookiecutter.tags %}
    "created-by"                  = "adk"
{%- endif %}
{%- if cookiecutter.agent_garden %}
    "deployed-with"               = "agent-garden"
{%- if cookiecutter.agent_sample_id %}
    "vertex-agent-sample-id"      = "{{cookiecutter.agent_sample_id}}"
    "vertex-agent-sample-publisher" = "{{cookiecutter.agent_sample_publisher}}"
{%- endif %}
{%- endif %}
  }

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

{%- if "adk" in cookiecutter.tags and cookiecutter.session_type == "alloydb" %}

      env {
        name  = "DB_HOST"
        value = google_alloydb_instance.session_db_instance["staging"].ip_address
      }

      env {
        name = "DB_PASS"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.db_password["staging"].secret_id
            version = "latest"
          }
        }
      }
{%- endif %}
    }

    service_account                = google_service_account.app_sa["staging"].email
    max_instance_request_concurrency = 40

    scaling {
      min_instance_count = 1
      max_instance_count = 10
    }

    session_affinity = true

{%- if "adk" in cookiecutter.tags and cookiecutter.session_type == "alloydb" %}
    # VPC access for AlloyDB connectivity
    vpc_access {
      network_interfaces {
        network    = google_compute_network.default["staging"].id
        subnetwork = google_compute_subnetwork.default["staging"].id
      }
    }
{%- endif %}
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
  labels = {
{%- if "adk" in cookiecutter.tags %}
    "created-by"                  = "adk"
{%- endif %}
{%- if cookiecutter.agent_garden %}
    "deployed-with"               = "agent-garden"
{%- if cookiecutter.agent_sample_id %}
    "vertex-agent-sample-id"      = "{{cookiecutter.agent_sample_id}}"
    "vertex-agent-sample-publisher" = "{{cookiecutter.agent_sample_publisher}}"
{%- endif %}
{%- endif %}
  }

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

{%- if "adk" in cookiecutter.tags and cookiecutter.session_type == "alloydb" %}

      env {
        name  = "DB_HOST"
        value = google_alloydb_instance.session_db_instance["prod"].ip_address
      }

      env {
        name = "DB_PASS"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.db_password["prod"].secret_id
            version = "latest"
          }
        }
      }
{%- endif %}
    }

    service_account                = google_service_account.app_sa["prod"].email
    max_instance_request_concurrency = 40

    scaling {
      min_instance_count = 1
      max_instance_count = 10
    }

    session_affinity = true

{%- if "adk" in cookiecutter.tags and cookiecutter.session_type == "alloydb" %}
    # VPC access for AlloyDB connectivity
    vpc_access {
      network_interfaces {
        network    = google_compute_network.default["prod"].id
        subnetwork = google_compute_subnetwork.default["prod"].id
      }
    }
{%- endif %}
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
