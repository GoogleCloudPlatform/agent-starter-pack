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

import os

from app.app_utils.gcs import create_bucket_if_not_exists


def setup_telemetry(project_id: str, location: str = "us-central1") -> str:
    """Configure OpenTelemetry and GenAI telemetry."""
    # Enable GenAI event capture
    os.environ.setdefault("GOOGLE_CLOUD_AGENT_ENGINE_ENABLE_TELEMETRY", "true")
    os.environ.setdefault("ADK_CAPTURE_MESSAGE_CONTENT_IN_SPANS", "false")
    os.environ.setdefault(
        "OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT", "NO_CONTENT"
    )

    # Configure telemetry upload to GCS
    os.environ.setdefault("OTEL_INSTRUMENTATION_GENAI_UPLOAD_FORMAT", "jsonl")
    os.environ.setdefault("OTEL_INSTRUMENTATION_GENAI_COMPLETION_HOOK", "upload")
    os.environ.setdefault(
        "OTEL_SEMCONV_STABILITY_OPT_IN", "gen_ai_latest_experimental"
    )

    # Set resource attributes
    commit_sha = os.environ.get("COMMIT_SHA", "dev")
    os.environ.setdefault(
        "OTEL_RESOURCE_ATTRIBUTES",
        f"service.namespace=myagent-1762901584,service.version={commit_sha}",
    )

    # Setup telemetry bucket
    bucket = os.environ.get("GENAI_TELEMETRY_BUCKET", f"{project_id}-genai-telemetry")
    path = os.environ.get("GENAI_TELEMETRY_PATH", "telemetry")

    create_bucket_if_not_exists(bucket_name=bucket, project=project_id, location=location)

    os.environ.setdefault(
        "OTEL_INSTRUMENTATION_GENAI_UPLOAD_BASE_PATH",
        f"gs://{bucket}/{path}",
    )

    return bucket
