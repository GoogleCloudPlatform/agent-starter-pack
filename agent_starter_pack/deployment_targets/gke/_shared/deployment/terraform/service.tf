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
    google_project_service.deploy_project_services,
  ]
}

# Cloud Router for NAT gateway
resource "google_compute_router" "router" {
  for_each = local.deploy_project_ids

  name    = "${var.project_name}-router"
  project = each.value
  region  = var.region
  network = google_compute_network.gke_network[each.key].id
}

# Cloud NAT for private GKE nodes to access the internet
resource "google_compute_router_nat" "nat" {
  for_each = local.deploy_project_ids

  name                               = "${var.project_name}-nat"
  project                            = each.value
  router                             = google_compute_router.router[each.key].name
  region                             = var.region
  nat_ip_allocate_option             = "AUTO_ONLY"
  source_subnetwork_ip_ranges_to_nat = "ALL_SUBNETWORKS_ALL_IP_RANGES"
}

# Artifact Registry for container images
resource "google_artifact_registry_repository" "docker_repo" {
  for_each = local.deploy_project_ids

  location      = var.region
  repository_id = var.project_name
  format        = "DOCKER"
  project       = each.value

  depends_on = [google_project_service.deploy_project_services]
}

# --- Kubernetes Resources (managed by Terraform for staging/prod) ---
# Note: Provider aliases require separate resource blocks per environment.

# Staging Kubernetes Resources

resource "kubernetes_namespace_v1" "app_staging" {
  provider = kubernetes.staging
  metadata {
    name = var.project_name
  }
  depends_on = [google_container_cluster.app]
}

resource "kubernetes_service_account_v1" "app_staging" {
  provider = kubernetes.staging
  metadata {
    name      = var.project_name
    namespace = kubernetes_namespace_v1.app_staging.metadata[0].name
    annotations = {
      "iam.gke.io/gcp-service-account" = google_service_account.app_sa["staging"].email
    }
  }
}

resource "kubernetes_service_v1" "app_staging" {
  provider = kubernetes.staging
  metadata {
    name      = var.project_name
    namespace = kubernetes_namespace_v1.app_staging.metadata[0].name
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

resource "kubernetes_horizontal_pod_autoscaler_v2" "app_staging" {
  provider = kubernetes.staging
  metadata {
    name      = var.project_name
    namespace = kubernetes_namespace_v1.app_staging.metadata[0].name
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

resource "kubernetes_pod_disruption_budget_v1" "app_staging" {
  provider = kubernetes.staging
  metadata {
    name      = var.project_name
    namespace = kubernetes_namespace_v1.app_staging.metadata[0].name
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

{%- if cookiecutter.language == "python" %}
{%- if cookiecutter.is_adk and cookiecutter.session_type == "cloud_sql" %}

resource "kubernetes_secret_v1" "db_password_staging" {
  provider = kubernetes.staging
  metadata {
    name      = "${var.project_name}-db-password"
    namespace = kubernetes_namespace_v1.app_staging.metadata[0].name
  }
  data = {
    password = random_password.db_password["staging"].result
  }
  depends_on = [kubernetes_namespace_v1.app_staging]
}
{%- endif %}
{%- endif %}

resource "kubernetes_deployment_v1" "app_staging" {
  provider = kubernetes.staging
  metadata {
    name      = var.project_name
    namespace = kubernetes_namespace_v1.app_staging.metadata[0].name
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
        service_account_name = kubernetes_service_account_v1.app_staging.metadata[0].name

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
            value = google_storage_bucket.logs_data_bucket[var.staging_project_id].name
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
            value = google_sql_database_instance.session_db["staging"].connection_name
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
            value = local.data_store_ids["staging"]
          }
          env {
            name  = "DATA_STORE_REGION"
            value = var.data_store_region
          }
{%- elif cookiecutter.datastore_type == "vertex_ai_vector_search" %}
          env {
            name  = "VECTOR_SEARCH_COLLECTION"
            value = local.vector_search_collections["staging"]
          }
{%- endif %}
{%- endif %}
{%- if cookiecutter.bq_analytics %}
          env {
            name  = "BQ_ANALYTICS_DATASET_ID"
            value = google_bigquery_dataset.telemetry_dataset["staging"].dataset_id
          }
          env {
            name  = "BQ_ANALYTICS_GCS_BUCKET"
            value = google_storage_bucket.logs_data_bucket[var.staging_project_id].name
          }
          env {
            name  = "BQ_ANALYTICS_CONNECTION_ID"
            value = "${var.region}.${google_bigquery_connection.genai_telemetry_connection["staging"].connection_id}"
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
            google_sql_database_instance.session_db["staging"].connection_name,
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

  depends_on = [kubernetes_namespace_v1.app_staging]
}

# Production Kubernetes Resources

resource "kubernetes_namespace_v1" "app_prod" {
  provider = kubernetes.prod
  metadata {
    name = var.project_name
  }
  depends_on = [google_container_cluster.app]
}

resource "kubernetes_service_account_v1" "app_prod" {
  provider = kubernetes.prod
  metadata {
    name      = var.project_name
    namespace = kubernetes_namespace_v1.app_prod.metadata[0].name
    annotations = {
      "iam.gke.io/gcp-service-account" = google_service_account.app_sa["prod"].email
    }
  }
}

resource "kubernetes_service_v1" "app_prod" {
  provider = kubernetes.prod
  metadata {
    name      = var.project_name
    namespace = kubernetes_namespace_v1.app_prod.metadata[0].name
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

resource "kubernetes_horizontal_pod_autoscaler_v2" "app_prod" {
  provider = kubernetes.prod
  metadata {
    name      = var.project_name
    namespace = kubernetes_namespace_v1.app_prod.metadata[0].name
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

resource "kubernetes_pod_disruption_budget_v1" "app_prod" {
  provider = kubernetes.prod
  metadata {
    name      = var.project_name
    namespace = kubernetes_namespace_v1.app_prod.metadata[0].name
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

{%- if cookiecutter.language == "python" %}
{%- if cookiecutter.is_adk and cookiecutter.session_type == "cloud_sql" %}

resource "kubernetes_secret_v1" "db_password_prod" {
  provider = kubernetes.prod
  metadata {
    name      = "${var.project_name}-db-password"
    namespace = kubernetes_namespace_v1.app_prod.metadata[0].name
  }
  data = {
    password = random_password.db_password["prod"].result
  }
  depends_on = [kubernetes_namespace_v1.app_prod]
}
{%- endif %}
{%- endif %}

resource "kubernetes_deployment_v1" "app_prod" {
  provider = kubernetes.prod
  metadata {
    name      = var.project_name
    namespace = kubernetes_namespace_v1.app_prod.metadata[0].name
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
        service_account_name = kubernetes_service_account_v1.app_prod.metadata[0].name

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
            value = google_storage_bucket.logs_data_bucket[var.prod_project_id].name
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
            value = google_sql_database_instance.session_db["prod"].connection_name
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
            value = local.data_store_ids["prod"]
          }
          env {
            name  = "DATA_STORE_REGION"
            value = var.data_store_region
          }
{%- elif cookiecutter.datastore_type == "vertex_ai_vector_search" %}
          env {
            name  = "VECTOR_SEARCH_COLLECTION"
            value = local.vector_search_collections["prod"]
          }
{%- endif %}
{%- endif %}
{%- if cookiecutter.bq_analytics %}
          env {
            name  = "BQ_ANALYTICS_DATASET_ID"
            value = google_bigquery_dataset.telemetry_dataset["prod"].dataset_id
          }
          env {
            name  = "BQ_ANALYTICS_GCS_BUCKET"
            value = google_storage_bucket.logs_data_bucket[var.prod_project_id].name
          }
          env {
            name  = "BQ_ANALYTICS_CONNECTION_ID"
            value = "${var.region}.${google_bigquery_connection.genai_telemetry_connection["prod"].connection_id}"
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
            google_sql_database_instance.session_db["prod"].connection_name,
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

  depends_on = [kubernetes_namespace_v1.app_prod]
}
