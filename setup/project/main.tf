locals {
  environments = ["dev", "uat", "prod"]
  required_apis = [
    "compute.googleapis.com",
    "servicemanagement.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "cloudbilling.googleapis.com",
    "iam.googleapis.com",
  ]
}

# --- Projects ---

resource "random_id" "project_suffix" {
  for_each = toset(local.environments)

  byte_length = 4
}

resource "google_project" "project" {
  for_each = toset(local.environments)

  name            = "${var.project_base_name}-${each.key}"
  project_id      = "${var.project_base_name}-${each.key}-${random_id.project_suffix[each.key].hex}"
  billing_account = var.billing_account
  org_id          = var.org_id
  labels = {
    environment = each.key
  }
}

# --- Service APIs ---

resource "google_project_service" "apis" {
  for_each = {
    for pair in setproduct(local.environments, local.required_apis) :
    "${pair[0]}-${pair[1]}" => {
      environment = pair[0]
      api         = pair[1]
    }
  }

  project = google_project.project[each.value.environment].project_id
  service = each.value.api

  # Prevent race conditions where the project is not ready yet
  depends_on = [google_project.project]
}

# --- VPC ---

resource "google_compute_network" "vpc" {
  for_each = toset(local.environments)

  project                 = google_project.project[each.key].project_id
  name                    = "default"
  auto_create_subnetworks = false

  # Ensure APIs are enabled before creating the network
  depends_on = [google_project_service.apis]
}

# --- Subnet ---

resource "google_compute_subnetwork" "subnet" {
  for_each = toset(local.environments)

  project                  = google_project.project[each.key].project_id
  name                     = "default"
  ip_cidr_range            = "10.0.0.0/20"
  network                  = google_compute_network.vpc[each.key].id
  region                   = var.region
  private_ip_google_access = true

  # Ensure the VPC is created first
  depends_on = [google_compute_network.vpc]
}

output "dev_project_id" {
  description = "The project ID of the dev environment."
  value       = google_project.project["dev"].project_id
}

output "uat_project_id" {
  description = "The project ID of the uat environment."
  value       = google_project.project["uat"].project_id
}

output "prod_project_id" {
  description = "The project ID of the prod environment."
  value       = google_project.project["prod"].project_id
}
