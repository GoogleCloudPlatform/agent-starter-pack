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

# Enable Cloud Resource Manager API for each project in e2e_test_project_mapping
resource "google_project_service" "cloud_resource_manager_api" {
  for_each = {
    "dev"     = var.e2e_test_project_mapping.dev
    "staging" = var.e2e_test_project_mapping.staging
    "prod"    = var.e2e_test_project_mapping.prod
  }

  project            = each.value
  service            = "cloudresourcemanager.googleapis.com"
  disable_on_destroy = false
}
