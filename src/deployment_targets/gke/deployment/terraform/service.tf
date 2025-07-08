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

# Enable IAP API
resource "google_project_service" "iap_service" {
  for_each           = local.deploy_project_ids
  project            = each.value
  service            = "iap.googleapis.com"
  disable_on_destroy = false
  depends_on         = [google_project_service.deploy_project_services]
}

# Create OAuth Brand for IAP
resource "google_iap_brand" "project_brand" {
  for_each          = local.deploy_project_ids
  project           = google_project_service.iap_service[each.key].project
  support_email     = "security@${data.google_project.project[each.key].project_id}.iam.gserviceaccount.com" # Placeholder, user should verify this email/group exists
  application_title = "${var.project_name}-iap-${each.key}"
  depends_on        = [google_project_service.iap_service]
}

# Create OAuth Client for IAP
resource "google_iap_client" "project_client" {
  for_each     = local.deploy_project_ids
  display_name = "${var.project_name}-iap-client-${each.key}"
  brand        = google_iap_brand.project_brand[each.key].name
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

# AlloyDB Instance
resource "google_alloydb_instance" "session_db_instance" {
  for_each = local.deploy_project_ids
  
  cluster       = google_alloydb_cluster.session_db_cluster[each.key].name
  instance_id   = "${var.project_name}-alloydb-instance"
  instance_type = "PRIMARY"

  availability_type = "REGIONAL"

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

resource "kubernetes_secret" "db_credentials_staging" {
  provider = kubernetes.staging
  metadata {
    name = "${var.project_name}-db-credentials"
  }
  data = {
    DB_PASS = random_password.db_password["staging"].result
  }
  type = "Opaque"
}

resource "kubernetes_secret" "db_credentials_prod" {
  provider = kubernetes.prod
  metadata {
    name = "${var.project_name}-db-credentials"
  }
  data = {
    DB_PASS = random_password.db_password["prod"].result
  }
  type = "Opaque"
}

{%- endif %}

resource "google_container_cluster" "primary" {
  for_each = local.deploy_project_ids

  project  = each.value
  name     = "${var.project_name}-cluster-${each.key}"
  location = var.region
{%- if "adk" in cookiecutter.tags and cookiecutter.session_type == "alloydb" %}
  network    = google_compute_network.default[each.key].name
  subnetwork = google_compute_subnetwork.default[each.key].name
{%- endif %}

  enable_autopilot = true

  depends_on = [google_project_service.deploy_project_services]
}

# The following provider configurations assume that the Terraform principal
# has the necessary permissions to get the cluster credentials.
provider "kubernetes" {
  alias = "staging"

  host  = "https://container.googleapis.com/v1/projects/${var.staging_project_id}/locations/${var.region}/clusters/${google_container_cluster.primary["staging"].name}"
  token = data.google_client_config.staging.access_token
  cluster_ca_certificate = base64decode(google_container_cluster.primary["staging"].master_auth[0].cluster_ca_certificate)
}

provider "kubernetes" {
  alias = "prod"

  host  = "https://container.googleapis.com/v1/projects/${var.prod_project_id}/locations/${var.region}/clusters/${google_container_cluster.primary["prod"].name}"
  token = data.google_client_config.prod.access_token
  cluster_ca_certificate = base64decode(google_container_cluster.primary["prod"].master_auth[0].cluster_ca_certificate)
}

data "google_client_config" "staging" {
  project  = var.staging_project_id
  location = var.region
}

data "google_client_config" "prod" {
  project  = var.prod_project_id
  location = var.region
}

resource "kubernetes_manifest" "iap_backend_config_staging" {
  provider = kubernetes.staging
  manifest = {
    "apiVersion" = "cloud.google.com/v1"
    "kind"       = "BackendConfig"
    "metadata" = {
      "name"      = "${var.project_name}-backend-config"
      "namespace" = "default"
    }
    "spec" = {
      "iap" = {
        "enabled"            = true
        "oauth2ClientId"     = google_iap_client.project_client["staging"].client_id
        "oauth2ClientSecret" = google_iap_client.project_client["staging"].secret
      }
    }
  }
}

resource "kubernetes_manifest" "iap_backend_config_prod" {
  provider = kubernetes.prod
  manifest = {
    "apiVersion" = "cloud.google.com/v1"
    "kind"       = "BackendConfig"
    "metadata" = {
      "name"      = "${var.project_name}-backend-config"
      "namespace" = "default"
    }
    "spec" = {
      "iap" = {
        "enabled"            = true
        "oauth2ClientId"     = google_iap_client.project_client["prod"].client_id
        "oauth2ClientSecret" = google_iap_client.project_client["prod"].secret
      }
    }
  }
}

resource "kubernetes_deployment" "agent_staging" {
  provider = kubernetes.staging

  metadata {
    name = "${var.project_name}-deployment"
    labels = {
      app = var.project_name
    }
  }

  spec {
    replicas = 1
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
        container
          image = "us-docker.pkg.dev/cloudrun/container/hello" # Placeholder
          name  = var.project_name
          ports {
            container_port = 8080
          }
          {%- if "adk" in cookiecutter.tags and cookiecutter.session_type == "alloydb" %}
          env {
            name  = "DB_HOST"
            value = google_alloydb_instance.session_db_instance["staging"].ip_address
          }
          env {
            name = "DB_PASS"
            value_from {
              secret_key_ref {
                name = kubernetes_secret.db_credentials_staging.metadata[0].name
                key  = "DB_PASS"
              }
            }
          }
          {%- endif %}
        }
      }
    }
  }

  lifecycle {
    ignore_changes = [
      spec[0].template[0].spec[0].containers[0].image,
    ]
  }
}

resource "kubernetes_deployment" "agent_prod" {
  provider = kubernetes.prod

  metadata {
    name = "${var.project_name}-deployment"
    labels = {
      app = var.project_name
    }
  }

  spec {
    replicas = 1
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
        lifecycle {
    ignore_changes = [
      spec.template.spec.containers[0].image,
    ]
  }
}

resource "kubernetes_deployment" "agent_prod" {
  provider = kubernetes.prod

  metadata {
    name = "${var.project_name}-deployment"
    labels = {
      app = var.project_name
    }
  }

  spec {
    replicas = 1
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
        containers {
          image = "us-docker.pkg.dev/cloudrun/container/hello" # Placeholder
          name  = var.project_name
          ports {
            container_port = 8080
          }
          {%- if "adk" in cookiecutter.tags and cookiecutter.session_type == "alloydb" %}
          env {
            name  = "DB_HOST"
            value = google_alloydb_instance.session_db_instance["prod"].ip_address
          }
          env {
            name = "DB_PASS"
            value_from {
              secret_key_ref {
                name = kubernetes_secret.db_credentials_prod.metadata[0].name
                key  = "DB_PASS"
              }
            }
          }
          {%- endif %}
        }
      }
    }
  }

  lifecycle {
    ignore_changes = [
      spec.template.spec.containers[0].image,
    ]
  }
}

resource "kubernetes_service" "agent_staging" {
  provider = kubernetes.staging

  metadata {
    name = "${var.project_name}-service"
    annotations = {
      "cloud.google.com/backend-config" = "{\"default\": \"${kubernetes_manifest.iap_backend_config_staging.manifest.metadata.name}\"}"
      "cloud.google.com/neg"            = "{\"ingress\": true}"
    }
  }
  spec {
    selector = {
      app = kubernetes_deployment.agent_staging.spec[0].selector[0].match_labels.app
    }
    port {
      port        = 80
      target_port = 8080
    }
    type = "NodePort"
  }
}

resource "kubernetes_ingress_v1" "agent_staging" {
  provider = kubernetes.staging

  metadata {
    name = "${var.project_name}-ingress"
    annotations = {
      "kubernetes.io/ingress.class" = "gce"
    }
  }

  spec {
    default_backend {
      service {
        name = kubernetes_service.agent_staging.metadata[0].name
        port {
          number = 80
        }
      }
    }
  }
}

resource "kubernetes_service" "agent_prod" {
  provider = kubernetes.prod

  metadata {
    name = "${var.project_name}-service"
    annotations = {
      "cloud.google.com/backend-config" = "{\"default\": \"${kubernetes_manifest.iap_backend_config_prod.manifest.metadata.name}\"}"
      "cloud.google.com/neg"            = "{\"ingress\": true}"
    }
  }
  spec {
    selector = {
      app = kubernetes_deployment.agent_prod.spec[0].selector[0].match_labels.app
    }
    port {
      port        = 80
      target_port = 8080
    }
    type = "NodePort"
  }
}

resource "kubernetes_ingress_v1" "agent_prod" {
  provider = kubernetes.prod

  metadata {
    name = "${var.project_name}-ingress"
    annotations = {
      "kubernetes.io/ingress.class" = "gce"
    }
  }

  spec {
    default_backend {
      service {
        name = kubernetes_service.agent_prod.metadata[0].name
        port {
          number = 80
        }
      }
    }
  }
}