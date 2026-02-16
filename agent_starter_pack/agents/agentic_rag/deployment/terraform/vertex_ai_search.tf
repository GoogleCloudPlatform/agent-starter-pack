{% if cookiecutter.datastore_type == "vertex_ai_search" %}
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

# GCS bucket for documents to be ingested
resource "google_storage_bucket" "docs_bucket" {
  for_each                    = local.deploy_project_ids
  name                        = "${each.value}-${var.project_name}-docs"
  location                    = var.region
  project                     = each.value
  uniform_bucket_level_access = true
  force_destroy               = true

  depends_on = [resource.google_project_service.cicd_services, resource.google_project_service.deploy_project_services]
}

# Set up GCS Data Connector for staging
resource "null_resource" "data_connector_staging" {
  triggers = {
    project_id    = var.staging_project_id
    location      = var.data_store_region
    collection_id = "${var.project_name}-collection"
    scripts_dir   = "${path.module}/scripts"
  }

  provisioner "local-exec" {
    command = "uv run ${path.module}/scripts/setup_data_connector.py ${var.staging_project_id} ${var.data_store_region} ${var.project_name}-collection ${var.project_name} gs://${google_storage_bucket.docs_bucket["staging"].name} --refresh-interval ${var.data_connector_refresh_interval} --data-schema ${var.data_connector_data_schema}"
  }

  provisioner "local-exec" {
    when    = destroy
    command = "uv run ${self.triggers.scripts_dir}/delete_data_connector.py ${self.triggers.project_id} ${self.triggers.location} ${self.triggers.collection_id}"
  }

  depends_on = [google_storage_bucket.docs_bucket]
}

# Set up GCS Data Connector for prod
resource "null_resource" "data_connector_prod" {
  triggers = {
    project_id    = var.prod_project_id
    location      = var.data_store_region
    collection_id = "${var.project_name}-collection"
    scripts_dir   = "${path.module}/scripts"
  }

  provisioner "local-exec" {
    command = "uv run ${path.module}/scripts/setup_data_connector.py ${var.prod_project_id} ${var.data_store_region} ${var.project_name}-collection ${var.project_name} gs://${google_storage_bucket.docs_bucket["prod"].name} --refresh-interval ${var.data_connector_refresh_interval} --data-schema ${var.data_connector_data_schema}"
  }

  provisioner "local-exec" {
    when    = destroy
    command = "uv run ${self.triggers.scripts_dir}/delete_data_connector.py ${self.triggers.project_id} ${self.triggers.location} ${self.triggers.collection_id}"
  }

  depends_on = [google_storage_bucket.docs_bucket]
}

# Retrieve the auto-created data store ID for staging
data "external" "data_store_id_staging" {
  program = ["uv", "run", "${path.module}/scripts/get_data_store_id.py"]

  query = {
    project_id    = var.staging_project_id
    location      = var.data_store_region
    collection_id = "${var.project_name}-collection"
  }

  depends_on = [null_resource.data_connector_staging]
}

# Retrieve the auto-created data store ID for prod
data "external" "data_store_id_prod" {
  program = ["uv", "run", "${path.module}/scripts/get_data_store_id.py"]

  query = {
    project_id    = var.prod_project_id
    location      = var.data_store_region
    collection_id = "${var.project_name}-collection"
  }

  depends_on = [null_resource.data_connector_prod]
}

# Search engine app for staging — uses default_collection as Discovery Engine places data stores there regardless of connector collectionId
resource "google_discovery_engine_search_engine" "search_engine_staging" {
  project        = var.staging_project_id
  engine_id      = "${var.project_name}-search"
  collection_id  = "default_collection"
  location       = var.data_store_region
  display_name   = "Search Engine App Staging"
  data_store_ids = [data.external.data_store_id_staging.result.data_store_id]
  search_engine_config {
    search_tier = "SEARCH_TIER_ENTERPRISE"
  }
  provider   = google.staging_billing_override
  depends_on = [null_resource.data_connector_staging]
}

# Search engine app for prod — uses default_collection (see staging comment above)
resource "google_discovery_engine_search_engine" "search_engine_prod" {
  project        = var.prod_project_id
  engine_id      = "${var.project_name}-search"
  collection_id  = "default_collection"
  location       = var.data_store_region
  display_name   = "Search Engine App Prod"
  data_store_ids = [data.external.data_store_id_prod.result.data_store_id]
  search_engine_config {
    search_tier = "SEARCH_TIER_ENTERPRISE"
  }
  provider   = google.prod_billing_override
  depends_on = [null_resource.data_connector_prod]
}
{% endif %}
