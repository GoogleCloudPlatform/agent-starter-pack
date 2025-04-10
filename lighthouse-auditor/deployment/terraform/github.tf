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

provider "github" {
  token = data.google_secret_manager_secret_version.github_token.secret_data
  owner = var.repository_owner
}

data "google_secret_manager_secret_version" "github_token" {
  project = var.cicd_runner_project_id
  secret  = var.github_pat_secret_id
  version = "latest"
}

# Create the GitHub connection
resource "google_cloudbuildv2_connection" "github_connection" {
  count      = var.connection_exists ? 0 : 1
  project    = var.cicd_runner_project_id
  location   = var.region
  name       = var.host_connection_name

  github_config {
    app_installation_id = var.github_app_installation_id
    authorizer_credential {
      oauth_token_secret_version = "projects/${var.cicd_runner_project_id}/secrets/${var.github_pat_secret_id}/versions/latest"
    }
  }
  depends_on = [resource.google_project_service.cicd_services, resource.google_project_service.shared_services]
}

locals {
  connection_name = var.host_connection_name
}


# Try to get existing repo
data "github_repository" "existing_repo" {
  count = var.repository_exists ? 1 : 0
  full_name = "${var.repository_owner}/${var.repository_name}"
}

# Only create GitHub repo if it doesn't already exist
resource "github_repository" "repo" {
  count       = var.repository_exists ? 0 : 1
  name        = var.repository_name
  description = "Repository created by Terraform"
  visibility  = "private"

  has_issues      = true
  has_wiki        = false
  has_projects    = false
  has_downloads   = false

  allow_merge_commit = true
  allow_squash_merge = true
  allow_rebase_merge = true
  
  auto_init = false
}


resource "google_cloudbuildv2_repository" "repo" {
  project  = var.cicd_runner_project_id
  location = var.region
  name     = var.repository_name
  
  parent_connection = "projects/${var.cicd_runner_project_id}/locations/${var.region}/connections/${local.connection_name}"
  remote_uri       = "https://github.com/${var.repository_owner}/${var.repository_name}.git"
  depends_on = [
    resource.google_project_service.cicd_services,
    resource.google_project_service.shared_services,
    data.github_repository.existing_repo,
    github_repository.repo,
    google_cloudbuildv2_connection.github_connection,
  ]
}
