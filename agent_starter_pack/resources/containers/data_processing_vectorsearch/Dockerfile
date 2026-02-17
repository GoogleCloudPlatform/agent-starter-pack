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

# Base image for data processing pipelines (Vertex AI Vector Search)
# Versions match agent_starter_pack/agents/agentic_rag/data_ingestion/pyproject.toml
FROM python:3.11-slim

# Prevent Python from writing .pyc files
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install packages in a single layer and clean up to reduce image size
RUN pip install --no-cache-dir \
    "backoff>=2.2.0" \
    "bigframes>=2.0.0" \
    "google-cloud-aiplatform>=1.80.0" \
    "google-cloud-bigquery>=3.0.0" \
    "google-cloud-pipeline-components>=2.19.0" \
    "google-cloud-vectorsearch>=0.4.0" \
    "kfp>=1.4.0" \
    "langchain-text-splitters>=0.3.0" \
    "markdownify>=0.14.0" \
    "swifter>=1.4.0" \
    # Clean up to reduce image size
    && pip cache purge \
    && rm -rf /root/.cache/pip \
    && find /usr/local -type d -name '__pycache__' -exec rm -rf {} + \
    && find /usr/local -type f -name '*.pyc' -delete \
    && find /usr/local -type d -name 'tests' -exec rm -rf {} + \
    && find /usr/local -type d -name 'test' -exec rm -rf {} +
