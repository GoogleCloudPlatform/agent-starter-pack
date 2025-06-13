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


locals {
  # Assuming local.deploy_project_ids is already defined as a map with keys 'prod' and 'staging'
  # and values being the respective project IDs
  db_projects_to_create = var.create_session_db ? toset(keys(local.deploy_project_ids)) : toset([])
}


resource "google_compute_network" "default" {
  # Use for_each with the conditional set of projects
  for_each = local.db_projects_to_create


  name                    = "${var.project_name}-alloydb-network"
  project                 = local.deploy_project_ids[each.key]
  auto_create_subnetworks = false


  depends_on = [resource.google_project_service.deploy_project_services]
}


resource "google_compute_subnetwork" "default" {
  # Use the same conditional for_each pattern
  for_each = local.db_projects_to_create


  name          = "${var.project_name}-alloydb-network"
  ip_cidr_range = "10.0.0.0/24"
  region        = var.region
  network       = google_compute_network.default[each.key].id
  project       = local.deploy_project_ids[each.key]


  # This is required for Cloud Run VPC connectors
  purpose       = "PRIVATE"


  private_ip_google_access = true
}


resource "google_compute_global_address" "private_ip_alloc" {
  # Use the same conditional for_each pattern
  for_each = local.db_projects_to_create


  name          = "${var.project_name}-private-ip"
  project       = local.deploy_project_ids[each.key]
  address_type  = "INTERNAL"
  purpose       = "VPC_PEERING"
  prefix_length = 16
  network       = google_compute_network.default[each.key].id


  depends_on = [resource.google_project_service.deploy_project_services]
}


resource "google_service_networking_connection" "vpc_connection" {
  # Use the same conditional for_each pattern
  for_each = local.db_projects_to_create


  network                 = google_compute_network.default[each.key].id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.private_ip_alloc[each.key].name]
}


resource "google_alloydb_cluster" "session_db_cluster" {
  # Use the same conditional for_each pattern
  for_each = local.db_projects_to_create


  project    = local.deploy_project_ids[each.key]
  cluster_id = "${var.project_name}-alloydb-cluster"
  location   = var.region


  network_config {
    network = google_compute_network.default[each.key].id
  }


  depends_on = [
    google_service_networking_connection.vpc_connection
  ]
}


resource "google_alloydb_instance" "session_db_instance" {
  # Use the same conditional for_each pattern
  for_each = local.db_projects_to_create


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
  for_each = local.db_projects_to_create


  length           = 16
  special          = true
  override_special = "!#$%&*()-_=+[]{}<>:?"
}


# Store the password in Secret Manager
resource "google_secret_manager_secret" "db_password" {
  for_each = local.db_projects_to_create


  project   = local.deploy_project_ids[each.key]
  secret_id = "${var.project_name}-db-password"


  replication {
    auto {}
  }


  depends_on = [resource.google_project_service.deploy_project_services]
}


resource "google_secret_manager_secret_version" "db_password" {
  for_each = local.db_projects_to_create


  secret      = google_secret_manager_secret.db_password[each.key].id
  secret_data = random_password.db_password[each.key].result
}


resource "google_alloydb_user" "db_user" {
  for_each = local.db_projects_to_create


  cluster        = google_alloydb_cluster.session_db_cluster[each.key].name
  user_id        = "postgres"
  user_type      = "ALLOYDB_BUILT_IN"
  password       = random_password.db_password[each.key].result
  database_roles = ["alloydbsuperuser"]


  depends_on = [google_alloydb_instance.session_db_instance]
}
