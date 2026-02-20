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

  # Use private nodes (no external IPs) for security and org policy compliance
  private_cluster_config {
    enable_private_nodes    = true
    enable_private_endpoint = false
  }

  ip_allocation_policy {
    # Let GKE auto-assign secondary ranges for pods and services
  }

  deletion_protection = false

  # Make dependencies conditional to avoid errors.
  depends_on = [
    resource.google_project_service.services,
  ]
}

# Cloud Router for NAT gateway
resource "google_compute_router" "router" {
  name    = "${var.project_name}-router"
  project = var.dev_project_id
  region  = var.region
  network = google_compute_network.gke_network.id
}

# Cloud NAT for private GKE nodes to access the internet
resource "google_compute_router_nat" "nat" {
  name                               = "${var.project_name}-nat"
  project                            = var.dev_project_id
  router                             = google_compute_router.router.name
  region                             = var.region
  nat_ip_allocate_option             = "AUTO_ONLY"
  source_subnetwork_ip_ranges_to_nat = "ALL_SUBNETWORKS_ALL_IP_RANGES"
}

# Artifact Registry for container images
resource "google_artifact_registry_repository" "docker_repo" {
  location      = var.region
  repository_id = var.project_name
  format        = "DOCKER"
  project       = var.dev_project_id

  depends_on = [resource.google_project_service.services]
}

# Allow GKE Kubernetes ServiceAccount to impersonate the application GCP SA via Workload Identity
resource "google_service_account_iam_member" "workload_identity_binding" {
  service_account_id = google_service_account.app_sa.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "serviceAccount:${var.dev_project_id}.svc.id.goog[${var.project_name}/${var.project_name}]"

  depends_on = [google_container_cluster.app]
}

# --- Kubernetes Resources (managed by Terraform for dev) ---

resource "kubernetes_namespace_v1" "app" {
  metadata {
    name = var.project_name
  }
  depends_on = [google_container_cluster.app]
}

resource "kubernetes_service_account_v1" "app" {
  metadata {
    name      = var.project_name
    namespace = kubernetes_namespace_v1.app.metadata[0].name
    annotations = {
      "iam.gke.io/gcp-service-account" = "${var.project_name}-app@${var.dev_project_id}.iam.gserviceaccount.com"
    }
  }
}

resource "kubernetes_service_v1" "app" {
  metadata {
    name      = var.project_name
    namespace = kubernetes_namespace_v1.app.metadata[0].name
    labels = {
      app = var.project_name
    }
  }
  spec {
    type = "LoadBalancer"
    port {
      port        = 8080
      target_port = 8080
      protocol    = "TCP"
    }
    selector = {
      app = var.project_name
    }
  }
}

resource "kubernetes_horizontal_pod_autoscaler_v2" "app" {
  metadata {
    name      = var.project_name
    namespace = kubernetes_namespace_v1.app.metadata[0].name
    labels = {
      app = var.project_name
    }
  }
  spec {
    scale_target_ref {
      api_version = "apps/v1"
      kind        = "Deployment"
      name        = var.project_name
    }
    min_replicas = 2
    max_replicas = 10
    metric {
      type = "Resource"
      resource {
        name = "cpu"
        target {
          type                = "Utilization"
          average_utilization = 70
        }
      }
    }
  }
}

resource "kubernetes_pod_disruption_budget_v1" "app" {
  metadata {
    name      = var.project_name
    namespace = kubernetes_namespace_v1.app.metadata[0].name
    labels = {
      app = var.project_name
    }
  }
  spec {
    min_available = 1
    selector {
      match_labels = {
        app = var.project_name
      }
    }
  }
}
