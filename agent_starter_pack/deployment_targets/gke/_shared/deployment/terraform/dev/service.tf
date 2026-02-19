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
  project_id = var.dev_project_id
}

{%- if cookiecutter.language == "python" %}
{%- if cookiecutter.is_adk and cookiecutter.session_type == "cloud_sql" %}

# Generate a random password for the database user
resource "random_password" "db_password" {
  length           = 16
  special          = true
  override_special = "!#$%&*()-_=+[]{}<>:?"
}

# Cloud SQL Instance
resource "google_sql_database_instance" "session_db" {
  project          = var.dev_project_id
  name             = "${var.project_name}-db-dev"
  database_version = "POSTGRES_15"
  region           = var.region
  deletion_protection = false

  settings {
    tier = "db-custom-1-3840"

    backup_configuration {
      enabled = false # No backups for dev
    }

    # Enable IAM authentication
    database_flags {
      name  = "cloudsql.iam_authentication"
      value = "on"
    }
  }

  depends_on = [resource.google_project_service.services]
}

# Cloud SQL Database
resource "google_sql_database" "database" {
  project  = var.dev_project_id
  name     = "${var.project_name}" # Use project name for DB to avoid conflict with default 'postgres'
  instance = google_sql_database_instance.session_db.name
}

# Cloud SQL User
resource "google_sql_user" "db_user" {
  project  = var.dev_project_id
  name     = "${var.project_name}" # Use project name for user to avoid conflict with default 'postgres'
  instance = google_sql_database_instance.session_db.name
  password = google_secret_manager_secret_version.db_password.secret_data
}

# Store the password in Secret Manager
resource "google_secret_manager_secret" "db_password" {
  project   = var.dev_project_id
  secret_id = "${var.project_name}-db-password"

  replication {
    auto {}
  }

  depends_on = [resource.google_project_service.services]
}

resource "google_secret_manager_secret_version" "db_password" {
  secret      = google_secret_manager_secret.db_password.id
  secret_data = random_password.db_password.result
}

{%- endif %}
{%- endif %}

# VPC Network
resource "google_compute_network" "gke_network" {
  name                    = "${var.project_name}-network"
  project                 = var.dev_project_id
  auto_create_subnetworks = false

  depends_on = [resource.google_project_service.services]
}

# Subnet for GKE cluster
resource "google_compute_subnetwork" "gke_subnet" {
  name          = "${var.project_name}-subnet"
  project       = var.dev_project_id
  region        = var.region
  network       = google_compute_network.gke_network.id
  ip_cidr_range = "10.0.0.0/20"
}

# Firewall rule to allow internal traffic (metrics-server, pod-to-pod, etc.)
resource "google_compute_firewall" "allow_internal" {
  name    = "${var.project_name}-allow-internal"
  network = google_compute_network.gke_network.name
  project = var.dev_project_id

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
  name     = "${var.project_name}-dev"
  location = var.region
  project  = var.dev_project_id

  network    = google_compute_network.gke_network.name
  subnetwork = google_compute_subnetwork.gke_subnet.name

  # Enable Autopilot mode
  enable_autopilot = true

  deletion_protection = false

  # Make dependencies conditional to avoid errors.
  depends_on = [
    resource.google_project_service.services,
  ]
}
