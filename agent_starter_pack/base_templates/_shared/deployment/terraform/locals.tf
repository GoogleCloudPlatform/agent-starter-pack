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

locals {
  cicd_services = [
    "cloudbuild.googleapis.com",
{%- if cookiecutter.datastore_type == "vertex_ai_search" %}
    "discoveryengine.googleapis.com",
{%- endif %}
    "aiplatform.googleapis.com",
    "serviceusage.googleapis.com",
{%- if cookiecutter.language == "python" %}
    "bigquery.googleapis.com",
{%- endif %}
    "cloudresourcemanager.googleapis.com",
    "cloudtrace.googleapis.com",
    "telemetry.googleapis.com",
{%- if cookiecutter.datastore_type == "vertex_ai_vector_search" %}
    "vectorsearch.googleapis.com",
{%- endif %}
{%- if cookiecutter.is_adk and cookiecutter.session_type == "cloud_sql" %}
    "sqladmin.googleapis.com",
{%- endif %}
  ]

  deploy_project_services = [
    "aiplatform.googleapis.com",
{%- if cookiecutter.deployment_target != 'gke' %}
    "run.googleapis.com",
{%- endif %}
{%- if cookiecutter.deployment_target == "gke" %}
    "compute.googleapis.com",
    "container.googleapis.com",
{%- endif %}
{%- if cookiecutter.datastore_type == "vertex_ai_search" %}
    "discoveryengine.googleapis.com",
{%- endif %}
    "cloudresourcemanager.googleapis.com",
    "iam.googleapis.com",
{%- if cookiecutter.language == "python" %}
    "bigquery.googleapis.com",
{%- endif %}
    "serviceusage.googleapis.com",
    "logging.googleapis.com",
    "cloudtrace.googleapis.com",
    "telemetry.googleapis.com",
{%- if cookiecutter.datastore_type == "vertex_ai_vector_search" %}
    "vectorsearch.googleapis.com",
{%- endif %}
{%- if cookiecutter.is_adk and cookiecutter.session_type == "cloud_sql" %}
    "sqladmin.googleapis.com",
    "secretmanager.googleapis.com"
{%- endif %}
  ]

  deploy_project_ids = {
    prod    = var.prod_project_id
    staging = var.staging_project_id
  }

  all_project_ids = [
    var.cicd_runner_project_id,
    var.prod_project_id,
    var.staging_project_id
  ]

}

