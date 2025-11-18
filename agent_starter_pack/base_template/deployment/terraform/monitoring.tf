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

module "monitoring" {
  for_each = local.deploy_project_ids
  source   = "./modules/monitoring"

  project_id                         = each.value
  project_name                       = var.project_name
  alert_notification_email           = var.alert_notification_email
  latency_alert_threshold_ms         = var.latency_alert_threshold_ms
  error_rate_alert_threshold         = var.error_rate_alert_threshold
  retriever_latency_p99_threshold_ms = var.retriever_latency_p99_threshold_ms
  agent_error_rate_threshold_per_sec = var.agent_error_rate_threshold_per_sec
}
