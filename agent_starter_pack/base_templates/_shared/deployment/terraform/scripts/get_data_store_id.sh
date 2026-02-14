#!/bin/bash
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

# External data source script for Terraform.
# Reads JSON from stdin (with project_id, location, collection_id, display_name),
# outputs JSON to stdout with the data_store_id.
#
# Usage (via Terraform external data source):
#   data "external" "data_store_id" {
#     program = ["bash", "${path.module}/scripts/get_data_store_id.sh"]
#     query = {
#       project_id    = var.project_id
#       location      = var.data_store_region
#       collection_id = var.project_name
#       display_name  = var.project_name
#     }
#   }

set -euo pipefail

# Read JSON input from stdin
INPUT=$(cat)

PROJECT_ID=$(echo "${INPUT}" | python3 -c "import sys, json; print(json.load(sys.stdin)['project_id'])")
LOCATION=$(echo "${INPUT}" | python3 -c "import sys, json; print(json.load(sys.stdin)['location'])" <<< "${INPUT}")
COLLECTION_ID=$(echo "${INPUT}" | python3 -c "import sys, json; print(json.load(sys.stdin)['collection_id'])" <<< "${INPUT}")
DISPLAY_NAME=$(echo "${INPUT}" | python3 -c "import sys, json; print(json.load(sys.stdin)['display_name'])" <<< "${INPUT}")

TOKEN=$(gcloud auth application-default print-access-token 2>/dev/null || gcloud auth print-access-token)

# Use regional endpoint for non-global locations
if [ "${LOCATION}" = "global" ]; then
  API_BASE="https://discoveryengine.googleapis.com"
else
  API_BASE="https://${LOCATION}-discoveryengine.googleapis.com"
fi

PARENT="projects/${PROJECT_ID}/locations/${LOCATION}/collections/${COLLECTION_ID}"

RESPONSE=$(curl -s -X GET \
  "${API_BASE}/v1alpha/${PARENT}/dataConnectors" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "x-goog-user-project: ${PROJECT_ID}" \
  -H "Content-Type: application/json")

DATA_STORE_ID=$(echo "${RESPONSE}" | python3 -c "
import sys, json
data = json.load(sys.stdin)
for c in data.get('dataConnectors', []):
    if c.get('displayName') == '${DISPLAY_NAME}':
        entities = c.get('entities', [])
        if entities:
            ds = entities[0].get('dataStore', '')
            # Extract data store ID from full resource name
            # Format: projects/X/locations/Y/collections/Z/dataStores/ID
            parts = ds.split('/')
            if 'dataStores' in parts:
                idx = parts.index('dataStores')
                print(parts[idx + 1])
                break
" 2>/dev/null || true)

if [ -z "${DATA_STORE_ID}" ]; then
  DATA_STORE_ID="pending-creation"
fi

# Output JSON for Terraform external data source
echo "{\"data_store_id\": \"${DATA_STORE_ID}\"}"
