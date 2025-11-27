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
from __future__ import annotations

import os
import subprocess
import time
from typing import TYPE_CHECKING

# Suppress gRPC verbose logging
os.environ["GRPC_VERBOSITY"] = "NONE"

# Type hints only - no runtime import cost
if TYPE_CHECKING:
    from google.api_core.gapic_v1.client_info import ClientInfo
    from google.cloud.aiplatform_v1beta1.types.prediction_service import (
        CountTokensRequest,
    )
    from rich.console import Console

from agent_starter_pack.cli.utils.version import PACKAGE_NAME, get_current_version

# Lazy console - only create when needed
_console = None


def _get_console() -> Console:
    """Lazily initialize rich Console."""
    from rich.console import Console

    global _console
    if _console is None:
        _console = Console()
    return _console


_AUTH_ERROR_MESSAGE = (
    "Looks like you are not authenticated with Google Cloud.\n"
    "Please run: `gcloud auth login --update-adc`\n"
    "Then set your project: `gcloud config set project YOUR_PROJECT_ID`"
)


def enable_vertex_ai_api(
    project_id: str, auto_approve: bool = False, context: str | None = None
) -> bool:
    """Enable Vertex AI API with user confirmation and propagation waiting."""
    from rich.prompt import Confirm

    console = _get_console()
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
        # Lazy imports - only load when actually testing connection
        import google.auth
        from google.api_core.client_options import ClientOptions
        from google.cloud.aiplatform_v1beta1.services.prediction_service import (
            PredictionServiceClient,
        )

        credentials, _ = google.auth.default()
        client = PredictionServiceClient(
            credentials=credentials,
            client_options=ClientOptions(
                api_endpoint=f"{location}-aiplatform.googleapis.com"
            ),
            client_info=_get_client_info(context),
        )
        request = _get_dummy_request(project_id=project_id)
        client.count_tokens(request=request)
        return True
    except Exception:
        return False


def _get_user_agent(context: str | None = None) -> str:
    """Returns a custom user agent string."""
    version = get_current_version()
    prefix = "ag" if context == "agent-garden" else ""
    return f"{prefix}{version}-{PACKAGE_NAME}/{prefix}{version}-{PACKAGE_NAME}"


def _get_client_info(context: str | None = None) -> ClientInfo:
    """Returns ClientInfo with custom user agent."""
    from google.api_core.gapic_v1.client_info import ClientInfo

    user_agent = _get_user_agent(context)
    return ClientInfo(client_library_version=user_agent, user_agent=user_agent)


def _get_dummy_request(project_id: str) -> CountTokensRequest:
    """Creates a simple test request for Gemini."""
    from google.cloud.aiplatform_v1beta1.types.prediction_service import (
        CountTokensRequest,
    )

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

    # Lazy imports for retry after enabling API
    import google.auth
    from google.api_core.client_options import ClientOptions
    from google.api_core.exceptions import PermissionDenied
    from google.cloud.aiplatform_v1beta1.services.prediction_service import (
        PredictionServiceClient,
    )

    console = _get_console()

    # After enabling, test again with proper error handling
    credentials, _ = google.auth.default()
    client = PredictionServiceClient(
        credentials=credentials,
        client_options=ClientOptions(
            api_endpoint=f"{location}-aiplatform.googleapis.com"
        ),
        client_info=_get_client_info(context),
    )
    request = _get_dummy_request(project_id=project_id)

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
    # Lazy import google.auth only when verifying credentials
    import google.auth
    import google.auth.exceptions

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
