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

# Create a service account for CICD runner
resource "google_service_account" "cicd_runner_sa" {
  project      = var.cicd_runner_project_id
  account_id   = "cicd-runner-sa"
  display_name = "Service Account for CI/CD Pipeline Runner"
  description  = "Used by Cloud Build to execute CI/CD pipelines"
}

# Grant necessary roles to the service account
resource "google_project_iam_member" "cicd_runner_roles" {
  for_each = toset([
    "roles/cloudbuild.builds.builder",
    "roles/logging.logWriter",
    "roles/storage.admin",
    "roles/artifactregistry.reader",
    "roles/artifactregistry.writer",
    "roles/iam.serviceAccountUser",
    "roles/aiplatform.user",
    "roles/discoveryengine.editor",
    "roles/cloudtrace.agent"

  ])

  project = var.cicd_runner_project_id
  role    = each.key
  member  = "serviceAccount:${google_service_account.cicd_runner_sa.email}"
}
