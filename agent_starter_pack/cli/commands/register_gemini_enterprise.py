#!/usr/bin/env python3
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

"""Utility to register an Agent Engine to Gemini Enterprise."""

import json
import os
import subprocess
import sys
from pathlib import Path

import click
import requests
import vertexai
from google.auth import default
from google.auth.transport.requests import Request as GoogleAuthRequest
from packaging import version
from rich.console import Console

from agent_starter_pack.cli.utils.command import run_gcloud_command
from agent_starter_pack.cli.utils.gcp import (
    get_user_agent,
    get_x_goog_api_client_header,
)

# TOML parser - use standard library for Python 3.11+, fallback to tomli
if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

console = Console(highlight=False)
console_err = Console(stderr=True, highlight=False)


def _strip_callback(
    _ctx: click.Context, _param: click.Parameter, value: str | None
) -> str | None:
    """Click callback to strip whitespace/newlines from option values."""
    return value.strip() if value else value


# SDK version that contains the fix for Gemini Enterprise session bug
# See: https://github.com/GoogleCloudPlatform/agent-starter-pack/issues/495
SDK_MIN_VERSION_FOR_GEMINI_ENTERPRISE = "1.128.0"

# SDK upgrade command constants
_SDK_UPGRADE_PACKAGE = (
    "google-cloud-aiplatform[adk,agent_engines] "
    "@ git+https://github.com/googleapis/python-aiplatform.git"
)
_SDK_UPGRADE_COMMAND = f'uv add "{_SDK_UPGRADE_PACKAGE}"'


def get_sdk_version_from_lock_file() -> tuple[str | None, bool]:
    """Get google-cloud-aiplatform version and source from uv.lock file.

    Returns:
        Tuple of (version string or None, is_from_git boolean).
        If from git, the fix is assumed to be applied regardless of version.
    """
    lock_path = Path("uv.lock")
    if not lock_path.exists():
        return None, False

    try:
        with open(lock_path, "rb") as f:
            lock_data = tomllib.load(f)

        for package in lock_data.get("package", []):
            if package.get("name") == "google-cloud-aiplatform":
                found_version = package.get("version")
                source = package.get("source")
                is_from_git = isinstance(source, dict) and "git" in source
                return found_version, is_from_git

        return None, False
    except (tomllib.TOMLDecodeError, OSError):
        return None, False


def _is_sdk_version_affected(current_version: str) -> bool:
    """Check if the SDK version is affected by the Gemini Enterprise bug."""
    return version.parse(current_version) <= version.parse(
        SDK_MIN_VERSION_FOR_GEMINI_ENTERPRISE
    )


def _print_sdk_compatibility_warning(current_version: str) -> None:
    """Print warning message about SDK compatibility issue."""
    console.print("\n" + "=" * 70)
    console.print("[yellow]⚠️  Agent Engine SDK Compatibility Issue Detected[/yellow]")
    console.print("=" * 70)
    console.print(
        f"\nYour current google-cloud-aiplatform version ({current_version}) has a known"
    )
    console.print("issue with Agent Engine that causes 'Session not found' errors when")
    console.print("registering to Gemini Enterprise.")
    console.print(
        "\nSee: https://github.com/GoogleCloudPlatform/agent-starter-pack/issues/495"
    )
    console.print(
        "\n[bold]The fix is available in the SDK git repository "
        "(will be in PyPI >1.128.0).[/bold]"
    )


def _run_sdk_upgrade() -> bool:
    """Execute the SDK upgrade command.

    Returns:
        True if upgrade succeeded, False otherwise.
    """
    console.print("\n[blue]Upgrading SDK from git (this may take a minute)...[/blue]")
    try:
        result = subprocess.run(
            ["uv", "add", _SDK_UPGRADE_PACKAGE],
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout
        )

        if result.returncode == 0:
            console.print("\n[green]✅ SDK upgraded successfully![/green]")
            console.print("\n[bold]Next steps:[/bold]")
            console.print(
                "  1. Redeploy your agent to pick up the fix: [cyan]make deploy[/cyan]"
            )
            console.print("  2. Re-run this command to register with Gemini Enterprise")
            return True

        console_err.print(f"\n[red]❌ Failed to upgrade SDK:[/red]\n{result.stderr}")
        console.print(f"\nYou can manually run:\n  {_SDK_UPGRADE_COMMAND}")
        return False

    except FileNotFoundError:
        console_err.print(
            "\n[yellow]⚠️  'uv' command not found. Please run manually:[/yellow]"
        )
        console.print(f"  {_SDK_UPGRADE_COMMAND}")
        return False
    except subprocess.TimeoutExpired:
        console_err.print("\n[red]❌ Upgrade timed out.[/red]")
        return False


def check_and_upgrade_sdk_for_agent_engine() -> bool:
    """Check if SDK version is compatible with Gemini Enterprise and offer to upgrade.

    For Agent Engine deployments, there's a known issue with SDK versions <= 1.128.0
    that causes 'Session not found' errors. The fix is available in the git repo.

    Returns:
        True if SDK is compatible or user upgraded, False if user chose to abort.
    """
    try:
        current_version, is_from_git = get_sdk_version_from_lock_file()

        if not current_version:
            # No lock file or couldn't parse - skip check
            return True

        if is_from_git:
            # Installed from git - assume fix is applied
            return True

        if not _is_sdk_version_affected(current_version):
            return True  # Version is OK

        # Version is affected - warn user and offer upgrade
        _print_sdk_compatibility_warning(current_version)

        if click.confirm(
            "\nWould you like to upgrade to the fixed version from git now?",
            default=True,
        ):
            if _run_sdk_upgrade():
                return False  # User needs to redeploy and restart
            return click.confirm(
                "\nContinue anyway (may encounter errors)?", default=False
            )

        # User declined upgrade
        console.print(
            f"\nYou can manually upgrade later by running:\n  {_SDK_UPGRADE_COMMAND}"
        )
        return click.confirm("\nContinue anyway (may encounter errors)?", default=False)

    except Exception as e:
        # If we can't check the version, just continue
        console_err.print(f"[dim]Warning: Could not check SDK version: {e}[/dim]")
        return True


def get_discovery_engine_endpoint(location: str) -> str:
    """Get the appropriate Discovery Engine API endpoint for the given location.

    Args:
        location: The location/region (e.g., 'global', 'us', 'eu')

    Returns:
        The Discovery Engine API endpoint base URL

    Examples:
        >>> get_discovery_engine_endpoint('global')
        'https://discoveryengine.googleapis.com'
        >>> get_discovery_engine_endpoint('eu')
        'https://eu-discoveryengine.googleapis.com'
        >>> get_discovery_engine_endpoint('us')
        'https://us-discoveryengine.googleapis.com'
    """
    if location == "global":
        return "https://discoveryengine.googleapis.com"
    else:
        # Regional endpoints use the format: https://{region}-discoveryengine.googleapis.com
        return f"https://{location}-discoveryengine.googleapis.com"


def parse_agent_engine_id(agent_engine_id: str) -> dict[str, str] | None:
    """Parse an Agent Engine resource name to extract components.

    Args:
        agent_engine_id: Agent Engine resource name
            (e.g., projects/PROJECT_NUM/locations/REGION/reasoningEngines/ENGINE_ID)

    Returns:
        Dictionary with 'project', 'location', 'engine_id' keys, or None if invalid format
    """
    parts = agent_engine_id.split("/")
    if (
        len(parts) == 6
        and parts[0] == "projects"
        and parts[2] == "locations"
        and parts[4] == "reasoningEngines"
    ):
        return {
            "project": parts[1],
            "location": parts[3],
            "engine_id": parts[5],
        }
    return None


def parse_gemini_enterprise_app_id(app_id: str) -> dict[str, str] | None:
    """Parse Gemini Enterprise app resource name to extract components.

    Args:
        app_id: Gemini Enterprise app resource name
            (e.g., projects/{project_number}/locations/{location}/collections/{collection}/engines/{engine_id})

    Returns:
        Dictionary with 'project_number', 'location', 'collection', 'engine_id' keys, or None if invalid format
    """
    parts = app_id.split("/")
    if (
        len(parts) == 8
        and parts[0] == "projects"
        and parts[2] == "locations"
        and parts[4] == "collections"
        and parts[6] == "engines"
    ):
        return {
            "project_number": parts[1],
            "location": parts[3],
            "collection": parts[5],
            "engine_id": parts[7],
        }
    return None


def get_access_token() -> str:
    """Get Google Cloud access token.

    Returns:
        Access token string

    Raises:
        RuntimeError: If authentication fails
    """
    try:
        credentials, _ = default()
        auth_req = GoogleAuthRequest()
        credentials.refresh(auth_req)
        return credentials.token
    except Exception as e:
        console_err.print(f"Error getting access token: {e}")
        console_err.print(
            "Please ensure you are authenticated with 'gcloud auth application-default login'"
        )
        raise RuntimeError("Failed to get access token") from e


def _build_api_headers(
    access_token: str,
    project_id: str,
    content_type: bool = False,
) -> dict[str, str]:
    """Build headers for Discovery Engine API requests with user-agent.

    Args:
        access_token: Google Cloud access token
        project_id: GCP project ID or number for billing
        content_type: Whether to include Content-Type header (for POST/PATCH)

    Returns:
        Headers dictionary
    """
    headers = {
        "Authorization": f"Bearer {access_token}",
        "x-goog-user-project": project_id,
        "User-Agent": get_user_agent(),
        "x-goog-api-client": get_x_goog_api_client_header(),
    }
    if content_type:
        headers["Content-Type"] = "application/json"
    return headers


def get_identity_token() -> str:
    """Get Google Cloud identity token.

    First checks for ID_TOKEN environment variable (useful in CI/CD environments
    like Cloud Build where the token is fetched in a separate step).
    Falls back to gcloud CLI.

    Returns:
        Identity token string

    Raises:
        RuntimeError: If authentication fails
    """
    # Check for pre-fetched token in environment variable (e.g., from Cloud Build)
    env_token = os.getenv("ID_TOKEN", "").strip()
    if env_token:
        return env_token

    try:
        result = run_gcloud_command(
            ["auth", "print-identity-token"],
            capture_output=True,
            check=True,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        console_err.print(f"Error getting identity token: {e.stderr}")
        console_err.print(
            "Please ensure you are authenticated with 'gcloud auth login'"
        )
        raise RuntimeError("Failed to get identity token") from e
    except FileNotFoundError as e:
        console_err.print("Error: gcloud command not found")
        console_err.print("Please install Google Cloud SDK")
        raise RuntimeError("Failed to get identity token") from e


def fetch_agent_card_from_url(url: str, deployment_target: str) -> dict | None:
    """Fetch agent card from a URL with proper authentication.

    Args:
        url: The URL to fetch the agent card from
        deployment_target: The deployment target ('agent_engine' or 'cloud_run')

    Returns:
        Agent card dictionary if successful, None otherwise
    """
    try:
        headers = {}

        # Use appropriate authentication based on deployment target
        if deployment_target == "agent_engine":
            access_token = get_access_token()
            headers["Authorization"] = f"Bearer {access_token}"
        elif deployment_target == "cloud_run":
            identity_token = get_identity_token()
            headers["Authorization"] = f"Bearer {identity_token}"
        else:
            raise ValueError(
                f"Unknown deployment target: {deployment_target}. "
                f"Expected 'agent_engine' or 'cloud_run'"
            )

        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        return response.json()
    except requests.exceptions.HTTPError as e:
        console_err.print(
            f"⚠️  HTTP error fetching agent card from {url}: {e}",
            style="yellow",
        )
        if e.response.status_code == 401 or e.response.status_code == 403:
            console_err.print(
                "  Authentication failed. Ensure you are logged in with 'gcloud auth application-default login'",
                style="yellow",
            )
        return None
    except Exception as e:
        console_err.print(
            f"⚠️  Could not fetch agent card from {url}: {e}",
            style="yellow",
        )
        return None


def construct_agent_card_url_from_metadata(
    metadata: dict,
) -> str | None:
    """Construct agent card URL from deployment metadata (Agent Engine only).

    Args:
        metadata: Deployment metadata dictionary

    Returns:
        Agent card URL if construction succeeds, None otherwise
    """
    deployment_target = metadata.get("deployment_target")

    if deployment_target == "agent_engine":
        # For Agent Engine: construct URL from remote_agent_engine_id
        remote_agent_engine_id = metadata.get("remote_agent_engine_id")
        if remote_agent_engine_id and remote_agent_engine_id != "None":
            parsed = parse_agent_engine_id(remote_agent_engine_id)
            if parsed:
                location = parsed["location"]
                # Agent Engine A2A endpoint format
                agent_card_url = (
                    f"https://{location}-aiplatform.googleapis.com/v1beta1/"
                    f"{remote_agent_engine_id}/a2a/v1/card"
                )
                return agent_card_url

    return None


def prompt_for_agent_card_url_with_auto_construct(
    metadata: dict | None,
    default_url: str | None = None,
) -> str:
    """Get agent card URL with automatic construction from deployment metadata.

    Args:
        metadata: Deployment metadata dictionary (can be None)
        default_url: Default agent card URL (e.g., from CLI arg)

    Returns:
        Agent card URL
    """
    # If default URL provided, show as smart default
    if default_url:
        console.print("\nAgent card URL provided:")
        console.print(f"  [bold]{default_url}[/]")
        use_default = click.confirm(
            "Use this agent card URL?", default=True, show_default=True
        )
        if use_default:
            return default_url

    # Try to auto-construct from metadata (Agent Engine only)
    if metadata:
        auto_url = construct_agent_card_url_from_metadata(metadata)

        if auto_url:
            # Successfully constructed from Agent Engine metadata
            console.print(
                "\n✅ Found Agent Engine deployment in deployment_metadata.json"
            )
            console.print(f"   Agent card URL: [bold]{auto_url}[/]")

            use_auto = click.confirm(
                "\nUse this agent card URL?", default=True, show_default=True
            )

            if use_auto:
                return auto_url

    # Fallback: manual entry
    console.print("\n[blue]" + "=" * 70 + "[/]")
    console.print("[blue]A2A AGENT CARD URL[/]")
    console.print("[blue]" + "=" * 70 + "[/]")
    console.print(
        "\nEnter your agent card URL manually"
        "\n[blue]Example: https://your-service.run.app/a2a/app/.well-known/agent-card.json[/]"
    )

    agent_card_url = click.prompt(
        "\nAgent card URL",
        type=str,
    ).strip()

    return agent_card_url


def get_agent_engine_metadata(agent_engine_id: str) -> tuple[str | None, str | None]:
    """Fetch display_name and description from deployed Agent Engine.

    Args:
        agent_engine_id: Agent Engine resource name

    Returns:
        Tuple of (display_name, description) - either can be None if not found
    """
    parts = agent_engine_id.split("/")
    if len(parts) < 6:
        return None, None

    project_id = parts[1]
    location = parts[3]

    try:
        client = vertexai.Client(project=project_id, location=location)
        agent_engine = client.agent_engines.get(name=agent_engine_id)

        display_name = getattr(agent_engine.api_resource, "display_name", None)
        description = getattr(agent_engine.api_resource, "description", None)

        return display_name, description
    except Exception as e:
        console_err.print(f"Warning: Could not fetch metadata from Agent Engine: {e}")
        return None, None


def prompt_for_agent_engine_id(default_from_metadata: str | None) -> str:
    """Prompt user for Agent Engine ID with optional default.

    Args:
        default_from_metadata: Default value from deployment_metadata.json if available

    Returns:
        The Agent Engine resource name
    """
    if default_from_metadata:
        console.print("\nFound Agent Engine ID from deployment_metadata.json:")
        console.print(f"  [bold]{default_from_metadata}[/]")
        use_default = click.confirm(
            "Use this Agent Engine ID?", default=True, show_default=True
        )
        if use_default:
            return default_from_metadata

    console.print(
        "\nEnter your Agent Engine resource name"
        "\n[blue]Example: projects/123456789/locations/us-central1/reasoningEngines/1234567890[/]"
        "\n(You can find this in the Agent Builder Console or deployment_metadata.json)"
    )

    while True:
        agent_engine_id = click.prompt("Agent Engine ID", type=str).strip()
        parsed = parse_agent_engine_id(agent_engine_id)
        if parsed:
            return agent_engine_id
        else:
            console_err.print(
                "❌ Invalid format. Expected: projects/{project}/locations/{location}/reasoningEngines/{id}",
                style="bold red",
            )


def get_current_project_id() -> str | None:
    """Get current GCP project ID from auth defaults.

    Returns:
        Project ID string, or None if not configured
    """
    try:
        _, project_id = default()
        return project_id
    except Exception:
        return None


def get_project_number(project_id: str) -> str | None:
    """Get project number from project ID.

    Args:
        project_id: GCP project ID (e.g., 'my-project')

    Returns:
        Project number as string, or None if lookup fails
    """
    try:
        result = run_gcloud_command(
            ["projects", "describe", project_id, "--format=value(projectNumber)"],
            capture_output=True,
            check=True,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        # Maybe it's already a project number, return as-is
        if project_id.isdigit():
            return project_id
        return None
    except FileNotFoundError:
        console_err.print("Warning: gcloud command not found")
        # Maybe it's already a project number, return as-is
        if project_id.isdigit():
            return project_id
        return None
    except Exception:
        # Fallback for any other errors
        if project_id.isdigit():
            return project_id
        return None


def list_gemini_enterprise_apps(
    project_number: str,
    location: str = "global",
) -> list[dict] | None:
    """List available Gemini Enterprise apps in a project.

    Args:
        project_number: GCP project number
        location: Location (global, us, or eu)

    Returns:
        List of engine dictionaries with 'name' and 'displayName' keys, or None on error
    """
    try:
        access_token = get_access_token()
        base_endpoint = get_discovery_engine_endpoint(location)
        url = (
            f"{base_endpoint}/v1alpha/projects/{project_number}/"
            f"locations/{location}/collections/default_collection/engines"
        )
        headers = _build_api_headers(access_token, project_number)

        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()

        data = response.json()
        engines = data.get("engines", [])

        return engines

    except requests.exceptions.HTTPError as e:
        if (
            hasattr(e, "response")
            and e.response is not None
            and e.response.status_code == 404
        ):
            # No engines found or collection doesn't exist
            return []
        error_code = (
            e.response.status_code
            if hasattr(e, "response") and e.response is not None
            else "unknown"
        )
        console_err.print(
            f"⚠️  Could not list Gemini Enterprise apps: HTTP {error_code}",
            style="yellow",
        )
        return None
    except Exception as e:
        console_err.print(
            f"⚠️  Could not list Gemini Enterprise apps: {e}",
            style="yellow",
        )
        return None


def prompt_for_gemini_enterprise_components(
    default_project: str | None = None,
) -> str:
    """Prompt user for Gemini Enterprise resource components and construct full ID.

    Attempts to list available apps across all common locations in the project.
    Falls back to manual entry if listing fails or user chooses custom entry.

    Args:
        default_project: Default project number from Agent Engine ID (unused, kept for compatibility)

    Returns:
        Full Gemini Enterprise app resource name
    """
    console.print("\n[blue]" + "=" * 70 + "[/]")
    console.print("[blue]GEMINI ENTERPRISE CONFIGURATION[/]")
    console.print("[blue]" + "=" * 70 + "[/]")

    # Get current project ID from auth defaults
    current_project_id = get_current_project_id()
    project_id = None
    project_number = None

    if current_project_id:
        console.print(f"\n✓ Current project: {current_project_id}")
        console.print("  (from your authentication defaults)")
        use_current = click.confirm(
            "\nUse this project for Gemini Enterprise?", default=True
        )
        if use_current:
            project_id = current_project_id
        else:
            project_id = click.prompt("Enter project ID", type=str).strip()
    else:
        console.print(
            "\nYou need to provide the Gemini Enterprise app details."
            "\nFind these in: Google Cloud Console → Gemini Enterprise → Apps"
        )
        project_id = click.prompt("Project ID", type=str).strip()

    # Convert project ID to project number
    console.print(f"[dim]Looking up project number for '{project_id}'...[/]")
    project_number = get_project_number(project_id)
    if not project_number:
        console_err.print(
            f"⚠️  Could not find project number for '{project_id}'",
            style="yellow",
        )
        console.print("Please enter the project number directly:")
        project_number = click.prompt("Project number", type=str).strip()
    else:
        console.print(f"✓ Project number: {project_number}")

    # Search across all common locations
    console.print(f"\n[dim]Searching for Gemini Enterprise apps in {project_id}...[/]")
    all_engines = []
    common_locations = ["global", "us", "eu"]

    for location in common_locations:
        engines = list_gemini_enterprise_apps(project_number, location)
        if engines:
            # Add location info to each engine for display
            for engine in engines:
                engine["_location"] = location
            all_engines.extend(engines)

    # Show results if any apps found
    if len(all_engines) > 0:
        console.print(f"\n✓ Found {len(all_engines)} Gemini Enterprise app(s):\n")

        # Display available apps with numbers
        for idx, engine in enumerate(all_engines, 1):
            display_name = engine.get("displayName", "N/A")
            location = engine.get("_location", "N/A")
            # Extract short ID from full name
            full_name = engine.get("name", "")
            parts = full_name.split("/")
            short_id = parts[-1] if parts else "N/A"

            console.print(f"  [{idx}] {display_name} [dim]({location})[/]")
            console.print(f"      ID: {short_id}")

        # Add option for custom entry
        console.print("\n  [0] Enter a custom Gemini Enterprise ID\n")

        # Prompt for selection
        while True:
            try:
                selection = click.prompt(
                    f"Select an app (0-{len(all_engines)})",
                    type=int,
                    default=1 if len(all_engines) == 1 else None,
                )

                if 0 <= selection <= len(all_engines):
                    break
                else:
                    console_err.print(
                        f"Please enter a number between 0 and {len(all_engines)}"
                    )
            except (ValueError, click.exceptions.Abort):
                console_err.print("Invalid input. Please enter a number.")
                raise

        # If user selected an existing app
        if selection > 0:
            selected_engine = all_engines[selection - 1]
            full_id = selected_engine.get("name")

            console.print("\n✓ Selected Gemini Enterprise App:")
            console.print(f"  [bold]{full_id}[/]")
            confirmed = click.confirm("Use this app?", default=True)

            if confirmed:
                return full_id

            # If not confirmed, restart the whole process
            console.print("\nLet's try again...")
            return prompt_for_gemini_enterprise_components(default_project)

        # If user selected custom entry (0), fall through to manual entry

    else:
        console.print(
            f"\n⚠️  No Gemini Enterprise apps found in project {project_number}"
        )
        console.print(
            "You can enter the details manually or try a different project.\n"
        )
        retry = click.confirm("Try a different project?", default=False)
        if retry:
            return prompt_for_gemini_enterprise_components(None)

    # Manual entry flow
    console.print("\n[blue]Manual Configuration[/]")
    console.print(
        "\nEnter your Gemini Enterprise app details."
        "\nFind these in: Google Cloud Console → Gemini Enterprise → Apps"
    )

    # Get location for manual entry
    console.print("\nGemini Enterprise apps are typically in: global, us, or eu")
    location = click.prompt(
        "Location/Region",
        type=str,
        default="global",
        show_default=True,
    ).strip()

    # Get short ID
    console.print(
        "\nEnter your Gemini Enterprise ID (from the 'ID' column in the Apps table)."
        "\n[blue]Example: gemini-enterprise-123456_1234567890[/]"
    )
    ge_short_id = click.prompt("Gemini Enterprise ID", type=str).strip()

    # Construct full resource name
    full_id = f"projects/{project_number}/locations/{location}/collections/default_collection/engines/{ge_short_id}"

    console.print("\nConstructed Gemini Enterprise App ID:")
    console.print(f"  [bold]{full_id}[/]")
    confirmed = click.confirm("Is this correct?", default=True)

    if confirmed:
        return full_id

    # If not confirmed, restart
    console.print("\nLet's try again...")
    return prompt_for_gemini_enterprise_components(default_project)


def ensure_discovery_engine_invoker_role(
    project_id: str,
    project_number: str,
) -> None:
    """Grant Cloud Run Invoker role to Discovery Engine service account at project level.

    Silently grants the role if not already present. Only shows warnings/errors
    if there are permission issues or unexpected failures.

    Args:
        project_id: GCP project ID
        project_number: GCP project number
    """
    try:
        # Construct Discovery Engine service account
        service_account = (
            f"service-{project_number}@gcp-sa-discoveryengine.iam.gserviceaccount.com"
        )

        result = run_gcloud_command(
            [
                "projects",
                "add-iam-policy-binding",
                project_id,
                f"--member=serviceAccount:{service_account}",
                "--role=roles/run.servicesInvoker",
                "--condition=None",
                "--quiet",
            ],
            capture_output=True,
            check=False,
        )

        if result.returncode != 0:
            error_msg = result.stderr.lower()
            # Ignore "already exists" type errors
            if "already exists" not in error_msg and "already has" not in error_msg:
                # Permission errors - show warning but don't fail
                if "permission" in error_msg or "forbidden" in error_msg:
                    console.print(
                        f"\n⚠️  [yellow]Warning: Could not grant roles/run.invoker to {service_account}[/]\n"
                    )

    except Exception:
        pass


def get_gemini_enterprise_console_url(
    gemini_enterprise_app_id: str, project_id: str
) -> str | None:
    """Construct Gemini Enterprise console URL.

    Args:
        gemini_enterprise_app_id: Full Gemini Enterprise app resource name
        project_id: GCP project ID (not number)

    Returns:
        Console URL string, or None if parsing fails
    """
    parsed = parse_gemini_enterprise_app_id(gemini_enterprise_app_id)
    if not parsed:
        return None

    location = parsed["location"]
    engine_id = parsed["engine_id"]

    return (
        f"https://console.cloud.google.com/gemini-enterprise/locations/{location}/"
        f"engines/{engine_id}/overview/dashboard?project={project_id}"
    )


def register_a2a_agent(
    agent_card: dict,
    agent_card_url: str,
    gemini_enterprise_app_id: str,
    display_name: str,
    description: str,
    project_id: str | None = None,
    authorization_id: str | None = None,
) -> dict:
    """Register an A2A agent to Gemini Enterprise.

    Args:
        agent_card: Agent card dictionary fetched from the agent
        agent_card_url: URL where the agent card was fetched from
        gemini_enterprise_app_id: Full Gemini Enterprise app resource name
        display_name: Display name for the agent in Gemini Enterprise
        description: Description of the agent
        project_id: Optional GCP project ID for billing
        authorization_id: Optional OAuth authorization ID

    Returns:
        API response as dictionary

    Raises:
        requests.HTTPError: If the API request fails
        ValueError: If gemini_enterprise_app_id format is invalid
    """
    parsed = parse_gemini_enterprise_app_id(gemini_enterprise_app_id)
    if not parsed:
        raise ValueError(
            f"Invalid GEMINI_ENTERPRISE_APP_ID format. Expected: "
            f"projects/{{project_number}}/locations/{{location}}/collections/{{collection}}/engines/{{engine_id}}, "
            f"got: {gemini_enterprise_app_id}"
        )

    project_number = parsed["project_number"]
    as_location = parsed["location"]
    collection = parsed["collection"]
    engine_id = parsed["engine_id"]

    # Use provided project ID or fallback to project number from GE app
    if not project_id:
        project_id = project_number

    access_token = get_access_token()
    base_endpoint = get_discovery_engine_endpoint(as_location)
    url = (
        f"{base_endpoint}/v1alpha/projects/{project_number}/"
        f"locations/{as_location}/collections/{collection}/engines/{engine_id}/"
        "assistants/default_assistant/agents"
    )
    headers = _build_api_headers(access_token, project_id, content_type=True)

    # Build payload with A2A agent definition
    payload = {
        "displayName": display_name,
        "description": description,
        "icon": {
            "uri": "https://fonts.gstatic.com/s/i/short-term/release/googlesymbols/smart_toy/default/24px.svg"
        },
        "a2aAgentDefinition": {"jsonAgentCard": json.dumps(agent_card)},
    }

    # Add authorization config if provided
    if authorization_id:
        payload["authorizationConfig"] = {"agentAuthorization": authorization_id}

    console.print("\n[blue]Registering A2A agent to Gemini Enterprise...[/]")
    console.print(f"  Agent Card URL: {agent_card_url}")
    console.print(f"  Gemini Enterprise App: {gemini_enterprise_app_id}")
    console.print(f"  Display Name: {display_name}")

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()

        result = response.json()
        console.print("\n✅ Successfully registered A2A agent to Gemini Enterprise!")
        console.print(f"   Agent Name:\n   {result.get('name', 'N/A')}")
        return result

    except requests.exceptions.HTTPError as http_err:
        # Check if agent already exists and try to update
        if response.status_code in (400, 409):
            try:
                error_data = response.json()
                error_message = error_data.get("error", {}).get("message", "")

                if (
                    "already exists" in error_message.lower()
                    or "duplicate" in error_message.lower()
                ):
                    console.print(
                        "\n⚠️  [yellow]Agent already registered. Updating existing registration...[/]"
                    )

                    # List and find existing agent
                    list_response = requests.get(url, headers=headers, timeout=30)
                    list_response.raise_for_status()
                    agents_list = list_response.json().get("agents", [])

                    # Find matching agent (by URL in agent card)
                    existing_agent = None
                    for agent in agents_list:
                        a2a_def = agent.get("a2aAgentDefinition", {})
                        if a2a_def:
                            try:
                                card = json.loads(a2a_def.get("jsonAgentCard", "{}"))
                                if card.get("url") == agent_card_url:
                                    existing_agent = agent
                                    break
                            except json.JSONDecodeError:
                                continue

                    if existing_agent:
                        agent_name = existing_agent.get("name")
                        update_url = f"{base_endpoint}/v1alpha/{agent_name}"

                        console.print(f"  Updating agent: {agent_name}")

                        update_response = requests.patch(
                            update_url, headers=headers, json=payload, timeout=30
                        )
                        update_response.raise_for_status()

                        result = update_response.json()
                        console.print(
                            "\n✅ Successfully updated A2A agent registration!"
                        )
                        console.print(f"   Agent Name:\n   {result.get('name', 'N/A')}")
                        return result
            except (ValueError, KeyError) as e:
                console_err.print(
                    f"Warning: Could not parse error response from API: {e}"
                )

        console_err.print(
            f"\n❌ [red]HTTP error occurred: {http_err}[/]",
            style="bold red",
        )
        console_err.print(f"   Response: {response.text}")
        raise
    except requests.exceptions.RequestException as req_err:
        console_err.print(
            f"\n❌ [red]Request error occurred: {req_err}[/]",
            style="bold red",
        )
        raise


def register_agent(
    agent_engine_id: str,
    gemini_enterprise_app_id: str,
    display_name: str,
    description: str,
    tool_description: str,
    project_id: str | None = None,
    authorization_id: str | None = None,
) -> dict:
    """Register an agent engine to Gemini Enterprise.

    This function attempts to create a new agent registration. If the agent is already
    registered (same reasoning engine), it will automatically update the existing
    registration instead.

    Args:
        agent_engine_id: Agent engine resource name (e.g., projects/.../reasoningEngines/...)
        gemini_enterprise_app_id: Full Gemini Enterprise app resource name
            (e.g., projects/{project_number}/locations/{location}/collections/{collection}/engines/{engine_id})
        display_name: Display name for the agent in Gemini Enterprise
        description: Description of the agent
        tool_description: Description of what the tool does
        project_id: Optional GCP project ID for billing (extracted from agent_engine_id if not provided)
        authorization_id: Optional OAuth authorization ID
            (e.g., projects/{project_number}/locations/global/authorizations/{auth_id})

    Returns:
        API response as dictionary

    Raises:
        requests.HTTPError: If the API request fails
        ValueError: If gemini_enterprise_app_id format is invalid
    """
    parsed = parse_gemini_enterprise_app_id(gemini_enterprise_app_id)
    if not parsed:
        raise ValueError(
            f"Invalid GEMINI_ENTERPRISE_APP_ID format. Expected: "
            f"projects/{{project_number}}/locations/{{location}}/collections/{{collection}}/engines/{{engine_id}}, "
            f"got: {gemini_enterprise_app_id}"
        )

    project_number = parsed["project_number"]
    as_location = parsed["location"]
    collection = parsed["collection"]
    engine_id = parsed["engine_id"]

    # Use project from agent engine if not explicitly provided (for billing header)
    if not project_id:
        parsed_agent = parse_agent_engine_id(agent_engine_id)
        if parsed_agent:
            project_id = parsed_agent["project"]
        else:
            project_id = project_number

    # Get access token
    access_token = get_access_token()

    # Build API endpoint with regional support
    base_endpoint = get_discovery_engine_endpoint(as_location)
    url = (
        f"{base_endpoint}/v1alpha/projects/{project_number}/"
        f"locations/{as_location}/collections/{collection}/engines/{engine_id}/"
        "assistants/default_assistant/agents"
    )

    # Request headers
    headers = _build_api_headers(access_token, project_id, content_type=True)

    # Request body
    payload: dict = {
        "displayName": display_name,
        "description": description,
        "icon": {
            "uri": "https://fonts.gstatic.com/s/i/short-term/release/googlesymbols/smart_toy/default/24px.svg"
        },
        "adk_agent_definition": {
            "tool_settings": {"tool_description": tool_description},
            "provisioned_reasoning_engine": {"reasoning_engine": agent_engine_id},
        },
    }

    # Add OAuth authorization if provided (at top level, not inside adk_agent_definition)
    if authorization_id:
        payload["authorization_config"] = {"tool_authorizations": [authorization_id]}

    console.print("\n[blue]Registering agent to Gemini Enterprise...[/]")
    console.print(f"  Agent Engine: {agent_engine_id}")
    console.print(f"  Gemini Enterprise App: {gemini_enterprise_app_id}")
    console.print(f"  Display Name: {display_name}")

    try:
        # Try to create a new registration first
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()

        result = response.json()
        console.print("\n✅ Successfully registered agent to Gemini Enterprise!")
        console.print(f"   Agent Name:\n   {result.get('name', 'N/A')}")
        return result

    except requests.exceptions.HTTPError as http_err:
        # Check if the error is because the agent already exists
        if response.status_code in (400, 409):
            try:
                error_data = response.json()
                error_message = error_data.get("error", {}).get("message", "")

                # Check if error indicates the agent already exists
                if (
                    "already exists" in error_message.lower()
                    or "duplicate" in error_message.lower()
                ):
                    console.print(
                        "\n⚠️  [yellow]Agent already registered. Updating existing registration...[/]"
                    )

                    # For update, we need to use the specific agent resource name
                    # The agent name should be in the error or we can construct it
                    # Format: {url}/{agent_id} but we need to find existing agent first

                    # List existing agents to find the one for this reasoning engine
                    list_response = requests.get(url, headers=headers, timeout=30)
                    list_response.raise_for_status()
                    agents_list = list_response.json().get("agents", [])

                    # Find the agent that matches our reasoning engine
                    existing_agent = None
                    for agent in agents_list:
                        prov_re = agent.get("adk_agent_definition", {}).get(
                            "provisioned_reasoning_engine", {}
                        )
                        # Check both snake_case and camelCase as API response format may vary
                        re_name = prov_re.get(
                            "reasoning_engine", prov_re.get("reasoningEngine", "")
                        )
                        if re_name == agent_engine_id:
                            existing_agent = agent
                            break

                    if existing_agent:
                        agent_name = existing_agent.get("name")
                        update_url = f"{base_endpoint}/v1alpha/{agent_name}"

                        console.print(f"  Updating agent: {agent_name}")

                        # PATCH request to update
                        update_response = requests.patch(
                            update_url, headers=headers, json=payload, timeout=30
                        )
                        update_response.raise_for_status()

                        result = update_response.json()
                        console.print(
                            "\n✅ Successfully updated agent registration in Gemini Enterprise!"
                        )
                        console.print(f"   Agent Name:\n   {result.get('name', 'N/A')}")
                        return result
                    else:
                        console_err.print(
                            "❌ [red]Could not find existing agent to update[/]",
                            style="bold red",
                        )
                        raise
            except (ValueError, KeyError) as e:
                console_err.print(
                    f"Warning: Could not parse error response from API: {e}"
                )

        # If not an "already exists" error, or update failed, raise the original error
        console_err.print(
            f"\n❌ [red]HTTP error occurred: {http_err}[/]",
            style="bold red",
        )
        console_err.print(f"   Response: {response.text}")
        raise
    except requests.exceptions.RequestException as req_err:
        console_err.print(
            f"\n❌ [red]Request error occurred: {req_err}[/]",
            style="bold red",
        )
        raise


@click.command()
@click.option(
    "--agent-engine-id",
    envvar="AGENT_ENGINE_ID",
    callback=_strip_callback,
    help="Agent Engine resource name (e.g., projects/.../reasoningEngines/...). "
    "If not provided, reads from deployment_metadata.json.",
)
@click.option(
    "--metadata-file",
    default="deployment_metadata.json",
    help="Path to deployment metadata file (default: deployment_metadata.json).",
)
@click.option(
    "--gemini-enterprise-app-id",
    callback=_strip_callback,
    help="Gemini Enterprise app full resource name "
    "(e.g., projects/{project_number}/locations/{location}/collections/{collection}/engines/{engine_id}). "
    "If not provided, the command will prompt you interactively. "
    "Can also be set via ID or GEMINI_ENTERPRISE_APP_ID env var.",
)
@click.option(
    "--display-name",
    envvar="GEMINI_DISPLAY_NAME",
    callback=_strip_callback,
    help="Display name for the agent.",
)
@click.option(
    "--description",
    envvar="GEMINI_DESCRIPTION",
    callback=_strip_callback,
    help="Description of the agent.",
)
@click.option(
    "--tool-description",
    envvar="GEMINI_TOOL_DESCRIPTION",
    callback=_strip_callback,
    help="Description of what the tool does.",
)
@click.option(
    "--project-id",
    envvar="GOOGLE_CLOUD_PROJECT",
    callback=_strip_callback,
    help="GCP project ID (extracted from agent-engine-id if not provided).",
)
@click.option(
    "--authorization-id",
    envvar="GEMINI_AUTHORIZATION_ID",
    callback=_strip_callback,
    help="OAuth authorization resource name "
    "(e.g., projects/{project_number}/locations/global/authorizations/{auth_id}).",
)
@click.option(
    "--agent-card-url",
    envvar="AGENT_CARD_URL",
    callback=_strip_callback,
    help="URL to fetch the agent card for A2A agents "
    "(e.g., https://your-service.run.app/a2a/app/.well-known/agent-card.json). "
    "If provided, registers as an A2A agent instead of ADK agent.",
)
@click.option(
    "--deployment-target",
    envvar="DEPLOYMENT_TARGET",
    type=click.Choice(["agent_engine", "cloud_run"], case_sensitive=False),
    help="Deployment target (agent_engine or cloud_run).",
)
@click.option(
    "--project-number",
    envvar="PROJECT_NUMBER",
    callback=_strip_callback,
    help="GCP project number. Used as default when prompting for Gemini Enterprise configuration.",
)
@click.option(
    "--registration-type",
    envvar="REGISTRATION_TYPE",
    type=click.Choice(["a2a", "adk"], case_sensitive=False),
    help="Registration type: 'a2a' for A2A agents (requires agent card URL), "
    "'adk' for ADK agents on Agent Engine (requires agent engine ID). "
    "If not provided, auto-detected from metadata or prompted.",
)
@click.option(
    "--yes",
    "-y",
    is_flag=True,
    default=False,
    help="Auto-approve all prompts (non-interactive mode). "
    "Uses defaults from metadata and environment variables.",
)
def register_gemini_enterprise(
    agent_engine_id: str | None,
    metadata_file: str,
    gemini_enterprise_app_id: str | None,
    display_name: str | None,
    description: str | None,
    tool_description: str | None,
    project_id: str | None,
    authorization_id: str | None,
    agent_card_url: str | None,
    deployment_target: str | None,
    project_number: str | None,
    registration_type: str | None,
    yes: bool,
) -> None:
    """Register an agent to Gemini Enterprise.

    This command can run interactively or accept all parameters via command-line options.
    If key parameters are missing, it will prompt the user for input.
    """
    console.print("\n🤖 Agent → Gemini Enterprise Registration\n")

    # Read metadata file once to determine agent type and deployment target
    metadata = None
    try:
        metadata_path = Path(metadata_file)
        if metadata_path.exists():
            with open(metadata_path, encoding="utf-8") as f:
                metadata = json.load(f)
    except (json.JSONDecodeError, KeyError, FileNotFoundError):
        pass

    provided_agent_card_url = agent_card_url or (
        os.getenv("AGENT_CARD_URL", "").strip() or None
    )

    # Determine registration type (a2a vs adk)
    resolved_registration_type = registration_type
    if not resolved_registration_type:
        if provided_agent_card_url:
            # Agent card URL provided -> A2A
            resolved_registration_type = "a2a"
        elif metadata:
            # Use metadata to determine type
            is_a2a = metadata.get("is_a2a", False)
            resolved_registration_type = "a2a" if is_a2a else "adk"
        else:
            # No metadata, no agent card URL - prompt user to choose
            console.print("[blue]No deployment metadata found.[/]")
            console.print(
                "\nSelect registration type:\n"
                "  [1] A2A - Agent-to-Agent protocol (requires agent card URL)\n"
                "  [2] ADK - Agent Development Kit on Agent Engine (requires agent engine ID)\n"
            )
            choice = click.prompt(
                "Registration type (1 or 2)",
                type=click.Choice(["1", "2"]),
                default="1",
            )
            resolved_registration_type = "a2a" if choice == "1" else "adk"

    # Log the registration type
    if resolved_registration_type == "a2a":
        console.print("[blue]→ A2A registration mode[/]")
    else:
        console.print("[blue]→ ADK registration mode[/]")

    # Set up agent_card_url for A2A mode
    if resolved_registration_type == "a2a":
        if yes:
            # In --yes mode, use provided URL directly or auto-construct from metadata
            if provided_agent_card_url:
                agent_card_url = provided_agent_card_url
                console.print(f"Using agent card URL: {agent_card_url}")
            elif metadata:
                # Try to auto-construct from metadata
                auto_url = construct_agent_card_url_from_metadata(metadata)
                if auto_url:
                    agent_card_url = auto_url
                    console.print(
                        f"Using auto-constructed agent card URL: {agent_card_url}"
                    )
                else:
                    raise click.ClickException(
                        "Agent card URL is required in --yes mode for A2A registration. "
                        "Set the AGENT_CARD_URL environment variable."
                    )
            else:
                raise click.ClickException(
                    "Agent card URL is required in --yes mode for A2A registration. "
                    "Set the AGENT_CARD_URL environment variable."
                )
        else:
            if not provided_agent_card_url:
                agent_card_url = prompt_for_agent_card_url_with_auto_construct(
                    metadata, None
                )
            else:
                agent_card_url = prompt_for_agent_card_url_with_auto_construct(
                    metadata, provided_agent_card_url
                )
        if not deployment_target:
            deployment_target = (
                metadata.get("deployment_target", "cloud_run")
                if metadata
                else "cloud_run"
            )
    else:
        # ADK mode - no agent_card_url needed
        agent_card_url = None

    # A2A registration
    if agent_card_url:
        # Ensure deployment_target has a value (default to cloud_run if not set)
        resolved_deployment_target = deployment_target or "cloud_run"
        agent_card = fetch_agent_card_from_url(
            agent_card_url, resolved_deployment_target
        )
        if not agent_card:
            raise click.ClickException(
                f"Failed to fetch agent card from {agent_card_url}. "
                "Please verify the URL is correct and the agent is running."
            )

        console.print(f"✓ Fetched agent card: {agent_card.get('name', 'Unknown')}")

        resolved_gemini_enterprise_app_id = (
            gemini_enterprise_app_id
            or (os.getenv("ID", "").strip() or None)
            or (os.getenv("GEMINI_ENTERPRISE_APP_ID", "").strip() or None)
        )

        if not resolved_gemini_enterprise_app_id:
            if yes:
                raise click.ClickException(
                    "Gemini Enterprise App ID is required in --yes mode. "
                    "Set the ID or GEMINI_ENTERPRISE_APP_ID environment variable."
                )
            default_project = project_number
            if (
                not default_project
                and metadata
                and metadata.get("deployment_target") == "agent_engine"
            ):
                remote_agent_engine_id = metadata.get("remote_agent_engine_id")
                if remote_agent_engine_id:
                    parsed = parse_agent_engine_id(remote_agent_engine_id)
                    if parsed:
                        default_project = parsed["project"]

            resolved_gemini_enterprise_app_id = prompt_for_gemini_enterprise_components(
                default_project=default_project
            )

        # Get display name and description with smart defaults from agent card
        if not display_name:
            default_display_name = agent_card.get("name") or "My A2A Agent"
            if yes:
                resolved_display_name = default_display_name
            else:
                resolved_display_name = click.prompt(
                    "Display name", default=default_display_name
                )
        else:
            resolved_display_name = display_name

        if not description:
            default_description = agent_card.get("description") or "AI Agent"
            if yes:
                resolved_description = default_description
            else:
                resolved_description = click.prompt(
                    "Description", default=default_description
                )
        else:
            resolved_description = description

        # For Cloud Run deployments, ensure Discovery Engine has invoker permissions
        if resolved_deployment_target == "cloud_run":
            parsed_ge = parse_gemini_enterprise_app_id(
                resolved_gemini_enterprise_app_id
            )
            if parsed_ge and project_number:
                ensure_discovery_engine_invoker_role(
                    project_id=project_id or parsed_ge["project_number"],
                    project_number=project_number,
                )

        # Register as A2A agent
        try:
            register_a2a_agent(
                agent_card=agent_card,
                agent_card_url=agent_card_url,
                gemini_enterprise_app_id=resolved_gemini_enterprise_app_id,
                display_name=resolved_display_name,
                description=resolved_description,
                project_id=project_id,
                authorization_id=authorization_id,
            )

            # Show console URL
            # Need to get project ID for the console URL
            console_project_id = project_id or get_current_project_id()
            if console_project_id:
                console_url = get_gemini_enterprise_console_url(
                    resolved_gemini_enterprise_app_id, console_project_id
                )
                if console_url:
                    console.print(
                        f"\n🔗 View in Console:\n   [link={console_url}]{console_url}[/link]"
                    )
        except Exception as e:
            raise click.ClickException(f"Error during A2A registration: {e}") from e

    # ADK
    else:
        # Check SDK version compatibility for Agent Engine deployments
        # See: https://github.com/GoogleCloudPlatform/agent-starter-pack/issues/495
        # Skip interactive prompts in --yes mode
        if not yes and not check_and_upgrade_sdk_for_agent_engine():
            console.print("\n[yellow]Registration aborted.[/yellow]")
            return

        # Step 1: Get Agent Engine ID
        resolved_agent_engine_id = agent_engine_id

        if not resolved_agent_engine_id:
            env_id = os.getenv("AGENT_ENGINE_ID", "").strip() or None
            if env_id:
                resolved_agent_engine_id = env_id
            else:
                metadata_id = (
                    metadata.get("remote_agent_engine_id") if metadata else None
                )
                if yes and metadata_id:
                    # In --yes mode, use metadata value directly without prompting
                    resolved_agent_engine_id = metadata_id
                    console.print(f"Using Agent Engine ID from metadata: {metadata_id}")
                else:
                    resolved_agent_engine_id = prompt_for_agent_engine_id(metadata_id)

        # Validate and parse Agent Engine ID
        parsed_ae = parse_agent_engine_id(resolved_agent_engine_id)
        if not parsed_ae:
            raise click.ClickException(
                f"Invalid Agent Engine ID format: {resolved_agent_engine_id}\n"
                "Expected: projects/{{project}}/locations/{{location}}/reasoningEngines/{{id}}"
            )

        # Step 2: Get Gemini Enterprise App ID
        resolved_gemini_enterprise_app_id = (
            gemini_enterprise_app_id
            or (os.getenv("ID", "").strip() or None)
            or (os.getenv("GEMINI_ENTERPRISE_APP_ID", "").strip() or None)
        )

        if not resolved_gemini_enterprise_app_id:
            if yes:
                raise click.ClickException(
                    "Gemini Enterprise App ID is required in --yes mode. "
                    "Set the ID or GEMINI_ENTERPRISE_APP_ID environment variable."
                )
            resolved_gemini_enterprise_app_id = prompt_for_gemini_enterprise_components(
                default_project=parsed_ae["project"]
            )

        # Step 3: Get display name and description
        auto_display_name, auto_description = get_agent_engine_metadata(
            resolved_agent_engine_id
        )

        resolved_display_name = display_name or auto_display_name or "My Agent"
        resolved_description = description or auto_description or "AI Agent"
        resolved_tool_description = tool_description or resolved_description

        # Step 4: Register as ADK agent
        try:
            register_agent(
                agent_engine_id=resolved_agent_engine_id,
                gemini_enterprise_app_id=resolved_gemini_enterprise_app_id,
                display_name=resolved_display_name,
                description=resolved_description,
                tool_description=resolved_tool_description,
                project_id=project_id,
                authorization_id=authorization_id,
            )

            # Show console URL
            console_project_id = project_id or get_current_project_id()
            if console_project_id:
                console_url = get_gemini_enterprise_console_url(
                    resolved_gemini_enterprise_app_id, console_project_id
                )
                if console_url:
                    console.print(
                        f"\n🔗 View in Console:\n   [link={console_url}]{console_url}[/link]"
                    )
        except Exception as e:
            raise click.ClickException(f"Error during ADK registration: {e}") from e
