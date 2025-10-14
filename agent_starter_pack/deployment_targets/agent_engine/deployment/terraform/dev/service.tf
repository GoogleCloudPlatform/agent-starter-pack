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
  project_id = var.dev_project_id
}

resource "google_vertex_ai_reasoning_engine" "app" {
  display_name = var.project_name
  description  = "Agent deployed via Terraform"
  region       = var.region
  project      = var.dev_project_id

  spec {
    service_account = google_service_account.app_sa.email

    package_spec {
      python_version        = "3.11"
      pickle_object_gcs_uri = "gs://placeholder-bucket/placeholder.pkl"
      requirements_gcs_uri  = "gs://placeholder-bucket/requirements.txt"
    }
  }

  # This lifecycle block prevents Terraform from overwriting the spec when it's
  # updated by Agent Engine deployments outside of Terraform (e.g., via CI/CD pipelines)
  lifecycle {
    ignore_changes = [
      spec,
    ]
  }

  # Make dependencies conditional to avoid errors.
  depends_on = [resource.google_project_service.services]
}
