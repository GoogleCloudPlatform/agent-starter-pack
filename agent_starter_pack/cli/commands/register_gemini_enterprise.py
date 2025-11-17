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
import sys
from pathlib import Path

import click
import requests
import vertexai
from google.auth import default
from google.auth.transport.requests import Request as GoogleAuthRequest
from rich.console import Console

console = Console(highlight=False)
console_err = Console(stderr=True, highlight=False)


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


def get_agent_engine_id_from_metadata(
    metadata_file: str = "deployment_metadata.json",
) -> str | None:
    """Try to read the agent engine ID from deployment metadata.

    Args:
        metadata_file: Path to deployment metadata JSON file

    Returns:
        The agent engine resource name if found, None otherwise
    """
    metadata_path = Path(metadata_file)
    if not metadata_path.exists():
        return None

    try:
        with open(metadata_path, encoding="utf-8") as f:
            metadata = json.load(f)
            return metadata.get("remote_agent_engine_id")
    except (json.JSONDecodeError, KeyError):
        return None


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


def get_access_token() -> str:
    """Get Google Cloud access token.

    Returns:
        Access token string

    Raises:
        SystemExit: If authentication fails
    """
    try:
        credentials, _ = default()
        auth_req = GoogleAuthRequest()
        credentials.refresh(auth_req)
        return credentials.token
    except Exception as e:
        print(f"Error getting access token: {e}", file=sys.stderr)
        print(
            "Please ensure you are authenticated with 'gcloud auth application-default login'",
            file=sys.stderr,
        )
        raise RuntimeError("Failed to get access token") from e


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
        print(
            f"Warning: Could not fetch metadata from Agent Engine: {e}", file=sys.stderr
        )
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


def prompt_for_gemini_enterprise_components(
    default_project: str | None = None,
) -> str:
    """Prompt user for Gemini Enterprise resource components and construct full ID.

    Args:
        default_project: Default project number from Agent Engine ID

    Returns:
        Full Gemini Enterprise app resource name
    """
    console.print("\n[blue]" + "=" * 70 + "[/]")
    console.print("[blue]GEMINI ENTERPRISE CONFIGURATION[/]")
    console.print("[blue]" + "=" * 70 + "[/]")

    console.print(
        "\nYou need to provide the Gemini Enterprise app details."
        "\nFind these in: Google Cloud Console → Gemini Enterprise → Apps"
        "\nCopy the ID from the 'ID' column for your Gemini Enterprise instance."
    )

    while True:
        # Project number
        if default_project:
            console.print(f"\n[dim]Default from Agent Engine: {default_project}[/]")
        project_number = click.prompt(
            "Project number", type=str, default=default_project or ""
        ).strip()

        # Location - GE apps are typically in 'global', 'us', or 'eu'
        console.print("\nGemini Enterprise apps are in: global, us, or eu")
        location = click.prompt(
            "Location/Region",
            type=str,
            default="global",
            show_default=True,
        ).strip()

        # Gemini Enterprise short ID
        console.print(
            "\nEnter your Gemini Enterprise ID (from the 'ID' column in the Apps table)."
            "\n[blue]Example: gemini-enterprise-1762990_8862980842627[/]"
        )
        ge_short_id = click.prompt("Gemini Enterprise ID", type=str).strip()

        # Construct full resource name
        # Format: projects/{project_number}/locations/{location}/collections/default_collection/engines/{ge_id}
        full_id = f"projects/{project_number}/locations/{location}/collections/default_collection/engines/{ge_short_id}"

        console.print("\nConstructed Gemini Enterprise App ID:")
        console.print(f"  [bold]{full_id}[/]")
        confirmed = click.confirm("Is this correct?", default=True)

        if confirmed:
            return full_id

        click.echo("Let's try again...")


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
    # Parse Gemini Enterprise app resource name
    # Format: projects/{project_number}/locations/{location}/collections/{collection}/engines/{engine_id}
    parts = gemini_enterprise_app_id.split("/")
    if (
        len(parts) != 8
        or parts[0] != "projects"
        or parts[2] != "locations"
        or parts[4] != "collections"
        or parts[6] != "engines"
    ):
        raise ValueError(
            f"Invalid GEMINI_ENTERPRISE_APP_ID format. Expected: "
            f"projects/{{project_number}}/locations/{{location}}/collections/{{collection}}/engines/{{engine_id}}, "
            f"got: {gemini_enterprise_app_id}"
        )

    project_number = parts[1]
    as_location = parts[3]
    collection = parts[5]
    engine_id = parts[7]

    # Use project from agent engine if not explicitly provided (for billing header)
    if not project_id:
        # Extract from agent_engine_id: projects/{project}/locations/{location}/reasoningEngines/{id}
        agent_parts = agent_engine_id.split("/")
        if len(agent_parts) > 1 and agent_parts[0] == "projects":
            project_id = agent_parts[1]
        else:
            # Fallback to the project number from the Gemini Enterprise App ID.
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
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "x-goog-user-project": project_id,
    }

    # Request body
    adk_agent_definition: dict = {
        "tool_settings": {"tool_description": tool_description},
        "provisioned_reasoning_engine": {"reasoningEngine": agent_engine_id},
    }

    # Add OAuth authorization if provided
    if authorization_id:
        adk_agent_definition["authorizations"] = [authorization_id]

    payload = {
        "displayName": display_name,
        "description": description,
        "icon": {
            "uri": "https://fonts.gstatic.com/s/i/short-term/release/googlesymbols/smart_toy/default/24px.svg"
        },
        "adk_agent_definition": adk_agent_definition,
    }

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
        console.print(f"   Agent Name: {result.get('name', 'N/A')}")
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
                        re_name = (
                            agent.get("adk_agent_definition", {})
                            .get("provisioned_reasoning_engine", {})
                            .get("reasoningEngine", "")
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
                        console.print(f"   Agent Name: {result.get('name', 'N/A')}")
                        return result
                    else:
                        console_err.print(
                            "❌ [red]Could not find existing agent to update[/]",
                            style="bold red",
                        )
                        raise
            except (ValueError, KeyError):
                # Failed to parse error response, raise original error
                pass

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
    help="Gemini Enterprise app full resource name "
    "(e.g., projects/{project_number}/locations/{location}/collections/{collection}/engines/{engine_id}). "
    "If not provided, the command will prompt you interactively. "
    "Can also be set via ID or GEMINI_ENTERPRISE_APP_ID env var.",
)
@click.option(
    "--display-name",
    envvar="GEMINI_DISPLAY_NAME",
    help="Display name for the agent.",
)
@click.option(
    "--description",
    envvar="GEMINI_DESCRIPTION",
    help="Description of the agent.",
)
@click.option(
    "--tool-description",
    envvar="GEMINI_TOOL_DESCRIPTION",
    help="Description of what the tool does.",
)
@click.option(
    "--project-id",
    envvar="GOOGLE_CLOUD_PROJECT",
    help="GCP project ID (extracted from agent-engine-id if not provided).",
)
@click.option(
    "--authorization-id",
    envvar="GEMINI_AUTHORIZATION_ID",
    help="OAuth authorization resource name "
    "(e.g., projects/{project_number}/locations/global/authorizations/{auth_id}).",
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
) -> None:
    """Register an Agent Engine to Gemini Enterprise.

    This command can run interactively or accept all parameters via command-line options.
    If key parameters are missing, it will prompt the user for input.
    """
    console.print("\n🤖 Agent Engine → Gemini Enterprise Registration\n")

    # Step 1: Get Agent Engine ID (with smart defaults from deployment_metadata.json)
    resolved_agent_engine_id = agent_engine_id

    if not resolved_agent_engine_id:
        # Check if we have ID from env var (backward compatibility)
        env_id = os.getenv("AGENT_ENGINE_ID")
        if env_id:
            resolved_agent_engine_id = env_id
        else:
            # Try to get from metadata file
            metadata_id = get_agent_engine_id_from_metadata(metadata_file)
            # Prompt user (with default if available)
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
        or os.getenv("ID")
        or os.getenv("GEMINI_ENTERPRISE_APP_ID")
    )

    if not resolved_gemini_enterprise_app_id:
        # Interactive mode: prompt for components and construct the full ID
        resolved_gemini_enterprise_app_id = prompt_for_gemini_enterprise_components(
            default_project=parsed_ae["project"]
        )

    # Step 3: Get display name and description (from Agent Engine metadata or defaults)
    auto_display_name, auto_description = get_agent_engine_metadata(
        resolved_agent_engine_id
    )

    resolved_display_name = display_name or auto_display_name or "My Agent"
    resolved_description = description or auto_description or "AI Agent"
    resolved_tool_description = tool_description or resolved_description

    # Step 4: Register the agent
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
    except Exception as e:
        raise click.ClickException(f"Error during registration: {e}") from e
