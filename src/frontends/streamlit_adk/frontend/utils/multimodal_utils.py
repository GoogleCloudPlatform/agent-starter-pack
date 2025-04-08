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

import base64
from typing import Any
from urllib.parse import quote

import google.cloud.storage as storage
from google.genai import types

HELP_MESSAGE_MULTIMODALITY = (
    "For Gemini models to access the URIs you provide, store them in "
    "Google Cloud Storage buckets within the same project used by Gemini."
)

HELP_GCS_CHECKBOX = (
    "Enabling GCS upload will increase the app observability by avoiding"
    " forwarding and logging large byte strings within the app."
)


def format_content(parts: list[types.Part] | str) -> str:
    """Formats content as a string, handling both text and multimedia inputs."""
    # Check if parts is empty
    if not parts:
        return ""

    # Handle case where parts might be a string
    if isinstance(parts, str):
        return parts

    markdown = ""
    text = ""
    for part in parts:
        # Convert to Part object if it's a dictionary
        if isinstance(part, dict):
            part = types.Part.model_validate(part)
        if part.text:
            text = part.text
        # Handle inline data (images and other media)
        elif part.inline_data:
            if "image" in part.inline_data.mime_type:
                # For images, create an HTML img tag
                image_data = base64.b64encode(part.inline_data.data).decode("utf-8")
                image_markdown = f'<img src="data:{part.inline_data.mime_type};base64,{image_data}" width="100">'
                markdown = (
                    markdown
                    + f"""
- {image_markdown}
"""
                )
            else:
                # For other media types
                markdown = markdown + f"- Local media: {part.inline_data.mime_type}\n"
        # Handle file data (GCS files)
        elif part.file_data:
            if part.file_data.mime_type and "image" in part.file_data.mime_type:
                # GCS images
                image_url = gs_uri_to_https_url(part.file_data.file_uri)
                image_markdown = f'<img src="{image_url}" width="100">'
                markdown = (
                    markdown
                    + f"""
- {image_markdown}
"""
                )
            else:
                # GCS other media
                image_url = gs_uri_to_https_url(part.file_data.file_uri)
                markdown = (
                    markdown + f"- Remote media: "
                    f"[{part.file_data.file_uri}]({image_url})\n"
                )
    markdown = (
        markdown
        + f"""

{text}"""
    )
    return markdown


def get_gcs_blob_mime_type(gcs_uri: str) -> str | None:
    """Fetches the MIME type (content type) of a Google Cloud Storage blob.

    Args:
        gcs_uri (str): The GCS URI of the blob in the format "gs://bucket-name/object-name".

    Returns:
        str: The MIME type of the blob (e.g., "image/jpeg", "text/plain") if found,
             or None if the blob does not exist or an error occurs.
    """
    storage_client = storage.Client()

    try:
        bucket_name, object_name = gcs_uri.replace("gs://", "").split("/", 1)

        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(object_name)
        blob.reload()
        return blob.content_type
    except Exception as e:
        print(f"Error retrieving MIME type for {gcs_uri}: {e}")
        return None  # Indicate failure


def get_parts_from_files(
    upload_gcs_checkbox: bool, uploaded_files: list[Any], gcs_uris: str
) -> list[types.Part]:
    """Processes uploaded files and GCS URIs to create a list of content parts."""
    parts = []
    # read from local directly
    if not upload_gcs_checkbox:
        for uploaded_file in uploaded_files:
            im_bytes = uploaded_file.read()
            if "image" in uploaded_file.type:
                # Create inline_data Part for images
                blob = types.Blob(
                    mime_type=uploaded_file.type,
                    data=base64.b64encode(im_bytes).decode("utf-8"),
                )
                parts.append(types.Part(inline_data=blob))
            else:
                # Create inline_data Part for other file types
                blob = types.Blob(
                    mime_type=uploaded_file.type,
                    data=base64.b64encode(im_bytes).decode("utf-8"),
                )
                parts.append(types.Part(inline_data=blob))

    # Process GCS URIs
    if gcs_uris != "":
        for uri in gcs_uris.split(","):
            mime_type = get_gcs_blob_mime_type(uri)
            if mime_type:
                # Create file_data Part for GCS URIs
                file_data = types.FileData(file_uri=uri, mime_type=mime_type)
                parts.append(types.Part(file_data=file_data))

    return parts


def upload_bytes_to_gcs(
    bucket_name: str,
    blob_name: str,
    file_bytes: bytes,
    content_type: str | None = None,
) -> str:
    """Uploads a bytes object to Google Cloud Storage and returns the GCS URI.

    Args:
        bucket_name: The name of the GCS bucket.
        blob_name: The desired name for the uploaded file in GCS.
        file_bytes: The file's content as a bytes object.
        content_type (optional): The MIME type of the file (e.g., "image/png").
            If not provided, GCS will try to infer it.

    Returns:
        str: The GCS URI (gs://bucket_name/blob_name) of the uploaded file.

    Raises:
        GoogleCloudError: If there's an issue with the GCS operation.
    """
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    blob.upload_from_string(data=file_bytes, content_type=content_type)
    # Construct and return the GCS URI
    gcs_uri = f"gs://{bucket_name}/{blob_name}"
    return gcs_uri


def gs_uri_to_https_url(gs_uri: str) -> str:
    """Converts a GS URI to an HTTPS URL without authentication.

    Args:
        gs_uri: The GS URI in the format gs://<bucket>/<object>.

    Returns:
        The corresponding HTTPS URL, or None if the GS URI is invalid.
    """

    if not gs_uri.startswith("gs://"):
        raise ValueError("Invalid GS URI format")

    gs_uri = gs_uri[5:]

    # Extract bucket and object names, then URL encode the object name
    bucket_name, object_name = gs_uri.split("/", 1)
    object_name = quote(object_name)

    # Construct the HTTPS URL
    https_url = f"https://storage.mtls.cloud.google.com/{bucket_name}/{object_name}"
    return https_url


def upload_files_to_gcs(st: Any, bucket_name: str, files_to_upload: list[Any]) -> None:
    """Upload multiple files to Google Cloud Storage and store URIs in session state."""
    bucket_name = bucket_name.replace("gs://", "")
    uploaded_uris = []
    for file in files_to_upload:
        if file:
            file_bytes = file.read()
            gcs_uri = upload_bytes_to_gcs(
                bucket_name=bucket_name,
                blob_name=file.name,
                file_bytes=file_bytes,
                content_type=file.type,
            )
            uploaded_uris.append(gcs_uri)
    st.session_state.uploader_key += 1
    st.session_state["gcs_uris_to_be_sent"] = ",".join(uploaded_uris)
