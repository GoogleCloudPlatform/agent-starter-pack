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

# Get project information to access the project number
data "google_project" "project" {
  for_each = local.deploy_project_ids

  project_id = local.deploy_project_ids[each.key]
}

{%- if cookiecutter.language == "python" %}
{%- if cookiecutter.is_adk and cookiecutter.session_type == "cloud_sql" %}

# Generate a random password for the database user
resource "random_password" "db_password" {
  for_each = local.deploy_project_ids

  length           = 16
  special          = true
  override_special = "!#$%&*()-_=+[]{}<>:?"
}

# Cloud SQL Instance
resource "google_sql_database_instance" "session_db" {
  for_each = local.deploy_project_ids

  project          = local.deploy_project_ids[each.key]
  name             = "${var.project_name}-db-${each.key}"
  database_version = "POSTGRES_15"
  region           = var.region
  deletion_protection = false # For easier teardown in starter packs

  settings {
    tier = "db-custom-1-3840"

    backup_configuration {
      enabled = true
      start_time = "03:00"
    }

    # Enable IAM authentication
    database_flags {
      name  = "cloudsql.iam_authentication"
      value = "on"
    }
  }

  depends_on = [google_project_service.deploy_project_services]
}

# Cloud SQL Database
resource "google_sql_database" "database" {
  for_each = local.deploy_project_ids

  project  = local.deploy_project_ids[each.key]
  name     = "${var.project_name}" # Use project name for DB to avoid conflict with default 'postgres'
  instance = google_sql_database_instance.session_db[each.key].name
}

# Cloud SQL User
resource "google_sql_user" "db_user" {
  for_each = local.deploy_project_ids

  project  = local.deploy_project_ids[each.key]
  name     = "${var.project_name}" # Use project name for user to avoid conflict with default 'postgres'
  instance = google_sql_database_instance.session_db[each.key].name
  password = random_password.db_password[each.key].result
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

{%- endif %}
{%- if cookiecutter.data_ingestion %}
{%- if cookiecutter.datastore_type == "vertex_ai_search" %}

locals {
  data_store_ids = {
    staging = data.external.data_store_id_staging.result.data_store_id
    prod    = data.external.data_store_id_prod.result.data_store_id
  }
}
{%- elif cookiecutter.datastore_type == "vertex_ai_vector_search" %}

locals {
  vector_search_collections = {
    for key, project_id in local.deploy_project_ids :
    key => "projects/${project_id}/locations/${var.vector_search_location}/collections/${var.vector_search_collection_id}"
  }
}
{%- endif %}
{%- endif %}
{%- endif %}

# VPC Network
resource "google_compute_network" "gke_network" {
  for_each = local.deploy_project_ids

  name                    = "${var.project_name}-network"
  project                 = each.value
  auto_create_subnetworks = false

  depends_on = [google_project_service.deploy_project_services]
}

# Subnet for GKE cluster
resource "google_compute_subnetwork" "gke_subnet" {
  for_each = local.deploy_project_ids

  name          = "${var.project_name}-subnet"
  project       = each.value
  region        = var.region
  network       = google_compute_network.gke_network[each.key].id
  ip_cidr_range = "10.0.0.0/20"
}

# Firewall rule to allow internal traffic (metrics-server, pod-to-pod, etc.)
resource "google_compute_firewall" "allow_internal" {
  for_each = local.deploy_project_ids

  name    = "${var.project_name}-allow-internal"
  network = google_compute_network.gke_network[each.key].name
  project = each.value

  allow {
    protocol = "tcp"
  }
  allow {
    protocol = "udp"
  }
  allow {
    protocol = "icmp"
  }

  source_ranges = ["10.0.0.0/8"]
}

# GKE Autopilot Cluster
resource "google_container_cluster" "app" {
  for_each = local.deploy_project_ids

  name     = "${var.project_name}-${each.key}"
  location = var.region
  project  = each.value

  network    = google_compute_network.gke_network[each.key].name
  subnetwork = google_compute_subnetwork.gke_subnet[each.key].name

  # Enable Autopilot mode
  enable_autopilot = true

  deletion_protection = false

  # Make dependencies conditional to avoid errors.
  depends_on = [
    google_project_service.deploy_project_services,
  ]
}
