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
# Define local variables for roles


locals {
  cicd_runner_roles = [
    "roles/owner",
  ]
  
  e2e_project_roles = [
    "roles/owner", 
  ]
}

# Create a service account for CICD runner
resource "google_service_account" "cicd_runner_sa" {
  project      = var.cicd_runner_project_id
  account_id   = "cicd-tests-runner-sa"
  display_name = "Service Account for CI/CD Pipeline Runner"
  description  = "Used by Cloud Build to execute CI/CD pipelines"
}

# Grant necessary roles to the service account
resource "google_project_iam_member" "cicd_runner_roles" {
  for_each = toset(local.cicd_runner_roles)

  project = var.cicd_runner_project_id
  role    = each.key
  member  = "serviceAccount:${google_service_account.cicd_runner_sa.email}"
}

# Grant permissions to the service account for each environment project
resource "google_project_iam_member" "cicd_runner_e2e_project_roles" {
  for_each = {
    for idx, proj_role in flatten([
      for env, project_id in var.e2e_test_project_mapping : [
        for role in local.e2e_project_roles : {
          project = project_id
          env     = env
          role    = role
        }
      ]
    ]) : "${proj_role.env}-${proj_role.role}" => proj_role
  }

  project = each.value.project
  role    = each.value.role
  member  = "serviceAccount:${google_service_account.cicd_runner_sa.email}"
}
