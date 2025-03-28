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

resource "google_service_account" "cicd_runner_sa" {
  account_id   = "${var.project_name}-cb"
  display_name = "CICD Runner SA"
  project      = var.cicd_runner_project_id
  depends_on   = [resource.google_project_service.cicd_services, resource.google_project_service.shared_services]
}
{% if cookiecutter.deployment_target == 'cloud_run' %}
resource "google_service_account" "cloud_run_app_sa" {
  for_each = local.deploy_project_ids

  account_id   = "${var.project_name}-cr"
  display_name = "Cloud Run Generative AI app SA"
  project      = each.value
  depends_on   = [resource.google_project_service.cicd_services, resource.google_project_service.shared_services]
}
{% endif %}

{% if cookiecutter.data_ingestion %}
# Service account to run Vertex AI pipeline
resource "google_service_account" "vertexai_pipeline_app_sa" {
  for_each = local.deploy_project_ids

  account_id   = "${var.project_name}-rag"
  display_name = "Vertex AI Pipeline app SA"
  project      = each.value
  depends_on   = [resource.google_project_service.cicd_services, resource.google_project_service.shared_services]
}
{% endif %}
