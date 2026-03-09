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

output "app_service_account_emails" {
  description = "Application service account emails by environment"
  value       = { for k, v in google_service_account.app_sa : k => v.email }
}

output "cicd_runner_service_account_email" {
  description = "CI/CD runner service account email"
  value       = google_service_account.cicd_runner_sa.email
}

output "logs_bucket_names" {
  description = "Logs storage bucket names by environment"
  value       = { for k, v in google_storage_bucket.logs_data_bucket : k => v.name }
}
{% if cookiecutter.deployment_target in ['cloud_run', 'gke'] %}
output "artifact_registry_repository" {
  description = "Artifact Registry repository ID"
  value       = google_artifact_registry_repository.repo-artifacts-genai.repository_id
}
{% endif %}
