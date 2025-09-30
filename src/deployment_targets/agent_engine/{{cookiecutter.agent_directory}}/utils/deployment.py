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

import datetime
import json
import logging
from typing import Any


def parse_env_vars(env_vars_string: str | None) -> dict[str, str]:
    """Parse environment variables from a comma-separated KEY=VALUE string.

    Args:
        env_vars_string: Comma-separated list of environment variables in KEY=VALUE format

    Returns:
        Dictionary of environment variables with keys and values stripped of whitespace
    """
    env_vars = {}
    if env_vars_string:
        for pair in env_vars_string.split(","):
            if "=" in pair:
                key, value = pair.split("=", 1)
                env_vars[key.strip()] = value.strip()
            else:
                logging.warning(f"Skipping malformed environment variable pair: {pair}")
    return env_vars


def write_deployment_metadata(
    remote_agent: Any,
    metadata_file: str = "deployment_metadata.json",
) -> None:
    """Write deployment metadata to file.

    Args:
        remote_agent: The deployed agent engine resource
        metadata_file: Path to write the metadata JSON file
    """
    metadata = {
        "remote_agent_engine_id": remote_agent.api_resource.name,
        "deployment_timestamp": datetime.datetime.now().isoformat(),
    }

    with open(metadata_file, "w") as f:
        json.dump(metadata, f, indent=2)

    logging.info(f"Agent Engine ID written to {metadata_file}")


def print_deployment_success(
    remote_agent: Any,
    location: str,
    project: str,
) -> None:
    """Print deployment success message with console URL.

    Args:
        remote_agent: The deployed agent engine resource
        location: GCP region where the agent was deployed
        project: GCP project ID
    """
    # Extract agent engine ID for console URL
    agent_engine_id = remote_agent.api_resource.name.split("/")[-1]
    console_url = f"https://console.cloud.google.com/vertex-ai/agents/locations/{location}/agent-engines/{agent_engine_id}?project={project}"

{%- if "adk" in cookiecutter.tags %}
    print(
        f"\n✅ Deployment successful! Test your agent: notebooks/adk_app_testing.ipynb"
        f"\n📊 View in console: {console_url}\n"
    )
{%- else %}
    print(f"\n✅ Deployment successful!\n📊 View in console: {console_url}\n")
{%- endif %}
