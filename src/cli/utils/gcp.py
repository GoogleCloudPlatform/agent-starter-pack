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

# ruff: noqa: E722
import subprocess

import google.auth
from google.api_core.client_options import ClientOptions
from google.api_core.gapic_v1.client_info import ClientInfo
from google.cloud.aiplatform import initializer
from google.cloud.aiplatform_v1beta1.services.prediction_service import (
    PredictionServiceClient,
)
from google.cloud.aiplatform_v1beta1.types.prediction_service import (
    CountTokensRequest,
)

from src.cli.utils.version import PACKAGE_NAME, get_current_version


def get_user_agent() -> str:
    """Returns custom user agent header tuple (version, agent string)."""
    version = get_current_version()
    return f"{version}-{PACKAGE_NAME}/{version}-{PACKAGE_NAME}"


def get_client_info() -> ClientInfo:
    """Returns ClientInfo with custom user agent."""
    user_agent = get_user_agent()
    return ClientInfo(client_library_version=user_agent, user_agent=user_agent)


def get_dummy_request(project_id: str) -> CountTokensRequest:
    """Creates a simple test request for Gemini."""
    return CountTokensRequest(
        contents=[{"role": "user", "parts": [{"text": "Hi"}]}],
        endpoint=f"projects/{project_id}/locations/global/publishers/google/models/gemini-2.0-flash",
    )


def verify_vertex_connection(
    project_id: str,
    location: str = "us-central1",
) -> None:
    """Verifies Vertex AI connection with a test Gemini request."""
    credentials, _ = google.auth.default()
    client = PredictionServiceClient(
        credentials=credentials,
        client_options=ClientOptions(
            api_endpoint=f"{location}-aiplatform.googleapis.com"
        ),
        client_info=get_client_info(),
        transport=initializer.global_config._api_transport,
    )
    request = get_dummy_request(project_id=project_id)
    client.count_tokens(request=request)


def verify_credentials() -> dict:
    """Verify GCP credentials and return current project and account."""
    try:
        # Get credentials and project
        credentials, project = google.auth.default()

        # Try multiple methods to get account email
        account = None

        # Method 1: Try _account attribute
        if hasattr(credentials, "_account"):
            account = credentials._account

        # Method 2: Try service_account_email
        if not account and hasattr(credentials, "service_account_email"):
            account = credentials.service_account_email

        # Method 3: Try getting from token info if available
        if not account and hasattr(credentials, "id_token"):
            try:
                import jwt

                decoded = jwt.decode(
                    credentials.id_token, options={"verify_signature": False}
                )
                account = decoded.get("email")
            except:
                pass

        # Method 4: Try getting from gcloud config as fallback
        if not account:
            try:
                result = subprocess.run(
                    ["gcloud", "config", "get-value", "account"],
                    capture_output=True,
                    text=True,
                )
                account = result.stdout.strip()
            except:
                pass

        # Fallback if all methods fail
        if not account:
            account = "Unknown account"

        return {"project": project, "account": account}
    except Exception as e:
        raise Exception(f"Failed to verify GCP credentials: {e!s}") from e
