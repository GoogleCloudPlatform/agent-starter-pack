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

# Sets up a GCS Data Connector for Vertex AI Search via the Discovery Engine API.
# Idempotent: checks if the connector already exists before creating.
# After creation, triggers an initial sync via startConnectorRun.
#
# Usage: bash setup_data_connector.sh <project_id> <location> <collection_id> <data_connector_display_name> <gcs_uri> <refresh_interval>

set -euo pipefail

PROJECT_ID="${1:?Missing project_id}"
LOCATION="${2:?Missing location}"
COLLECTION_ID="${3:?Missing collection_id}"
DISPLAY_NAME="${4:?Missing data_connector_display_name}"
GCS_URI="${5:?Missing gcs_uri}"
REFRESH_INTERVAL="${6:-86400s}"

PARENT="projects/${PROJECT_ID}/locations/${LOCATION}/collections/${COLLECTION_ID}"

TOKEN=$(gcloud auth application-default print-access-token 2>/dev/null || gcloud auth print-access-token)

# Use regional endpoint for non-global locations
if [ "${LOCATION}" = "global" ]; then
  API_BASE="https://discoveryengine.googleapis.com"
else
  API_BASE="https://${LOCATION}-discoveryengine.googleapis.com"
fi

# Check if connector already exists by listing connectors and filtering by display name
EXISTING=$(curl -s -X GET \
  "${API_BASE}/v1alpha/${PARENT}/dataConnectors" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "x-goog-user-project: ${PROJECT_ID}" \
  -H "Content-Type: application/json")

CONNECTOR_NAME=$(echo "${EXISTING}" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    for c in data.get('dataConnectors', []):
        if c.get('displayName') == '${DISPLAY_NAME}':
            print(c['name'])
            break
except Exception:
    pass
" 2>/dev/null || true)

if [ -n "${CONNECTOR_NAME}" ]; then
  echo "Data connector '${DISPLAY_NAME}' already exists: ${CONNECTOR_NAME}"
  echo "Skipping creation."
  exit 0
fi

echo "Creating data connector '${DISPLAY_NAME}'..."

# Create data connector via setUpDataConnectorV2
RESPONSE=$(curl -s -X POST \
  "${API_BASE}/v1alpha/${PARENT}:setUpDataConnectorV2" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "x-goog-user-project: ${PROJECT_ID}" \
  -H "Content-Type: application/json" \
  -d "{
    \"dataConnector\": {
      \"displayName\": \"${DISPLAY_NAME}\",
      \"dataSource\": \"cloud_storage\",
      \"refreshInterval\": \"${REFRESH_INTERVAL}\",
      \"params\": {
        \"paths\": \"${GCS_URI}\"
      },
      \"entities\": [
        {
          \"entityName\": \"documents\"
        }
      ],
      \"staticIpEnabled\": false
    }
  }")

# Check for LRO
LRO_NAME=$(echo "${RESPONSE}" | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(data.get('name', ''))
" 2>/dev/null || true)

if [ -z "${LRO_NAME}" ]; then
  echo "Error: Failed to create data connector. Response:"
  echo "${RESPONSE}"
  exit 1
fi

echo "LRO started: ${LRO_NAME}"

# Poll LRO until complete
MAX_RETRIES=60
RETRY=0
while [ ${RETRY} -lt ${MAX_RETRIES} ]; do
  sleep 10
  RETRY=$((RETRY + 1))

  LRO_STATUS=$(curl -s -X GET \
    "${API_BASE}/v1alpha/${LRO_NAME}" \
    -H "Authorization: Bearer ${TOKEN}" \
    -H "x-goog-user-project: ${PROJECT_ID}")

  DONE=$(echo "${LRO_STATUS}" | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(data.get('done', False))
" 2>/dev/null || echo "False")

  if [ "${DONE}" = "True" ]; then
    echo "Data connector created successfully."

    # Trigger initial sync
    echo "Triggering initial connector sync..."
    bash "$(dirname "$0")/start_connector_run.sh" "${PROJECT_ID}" "${LOCATION}" "${COLLECTION_ID}"
    exit 0
  fi

  echo "Waiting for LRO to complete (attempt ${RETRY}/${MAX_RETRIES})..."
done

echo "Error: LRO did not complete within the timeout period."
exit 1
