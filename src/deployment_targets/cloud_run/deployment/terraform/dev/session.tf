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

# This file handles AlloyDB session database setup for the dev environment

resource "google_compute_network" "default" {
  name                    = "${var.project_name}-alloydb-network"
  project                 = var.dev_project_id
  auto_create_subnetworks = false
  count                   = var.create_session_db ? 1 : 0
  depends_on = [resource.google_project_service.services]
}

resource "google_compute_subnetwork" "default" {
  name          = "${var.project_name}-alloydb-network"
  ip_cidr_range = "10.0.0.0/24"
  region        = var.region
  network       = google_compute_network.default[0].id
  project       = var.dev_project_id
  count         = var.create_session_db ? 1 : 0

  # This is required for Cloud Run VPC connectors
  purpose       = "PRIVATE"

  private_ip_google_access = true
}

resource "google_compute_global_address" "private_ip_alloc" {
  name          = "${var.project_name}-private-ip"
  project       = var.dev_project_id
  address_type  = "INTERNAL"
  purpose       = "VPC_PEERING"
  prefix_length = 16
  network       = google_compute_network.default[0].id
  count         = var.create_session_db ? 1 : 0

  depends_on = [resource.google_project_service.services]
}

resource "google_service_networking_connection" "vpc_connection" {
  network                 = google_compute_network.default[0].id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.private_ip_alloc[0].name]
  count                   = var.create_session_db ? 1 : 0
}

resource "google_alloydb_cluster" "session_db_cluster" {
  project    = var.dev_project_id
  cluster_id = "${var.project_name}-alloydb-cluster"
  location   = var.region
  count      = var.create_session_db ? 1 : 0

  network_config {
    network = google_compute_network.default[0].id
  }

  depends_on = [
    google_service_networking_connection.vpc_connection
  ]
}

resource "google_alloydb_instance" "session_db_instance" {
  cluster       = google_alloydb_cluster.session_db_cluster[0].name
  instance_id   = "${var.project_name}-alloydb-instance"
  instance_type = "PRIMARY"
  count         = var.create_session_db ? 1 : 0

  availability_type = "REGIONAL" # Regional redundancy

  machine_config {
    cpu_count = 2
  }
}

# Generate a random password for the database user
resource "random_password" "db_password" {
  length           = 16
  special          = true
  override_special = "!#$%&*()-_=+[]{}<>:?"
  count            = var.create_session_db ? 1 : 0
}

# Store the password in Secret Manager
resource "google_secret_manager_secret" "db_password" {
  project   = var.dev_project_id
  secret_id = "${var.project_name}-db-password"
  count     = var.create_session_db ? 1 : 0

  replication {
    auto {}
  }

  depends_on = [resource.google_project_service.services]
}

resource "google_secret_manager_secret_version" "db_password" {
  secret      = google_secret_manager_secret.db_password[0].id
  secret_data = random_password.db_password[0].result
  count       = var.create_session_db ? 1 : 0
}

resource "google_alloydb_user" "db_user" {
  cluster        = google_alloydb_cluster.session_db_cluster[0].name
  user_id        = "postgres"
  user_type      = "ALLOYDB_BUILT_IN"
  password       = random_password.db_password[0].result
  database_roles = ["alloydbsuperuser"]
  count          = var.create_session_db ? 1 : 0

  depends_on = [google_alloydb_instance.session_db_instance]
}
