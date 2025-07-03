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

resource "google_project_service" "cicd_services" {
  count              = length(local.cicd_services)
  project            = var.cicd_runner_project_id
  service            = local.cicd_services[count.index]
  disable_on_destroy = false
}

resource "google_project_service" "deploy_project_services" {
  for_each = {
    for pair in setproduct(keys(local.deploy_project_ids), local.deploy_project_services) :
    "${pair[0]}_${replace(pair[1], ".", "_")}" => {
      project = local.deploy_project_ids[pair[0]]
      service = pair[1]
    }
  }
  project            = each.value.project
  service            = each.value.service
  disable_on_destroy = false
}

# Enable Cloud Resource Manager API for the CICD runner project
resource "google_project_service" "cicd_cloud_resource_manager_api" {
  project            = var.cicd_runner_project_id
  service            = "cloudresourcemanager.googleapis.com"
  disable_on_destroy = false
}
