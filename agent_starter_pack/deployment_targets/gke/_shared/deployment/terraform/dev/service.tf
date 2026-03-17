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

resource "kubernetes_secret_v1" "db_password" {
  metadata {
    name      = "${var.project_name}-db-password"
    namespace = kubernetes_namespace_v1.app.metadata[0].name
  }
  data = {
    password = random_password.db_password.result
  }
  depends_on = [kubernetes_namespace_v1.app]
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

resource "kubernetes_deployment_v1" "app" {
  metadata {
    name      = var.project_name
    namespace = kubernetes_namespace_v1.app.metadata[0].name
    labels = {
      app = var.project_name
    }
  }

  spec {
    selector {
      match_labels = {
        app = var.project_name
      }
    }

    template {
      metadata {
        labels = {
          app = var.project_name
        }
      }

      spec {
        service_account_name = kubernetes_service_account_v1.app.metadata[0].name

        container {
          name  = var.project_name
          image = "us-docker.pkg.dev/cloudrun/container/hello"

          port {
            container_port = 8080
            protocol       = "TCP"
          }

{%- if cookiecutter.language != "python" %}
          env {
            name  = "GOOGLE_CLOUD_PROJECT"
            value = "{{ cookiecutter.google_cloud_project }}"
          }
          env {
            name  = "GOOGLE_CLOUD_LOCATION"
            value = "global"
          }
          env {
            name  = "GOOGLE_GENAI_USE_VERTEXAI"
            value = "True"
          }
{%- endif %}

          env {
            name  = "LOGS_BUCKET_NAME"
            value = google_storage_bucket.logs_data_bucket.name
          }

{%- if cookiecutter.language != "java" %}
          env {
            name  = "OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT"
            value = "NO_CONTENT"
          }
{%- endif %}

{%- if cookiecutter.language == "python" %}
{%- if cookiecutter.is_adk and cookiecutter.session_type == "cloud_sql" %}
          env {
            name  = "INSTANCE_CONNECTION_NAME"
            value = google_sql_database_instance.session_db.connection_name
          }
          env {
            name = "DB_PASS"
            value_from {
              secret_key_ref {
                name = "${var.project_name}-db-password"
                key  = "password"
              }
            }
          }
          env {
            name  = "DB_NAME"
            value = var.project_name
          }
          env {
            name  = "DB_USER"
            value = var.project_name
          }
{%- endif %}
{%- if cookiecutter.data_ingestion %}
{%- if cookiecutter.datastore_type == "vertex_ai_search" %}
          env {
            name  = "DATA_STORE_ID"
            value = data.external.data_store_id_dev.result.data_store_id
          }
          env {
            name  = "DATA_STORE_REGION"
            value = var.data_store_region
          }
{%- elif cookiecutter.datastore_type == "vertex_ai_vector_search" %}
          env {
            name  = "VECTOR_SEARCH_COLLECTION"
            value = "projects/${var.dev_project_id}/locations/${var.vector_search_location}/collections/${var.vector_search_collection_id}"
          }
{%- endif %}
{%- endif %}
{%- if cookiecutter.bq_analytics %}
          env {
            name  = "BQ_ANALYTICS_DATASET_ID"
            value = google_bigquery_dataset.telemetry_dataset.dataset_id
          }
          env {
            name  = "BQ_ANALYTICS_GCS_BUCKET"
            value = google_storage_bucket.logs_data_bucket.name
          }
          env {
            name  = "BQ_ANALYTICS_CONNECTION_ID"
            value = "${var.region}.${google_bigquery_connection.genai_telemetry_connection.connection_id}"
          }
{%- endif %}
{%- endif %}

          resources {
            requests = {
              cpu    = "0.5"
              memory = "1Gi"
            }
            limits = {
              cpu    = "1"
              memory = "2Gi"
            }
          }

          startup_probe {
            tcp_socket {
              port = 8080
            }
            initial_delay_seconds = 10
            period_seconds        = 10
            failure_threshold     = 18
          }

          readiness_probe {
            tcp_socket {
              port = 8080
            }
            initial_delay_seconds = 15
            period_seconds        = 10
          }

          liveness_probe {
            tcp_socket {
              port = 8080
            }
            initial_delay_seconds = 15
            period_seconds        = 20
          }

{%- if cookiecutter.language == "python" %}
{%- if cookiecutter.is_adk and cookiecutter.session_type == "cloud_sql" %}
          volume_mount {
            name       = "cloudsql"
            mount_path = "/cloudsql"
          }
{%- endif %}
{%- endif %}
        }

{%- if cookiecutter.language == "python" %}
{%- if cookiecutter.is_adk and cookiecutter.session_type == "cloud_sql" %}
        container {
          name  = "cloud-sql-proxy"
          image = "gcr.io/cloud-sql-connectors/cloud-sql-proxy:2.14.3"
          args = [
            "--structured-logs",
            "--unix-socket=/cloudsql",
            google_sql_database_instance.session_db.connection_name,
          ]

          security_context {
            run_as_non_root = true
          }

          resources {
            requests = {
              cpu    = "0.5"
              memory = "512Mi"
            }
          }

          volume_mount {
            name       = "cloudsql"
            mount_path = "/cloudsql"
          }
        }

        volume {
          name = "cloudsql"
          empty_dir {}
        }
{%- endif %}
{%- endif %}
      }
    }
  }

  lifecycle {
    ignore_changes = [
      spec[0].template[0].spec[0].container[0].image,
    ]
  }

  depends_on = [kubernetes_namespace_v1.app]
}
