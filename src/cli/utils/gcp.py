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
import os
import subprocess
import time

# Suppress gRPC verbose logging
os.environ["GRPC_VERBOSITY"] = "NONE"

import google.auth
from google.api_core.client_options import ClientOptions
from google.api_core.exceptions import PermissionDenied
from google.api_core.gapic_v1.client_info import ClientInfo
from google.cloud.aiplatform import initializer
from google.cloud.aiplatform_v1beta1.services.prediction_service import (
    PredictionServiceClient,
)
from google.cloud.aiplatform_v1beta1.types.prediction_service import (
    CountTokensRequest,
)
from rich.console import Console
from rich.prompt import Confirm

from src.cli.utils.version import PACKAGE_NAME, get_current_version

console = Console()

_AUTH_ERROR_MESSAGE = (
    "Looks like you are not authenticated with Google Cloud.\n"
    "Please run: `gcloud auth login --update-adc`\n"
    "Then set your project: `gcloud config set project YOUR_PROJECT_ID`"
)


def enable_vertex_ai_api(
    project_id: str, auto_approve: bool = False, context: str | None = None
) -> bool:
    """Enable Vertex AI API with user confirmation and propagation waiting."""
    api_name = "aiplatform.googleapis.com"

    # First test if API is already working with a direct connection
    if _test_vertex_ai_connection(project_id, context=context):
        return True

    if not auto_approve:
        console.print(
            f"Vertex AI API is not enabled in project '{project_id}'.", style="yellow"
        )
        console.print(
            "To continue, we need to enable the Vertex AI API.", style="yellow"
        )

        if not Confirm.ask(
            "Do you want to enable the Vertex AI API now?", default=True
        ):
            return False

    try:
        console.print("Enabling Vertex AI API...")
        subprocess.run(
            [
                "gcloud",
                "services",
                "enable",
                api_name,
                "--project",
                project_id,
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        console.print("✓ Vertex AI API enabled successfully")

        # Wait for API propagation
        console.print("⏳ Waiting for API availability to propagate...")
        max_wait_time = 180  # 3 minutes
        check_interval = 10  # 10 seconds
        start_time = time.time()

        while time.time() - start_time < max_wait_time:
            if _test_vertex_ai_connection(project_id, context=context):
                console.print("✓ Vertex AI API is now available")
                return True
            time.sleep(check_interval)
            console.print("⏳ Still waiting for API propagation...")

        console.print(
            "⚠️ API propagation took longer than expected, but continuing...",
            style="yellow",
        )
        return True

    except subprocess.CalledProcessError as e:
        console.print(f"Failed to enable Vertex AI API: {e.stderr}", style="bold red")
        return False


def _test_vertex_ai_connection(
    project_id: str, location: str = "us-central1", context: str | None = None
) -> bool:
    """Test Vertex AI connection without raising exceptions."""
    try:
        credentials, _ = google.auth.default()
        client = PredictionServiceClient(
            credentials=credentials,
            client_options=ClientOptions(
                api_endpoint=f"{location}-aiplatform.googleapis.com"
            ),
            client_info=get_client_info(context),
            transport=initializer.global_config._api_transport,
        )
        request = get_dummy_request(project_id=project_id)
        client.count_tokens(request=request)
        return True
    except Exception:
        return False


def get_user_agent(context: str | None = None) -> str:
    """Returns a custom user agent string."""
    version = get_current_version()
    prefix = "ag" if context == "agent-garden" else ""
    return f"{prefix}{version}-{PACKAGE_NAME}/{prefix}{version}-{PACKAGE_NAME}"


def get_client_info(context: str | None = None) -> ClientInfo:
    """Returns ClientInfo with custom user agent."""
    user_agent = get_user_agent(context)
    return ClientInfo(client_library_version=user_agent, user_agent=user_agent)


def get_dummy_request(project_id: str) -> CountTokensRequest:
    """Creates a simple test request for Gemini."""
    return CountTokensRequest(
        contents=[{"role": "user", "parts": [{"text": "Hi"}]}],
        endpoint=f"projects/{project_id}/locations/global/publishers/google/models/gemini-2.5-flash",
    )


def verify_vertex_connection(
    project_id: str,
    location: str = "us-central1",
    auto_approve: bool = False,
    context: str | None = None,
) -> None:
    """Verifies Vertex AI connection with a test Gemini request."""
    # First try direct connection - if it works, we're done
    if _test_vertex_ai_connection(project_id, location, context):
        return

    # If that failed, try to enable the API
    if not enable_vertex_ai_api(project_id, auto_approve, context):
        raise Exception("Vertex AI API is not enabled and user declined to enable it")

    # After enabling, test again with proper error handling
    credentials, _ = google.auth.default()
    client = PredictionServiceClient(
        credentials=credentials,
        client_options=ClientOptions(
            api_endpoint=f"{location}-aiplatform.googleapis.com"
        ),
        client_info=get_client_info(context),
        transport=initializer.global_config._api_transport,
    )
    request = get_dummy_request(project_id=project_id)

    try:
        client.count_tokens(request=request)
    except PermissionDenied as e:
        error_message = str(e)
        # Check if the error is specifically about API not being enabled
        if (
            "has not been used" in error_message
            and "aiplatform.googleapis.com" in error_message
        ):
            # This shouldn't happen since we checked above, but handle it gracefully
            console.print(
                "⚠️ API may still be propagating, retrying in 30 seconds...",
                style="yellow",
            )
            time.sleep(30)
            try:
                client.count_tokens(request=request)
            except PermissionDenied:
                raise Exception(
                    "Vertex AI API is enabled but not yet available. Please wait a few more minutes and try again."
                ) from e
        else:
            # Re-raise other permission errors
            raise


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
    except google.auth.exceptions.DefaultCredentialsError as e:
        # Authentication error - provide friendly message
        raise Exception(_AUTH_ERROR_MESSAGE) from e
    except Exception as e:
        # Check if the error message indicates authentication issues
        error_str = str(e).lower()
        if any(
            keyword in error_str for keyword in ["credential", "auth", "login", "token"]
        ):
            raise Exception(_AUTH_ERROR_MESSAGE) from e
        raise Exception(f"Failed to verify GCP credentials: {e!s}") from e
