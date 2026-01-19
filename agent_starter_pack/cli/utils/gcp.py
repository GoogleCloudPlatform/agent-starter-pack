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

from __future__ import annotations

import subprocess
import sys
import time
from typing import TYPE_CHECKING

import requests

# Type hints only - no runtime import cost
if TYPE_CHECKING:
    from rich.console import Console

from agent_starter_pack.cli.utils.command import run_gcloud_command
from agent_starter_pack.cli.utils.version import PACKAGE_NAME, get_current_version

# API endpoint constants
RESOURCE_MANAGER_API_BASE = "https://cloudresourcemanager.googleapis.com"

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


def get_user_agent(context: str | None = None) -> str:
    """Returns a custom user agent string."""
    version = get_current_version()
    prefix = "ag" if context == "agent-garden" else ""
    return f"{prefix}{version}-{PACKAGE_NAME}/{prefix}{version}-{PACKAGE_NAME}"


def get_x_goog_api_client_header(context: str | None = None) -> str:
    """Build x-goog-api-client header matching SDK format."""
    user_agent = get_user_agent(context)
    python_version = (
        f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    )
    return f"{user_agent} gl-python/{python_version} gccl/{user_agent}"


def _get_credentials_and_token() -> tuple:
    """Get credentials, project, and valid token.

    Returns:
        Tuple of (credentials, project, token)
    """
    import google.auth
    import google.auth.transport.requests

    credentials, project = google.auth.default()

    # Refresh credentials to get valid token
    auth_req = google.auth.transport.requests.Request()
    credentials.refresh(auth_req)

    return credentials, project, credentials.token


def _get_account_from_credentials(credentials: object) -> str | None:
    """Try to get account email from credentials object."""
    return getattr(credentials, "service_account_email", None) or getattr(
        credentials, "_account", None
    )


def _get_account_from_gcloud() -> str | None:
    """Try to get account from gcloud config."""
    try:
        result = run_gcloud_command(
            ["config", "get-value", "account"],
            check=False,
            capture_output=True,
            timeout=10,
        )
        return result.stdout.strip() or None
    except Exception:
        return None


def _test_vertex_connection(
    project: str, token: str, context: str | None = None
) -> tuple[bool, str | None]:
    """Test Vertex AI connection using requests.

    Returns:
        Tuple of (success, error_message)
    """
    user_agent = get_user_agent(context)
    x_goog_api_client = get_x_goog_api_client_header(context)

    try:
        response = requests.post(
            f"https://us-central1-aiplatform.googleapis.com/v1beta1/projects/{project}/locations/global/publishers/google/models/gemini-2.5-flash:countTokens",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "User-Agent": user_agent,
                "x-goog-api-client": x_goog_api_client,
            },
            json={"contents": [{"role": "user", "parts": [{"text": "Hi"}]}]},
            timeout=10,
        )

        if response.status_code == 200:
            return True, None
        elif response.status_code == 403:
            error_data = response.json().get("error", {})
            error_message = error_data.get("message", "")
            if "aiplatform.googleapis.com" in error_message:
                return False, "api_not_enabled"
            return False, f"Permission denied: {error_message}"
        else:
            return False, f"Status {response.status_code}: {response.text}"
    except requests.exceptions.RequestException as e:
        return False, f"Network error: {e}"


def enable_vertex_ai_api(project_id: str, context: str | None = None) -> bool:
    """Enable Vertex AI API and wait for propagation."""
    console = _get_console()

    try:
        console.print("Enabling Vertex AI API...")
        run_gcloud_command(
            [
                "services",
                "enable",
                "aiplatform.googleapis.com",
                "--project",
                project_id,
            ],
            check=True,
            capture_output=True,
        )
        console.print("✓ Vertex AI API enabled successfully")

        # Wait for API propagation
        console.print("⏳ Waiting for API availability to propagate...")
        max_wait_time = 180  # 3 minutes
        check_interval = 10  # 10 seconds
        start_time = time.time()

        # Get fresh token for retries
        _, _, token = _get_credentials_and_token()

        while time.time() - start_time < max_wait_time:
            success, _ = _test_vertex_connection(project_id, token, context)
            if success:
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


def verify_credentials_and_vertex(
    context: str | None = None,
    auto_approve: bool = True,
) -> dict:
    """Verify credentials and Vertex AI connection.

    Uses google.auth + requests for lightweight verification.

    Args:
        context: Optional context for user agent (e.g., "agent-garden")
        auto_approve: If False and API not enabled, prompt user to enable it

    Returns:
        Dict with project and account info

    Raises:
        Exception on authentication or connection failure
    """
    import google.auth.exceptions
    from rich.prompt import Confirm

    try:
        # Get credentials and token
        credentials, project, token = _get_credentials_and_token()

        # Test Vertex AI connection
        success, error = _test_vertex_connection(project, token, context)

        # Only fetch account for interactive mode (when we need to display it)
        def get_account() -> str:
            account = _get_account_from_credentials(credentials)
            if not account:
                account = _get_account_from_gcloud() or "Unknown account"
            return account

        if success:
            # In auto_approve mode, skip account lookup since it's not displayed
            account = get_account() if not auto_approve else "N/A"
            return {"project": project, "account": account}

        # Handle API not enabled
        if error == "api_not_enabled":
            if auto_approve:
                raise Exception(
                    f"Vertex AI API is not enabled in project '{project}'. "
                    f"Enable it with: gcloud services enable aiplatform.googleapis.com --project {project}"
                )
            else:
                # Interactive mode - offer to enable
                console = _get_console()
                console.print(
                    f"Vertex AI API is not enabled in project '{project}'.",
                    style="yellow",
                )
                if Confirm.ask(
                    "Do you want to enable the Vertex AI API now?", default=True
                ):
                    if enable_vertex_ai_api(project, context):
                        return {"project": project, "account": get_account()}
                    raise Exception("Failed to enable Vertex AI API")
                else:
                    raise Exception(
                        "Vertex AI API is not enabled and user declined to enable it"
                    )

        # Other errors
        raise Exception(f"Vertex AI connection failed: {error}")

    except google.auth.exceptions.DefaultCredentialsError as e:
        raise Exception(_AUTH_ERROR_MESSAGE) from e
    except requests.exceptions.RequestException as e:
        raise Exception(f"Network error connecting to Vertex AI: {e}") from e
    except Exception as e:
        error_str = str(e).lower()
        if any(
            keyword in error_str for keyword in ["credential", "auth", "login", "token"]
        ):
            raise Exception(_AUTH_ERROR_MESSAGE) from e
        raise


def get_project_number(project_id: str) -> str:
    """Get project number from project ID using Resource Manager API.

    Args:
        project_id: GCP project ID

    Returns:
        Project number as string

    Raises:
        PermissionError: If access is denied to the project
        ValueError: If the project is not found
        requests.exceptions.HTTPError: For other API failures
    """
    _, _, token = _get_credentials_and_token()

    user_agent = get_user_agent()
    x_goog_api_client = get_x_goog_api_client_header()

    response = requests.get(
        f"{RESOURCE_MANAGER_API_BASE}/v1/projects/{project_id}",
        headers={
            "Authorization": f"Bearer {token}",
            "User-Agent": user_agent,
            "x-goog-api-client": x_goog_api_client,
        },
        timeout=30,
    )

    if response.status_code == 403:
        raise PermissionError(
            f"Permission denied accessing project '{project_id}'. "
            "Ensure you have the required permissions."
        )
    if response.status_code == 404:
        raise ValueError(f"Project '{project_id}' not found.")

    response.raise_for_status()
    return response.json()["projectNumber"]
