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

output "gke_cluster_names" {
  description = "GKE cluster names by environment"
  value       = { for k, v in google_container_cluster.app : k => v.name }
}

output "gke_cluster_endpoints" {
  description = "GKE cluster endpoints by environment"
  value       = { for k, v in google_container_cluster.app : k => v.endpoint }
}

{%- if cookiecutter.is_adk and cookiecutter.session_type == "cloud_sql" %}

output "instance_connection_names" {
  value = { for k, v in google_sql_database_instance.session_db : k => v.connection_name }
}
{%- endif %}
