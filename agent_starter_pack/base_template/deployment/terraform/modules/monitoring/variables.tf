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

variable "project_id" {
  type        = string
  description = "Google Cloud Project ID for resource deployment."
}

variable "project_name" {
  type        = string
  description = "Project name used as a base for resource naming"
}

variable "alert_notification_email" {
  type        = string
  description = "Email address for alert notifications. Leave empty for console-only alerts."
  default     = ""
}

variable "latency_alert_threshold_ms" {
  type        = number
  description = "P95 latency threshold in milliseconds for alerting. P95 means 95% of requests complete faster than this threshold."
  default     = 3000
}

variable "error_rate_alert_threshold" {
  type        = number
  description = "Error count threshold per 5-minute window for alerting."
  default     = 10
}

variable "retriever_latency_p99_threshold_ms" {
  type        = number
  description = "P99 retriever latency threshold in milliseconds for alerting. P99 means 99% of retrieval operations complete faster than this threshold."
  default     = 10000
}

variable "agent_error_rate_threshold_per_sec" {
  type        = number
  description = "Agent error rate threshold in errors per second for alerting (Cloud Run agents)."
  default     = 0.5
}
