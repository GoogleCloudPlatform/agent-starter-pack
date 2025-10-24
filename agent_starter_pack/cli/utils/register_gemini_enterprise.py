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

import argparse
import json
import os
import sys
from pathlib import Path

import requests
import vertexai
from google.auth import default
from google.auth.transport.requests import Request as GoogleAuthRequest


def get_agent_engine_id(
    agent_engine_id: str | None, metadata_file: str = "deployment_metadata.json"
) -> str:
    """Get the agent engine ID from parameter or deployment metadata.

    Args:
        agent_engine_id: Optional agent engine resource name
        metadata_file: Path to deployment metadata JSON file

    Returns:
        The agent engine resource name

    Raises:
        ValueError: If agent_engine_id is not provided and metadata file doesn't exist
    """
    if agent_engine_id:
        return agent_engine_id

    # Try to read from deployment_metadata.json
    metadata_path = Path(metadata_file)
    if not metadata_path.exists():
        raise ValueError(
            f"No agent engine ID provided and {metadata_file} not found. "
            "Please provide --agent-engine-id or deploy your agent first."
        )

    with open(metadata_path) as f:
        metadata = json.load(f)
        return metadata["remote_agent_engine_id"]


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
        print(f"Warning: Could not fetch metadata from Agent Engine: {e}", file=sys.stderr)
        return None, None


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

    # Build API endpoint
    url = (
        f"https://discoveryengine.googleapis.com/v1alpha/projects/{project_number}/"
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

    print("Registering agent to Gemini Enterprise...")
    print(f"  Agent Engine: {agent_engine_id}")
    print(f"  Gemini Enterprise App: {gemini_enterprise_app_id}")
    print(f"  Display Name: {display_name}")
    print(f"  API Endpoint: {url}")

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()

        result = response.json()
        print("\n✅ Successfully registered agent to Gemini Enterprise!")
        print(f"   Agent Name: {result.get('name', 'N/A')}")
        return result

    except requests.exceptions.HTTPError as http_err:
        print(f"\n❌ HTTP error occurred: {http_err}", file=sys.stderr)
        print(f"   Response: {response.text}", file=sys.stderr)
        raise
    except requests.exceptions.RequestException as req_err:
        print(f"\n❌ Request error occurred: {req_err}", file=sys.stderr)
        raise


def main() -> None:
    """Main entry point for CLI."""
    parser = argparse.ArgumentParser(
        description="Register an Agent Engine to Gemini Enterprise"
    )
    parser.add_argument(
        "--agent-engine-id",
        help="Agent Engine resource name (e.g., projects/.../reasoningEngines/...). "
        "If not provided, reads from deployment_metadata.json",
    )
    parser.add_argument(
        "--metadata-file",
        default="deployment_metadata.json",
        help="Path to deployment metadata file (default: deployment_metadata.json)",
    )
    parser.add_argument(
        "--gemini-enterprise-app-id",
        help="Gemini Enterprise app full resource name "
        "(e.g., projects/{project_number}/locations/{location}/collections/{collection}/engines/{engine_id}). "
        "Can also be set via GEMINI_ENTERPRISE_APP_ID env var",
    )
    parser.add_argument(
        "--display-name",
        help="Display name for the agent. Can also be set via GEMINI_DISPLAY_NAME env var",
    )
    parser.add_argument(
        "--description",
        help="Description of the agent. Can also be set via GEMINI_DESCRIPTION env var",
    )
    parser.add_argument(
        "--tool-description",
        help="Description of what the tool does. Can also be set via GEMINI_TOOL_DESCRIPTION env var",
    )
    parser.add_argument(
        "--project-id",
        help="GCP project ID (extracted from agent-engine-id if not provided). "
        "Can also be set via GOOGLE_CLOUD_PROJECT env var",
    )
    parser.add_argument(
        "--authorization-id",
        help="OAuth authorization resource name "
        "(e.g., projects/{project_number}/locations/global/authorizations/{auth_id}). "
        "Can also be set via GEMINI_AUTHORIZATION_ID env var",
    )

    args = parser.parse_args()

    # Get agent engine ID
    try:
        agent_engine_id = get_agent_engine_id(args.agent_engine_id, args.metadata_file)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    # Auto-detect display_name and description from Agent Engine
    auto_display_name, auto_description = get_agent_engine_metadata(agent_engine_id)

    gemini_enterprise_app_id = args.gemini_enterprise_app_id or os.getenv(
        "GEMINI_ENTERPRISE_APP_ID"
    )
    if not gemini_enterprise_app_id:
        print(
            "Error: --gemini-enterprise-app-id or GEMINI_ENTERPRISE_APP_ID env var required",
            file=sys.stderr,
        )
        sys.exit(1)

    display_name = (
        args.display_name
        or os.getenv("GEMINI_DISPLAY_NAME")
        or auto_display_name
        or "My Agent"
    )
    description = (
        args.description
        or os.getenv("GEMINI_DESCRIPTION")
        or auto_description
        or "AI Agent"
    )
    tool_description = (
        args.tool_description or os.getenv("GEMINI_TOOL_DESCRIPTION") or description
    )
    project_id = args.project_id or os.getenv("GOOGLE_CLOUD_PROJECT")
    authorization_id = args.authorization_id or os.getenv("GEMINI_AUTHORIZATION_ID")

    try:
        register_agent(
            agent_engine_id=agent_engine_id,
            gemini_enterprise_app_id=gemini_enterprise_app_id,
            display_name=display_name,
            description=description,
            tool_description=tool_description,
            project_id=project_id,
            authorization_id=authorization_id,
        )
    except Exception as e:
        print(f"Error during registration: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
