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

# GKE Cluster
resource "google_container_cluster" "primary" {
  for_each = local.deploy_project_ids

  name     = "${var.project_name}-gke-cluster"
  location = var.region
  project  = local.deploy_project_ids[each.key]

  # We can't create a cluster with no node pool defined, but we want to use
  # a separately managed node pool. So we create the smallest possible default
  # node pool and immediately delete it.
  remove_default_node_pool = true
  initial_node_count       = 1

  network    = google_compute_network.default[each.key].id
  subnetwork = google_compute_subnetwork.default[each.key].id

  depends_on = [google_project_service.deploy_project_services]
}

resource "google_container_node_pool" "primary" {
  for_each = local.deploy_project_ids

  name       = "${var.project_name}-node-pool"
  location   = var.region
  cluster    = google_container_cluster.primary[each.key].name
  project    = local.deploy_project_ids[each.key]
  node_count = 1

  node_config {
    preemptible  = true
    machine_type = "e2-medium"

    # Google recommends custom service accounts that have cloud-platform scope and permissions granted via IAM Roles.
    service_account = google_service_account.gke_sa[each.key].email
    oauth_scopes = [
      "https://www.googleapis.com/auth/cloud-platform"
    ]
  }
}

# Service account for GKE nodes
resource "google_service_account" "gke_sa" {
  for_each = local.deploy_project_ids

  account_id   = "${var.project_name}-gke-sa"
  display_name = "GKE Service Account"
  project      = local.deploy_project_ids[each.key]
}

# IAM role for GKE service account
resource "google_project_iam_member" "gke_sa_roles" {
  for_each = toset([
    "roles/monitoring.metricWriter",
    "roles/monitoring.viewer",
    "roles/logging.logWriter",
  ])

  project = var.staging_project_id
  role    = each.key
  member  = "serviceAccount:${google_service_account.gke_sa["staging"].email}"
}

resource "google_project_iam_member" "gke_sa_roles_prod" {
  for_each = toset([
    "roles/monitoring.metricWriter",
    "roles/monitoring.viewer",
    "roles/logging.logWriter",
  ])

  project = var.prod_project_id
  role    = each.key
  member  = "serviceAccount:${google_service_account.gke_sa["prod"].email}"
}