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

# Create a manual Cloud Build trigger for scheduled cleanup
resource "google_cloudbuild_trigger" "scheduled_cleanup" {
  name            = "scheduled-cleanup"
  project         = var.cicd_runner_project_id
  location        = var.region  # Must match repository connection region
  description     = "Daily cleanup of test resources (Agent Engines, Cloud SQL, Vector Search, Service Accounts)"
  service_account = google_service_account.cicd_runner_sa.id

  # Manual trigger - will be invoked by Cloud Scheduler
  source_to_build {
    repository = local.repository_path
    ref        = "refs/heads/main"
    repo_type  = "GITHUB"
  }

  filename           = ".cloudbuild/scheduled-cleanup.yaml"
  include_build_logs = "INCLUDE_BUILD_LOGS_UNSPECIFIED"
}

# Create Cloud Scheduler job to trigger cleanup daily at 3 AM UTC
resource "google_cloud_scheduler_job" "daily_cleanup" {
  name             = "daily-cleanup-trigger"
  project          = var.cicd_runner_project_id
  region           = "europe-west1"  # Cloud Scheduler doesn't support europe-west4
  description      = "Triggers daily cleanup of test resources at 3 AM UTC"
  schedule         = "0 3 * * *"
  time_zone        = "UTC"
  attempt_deadline = "1800s"  # 30 minutes (max allowed)

  http_target {
    http_method = "POST"
    uri         = "https://cloudbuild.googleapis.com/v1/projects/${var.cicd_runner_project_id}/locations/${var.region}/triggers/${google_cloudbuild_trigger.scheduled_cleanup.trigger_id}:run"

    oauth_token {
      service_account_email = google_service_account.cicd_runner_sa.email
    }

    # For manual triggers with source_to_build, no request body is needed
    # The trigger configuration already specifies the source
    body = base64encode(jsonencode({}))
  }

  retry_config {
    retry_count = 3
  }

  depends_on = [
    google_project_service.cloud_scheduler_api,
    google_cloudbuild_trigger.scheduled_cleanup
  ]
}
