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

terraform {
  required_version = ">= 1.0.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 7.13.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.7.0"
    }
{%- if cookiecutter.deployment_target == 'gke' %}
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.37.0"
    }
{%- endif %}
{%- if cookiecutter.data_ingestion and cookiecutter.datastore_type == "vertex_ai_search" %}
    null = {
      source  = "hashicorp/null"
      version = "~> 3.2.0"
    }
    external = {
      source  = "hashicorp/external"
      version = "~> 2.3.0"
    }
{%- endif %}
  }
}

provider "google" {
  alias                 = "dev_billing_override"
  billing_project       = var.dev_project_id
  region = var.region
  user_project_override = true
}

{%- if cookiecutter.deployment_target == 'gke' %}

data "google_client_config" "default" {}

provider "kubernetes" {
  host                   = "https://${google_container_cluster.app.endpoint}"
  token                  = data.google_client_config.default.access_token
  cluster_ca_certificate = base64decode(google_container_cluster.app.master_auth[0].cluster_ca_certificate)
}
{%- endif %}
