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

"""OpenTelemetry setup for AG2 agents on Google Cloud."""

import logging
import os

logger = logging.getLogger(__name__)


def setup_telemetry() -> str | None:
    """Configure OpenTelemetry tracing for AG2 agents.

    Sets up Cloud Trace export when running on Cloud Run or GKE.
    Locally, tracing is disabled by default to avoid requiring credentials.
    """
    bucket = os.environ.get("LOGS_BUCKET_NAME")

    if not os.getenv("K_SERVICE"):
        return bucket

    try:
        from opentelemetry import trace
        from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        provider = TracerProvider()
        provider.add_span_processor(BatchSpanProcessor(CloudTraceSpanExporter()))
        trace.set_tracer_provider(provider)
    except ImportError:
        logger.debug("OpenTelemetry Cloud Trace dependencies not installed, skipping")

    return bucket
