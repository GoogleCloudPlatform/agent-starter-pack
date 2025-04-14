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

import json
import logging
from collections.abc import Sequence
from typing import Any

import google.cloud.storage as storage
from google.cloud import logging as google_cloud_logging
from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import SpanExportResult


class CloudTraceLoggingSpanExporter(CloudTraceSpanExporter):
    """
    An extended version of CloudTraceSpanExporter that logs span data to Google Cloud Logging
    and handles large attribute values by storing them in Google Cloud Storage.

    This class helps bypass the 256 character limit of Cloud Trace for attribute values
    by leveraging Cloud Logging (which has a 256KB limit) and Cloud Storage for larger payloads.
    """

    def __init__(
        self,
        logging_client: google_cloud_logging.Client | None = None,
        storage_client: storage.Client | None = None,
        bucket_name: str | None = None,
        debug: bool = False,
        **kwargs: Any,
    ) -> None:
        """
        Initialize the exporter with Google Cloud clients and configuration.

        :param logging_client: Google Cloud Logging client
        :param storage_client: Google Cloud Storage client
        :param bucket_name: Name of the GCS bucket to store large payloads
        :param debug: Enable debug mode for additional logging
        :param kwargs: Additional arguments to pass to the parent class
        """
        super().__init__(**kwargs)
        self.debug = debug
        self.logging_client = logging_client or google_cloud_logging.Client(
            project=self.project_id
        )
        self.logger = self.logging_client.logger(__name__)
        self.storage_client = storage_client or storage.Client(project=self.project_id)
        self.bucket_name = (
            bucket_name or f"{self.project_id}-{{cookiecutter.project_name}}-logs-data"
        )
        self.bucket = self.storage_client.bucket(self.bucket_name)

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        """
        Export the spans to Google Cloud Logging and Cloud Trace.

        :param spans: A sequence of spans to export
        :return: The result of the export operation
        """
        for span in spans:
            span_context = span.get_span_context()
            trace_id = format(span_context.trace_id, "x")
            span_id = format(span_context.span_id, "x")
            span_dict = json.loads(span.to_json())

            span_dict["trace"] = f"projects/{self.project_id}/traces/{trace_id}"
            span_dict["span_id"] = span_id

            span_dict = self._process_large_attributes(
                span_dict=span_dict, span_id=span_id
            )

            if self.debug:
                print(span_dict)

            # Log the span data to Google Cloud Logging
{%- if "adk" in cookiecutter.tags %}
            self.logger.log_struct(
                span_dict,
                labels={
                    "type": "agent_telemetry",
                    "service_name": "{{cookiecutter.project_name}}",
                },
                severity="INFO",
            )
{%- else %}
            self.logger.log_struct(span_dict, severity="INFO")
{%- endif %}
        # Export spans to Google Cloud Trace using the parent class method
        return super().export(spans)

    def store_in_gcs(self, content: str, span_id: str) -> str:
        """
        Initiate storing large content in Google Cloud Storage/

        :param content: The content to store
        :param span_id: The ID of the span
        :return: The  GCS URI of the stored content
        """
        if not self.storage_client.bucket(self.bucket_name).exists():
            logging.warning(
                f"Bucket {self.bucket_name} not found. "
                "Unable to store span attributes in GCS."
            )
            return "GCS bucket not found"

        blob_name = f"spans/{span_id}.json"
        blob = self.bucket.blob(blob_name)

        blob.upload_from_string(content, "application/json")
        return f"gs://{self.bucket_name}/{blob_name}"

    def _process_large_attributes(self, span_dict: dict, span_id: str) -> dict:
        """
        Process large attribute values by storing them in GCS if they exceed the size
        limit of Google Cloud Logging.

        :param span_dict: The span data dictionary
        :param trace_id: The trace ID
        :param span_id: The span ID
        :return: The updated span dictionary
        """
        attributes = span_dict["attributes"]
        if len(json.dumps(attributes).encode()) > 255 * 1024:  # 250 KB
            # Separate large payload from other attributes
            attributes_payload = dict(attributes.items())
            attributes_retain = dict(attributes.items())

            # Store large payload in GCS
            gcs_uri = self.store_in_gcs(json.dumps(attributes_payload), span_id)
            attributes_retain["uri_payload"] = gcs_uri
            attributes_retain["url_payload"] = (
                f"https://storage.mtls.cloud.google.com/"
                f"{self.bucket_name}/spans/{span_id}.json"
            )

            span_dict["attributes"] = attributes_retain
            logging.info(
                "Length of payload span above 250 KB, storing attributes in GCS "
                "to avoid large log entry errors"
            )

        return span_dict
