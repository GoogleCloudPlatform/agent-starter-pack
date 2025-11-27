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

import asyncio
import datetime
import importlib
import inspect
import json
import logging
import os
import warnings
from typing import Any

import click
import google.auth
import vertexai
from dotenv import dotenv_values
from vertexai._genai import _agent_engines_utils
from vertexai._genai.types import AgentEngine, AgentEngineConfig{%- if cookiecutter.is_adk_live %}, AgentServerMode{%- endif %}
{%- if cookiecutter.is_adk_live %}

from {{cookiecutter.agent_directory}}.app_utils.gcs import create_bucket_if_not_exists
{%- endif %}

# Suppress google-cloud-storage version compatibility warning
warnings.filterwarnings(
    "ignore", category=FutureWarning, module="google.cloud.aiplatform"
)


def generate_class_methods_from_agent(agent_instance: Any) -> list[dict[str, Any]]:
    """Generate method specifications with schemas from agent's register_operations().

    See: https://docs.cloud.google.com/agent-builder/agent-engine/use/custom#supported-operations
    """
    registered_operations = _agent_engines_utils._get_registered_operations(
        agent=agent_instance
    )
    class_methods_spec = _agent_engines_utils._generate_class_methods_spec_or_raise(
        agent=agent_instance,
        operations=registered_operations,
    )
    class_methods_list = [
        _agent_engines_utils._to_dict(method_spec) for method_spec in class_methods_spec
    ]
    return class_methods_list


def parse_key_value_pairs(kv_string: str | None) -> dict[str, str]:
    """Parse key-value pairs from a comma-separated KEY=VALUE string."""
    result = {}
    if kv_string:
        for pair in kv_string.split(","):
            if "=" in pair:
                key, value = pair.split("=", 1)
                result[key.strip()] = value.strip()
            else:
                logging.warning(f"Skipping malformed key-value pair: {pair}")
    return result


def load_env_file(env_file_path: str | None, app_directory: str) -> dict[str, str]:
    """Load environment variables from a .env file and return as dictionary."""
    # Determine which .env file to use
    if env_file_path:
        target_file = env_file_path
    else:
        target_file = os.path.join(app_directory, ".env")

    if not os.path.exists(target_file):
        if env_file_path:  # Only warn if a specific file was explicitly provided
            logging.warning(f"Specified env file not found: {target_file}")
        return {}

    logging.info(f"Loading environment variables from {target_file}")
    env_vars = dotenv_values(target_file)

    # Filter out GOOGLE_CLOUD_* variables - these are managed by the deployment
    filtered_vars = {}
    for key, value in env_vars.items():
        if value is None:
            continue
        if key.startswith("GOOGLE_CLOUD_"):
            logging.info(f"Ignoring {key} from .env (managed by deployment)")
            continue
        filtered_vars[key] = value

    return filtered_vars


def write_deployment_metadata(
    remote_agent: Any,
    metadata_file: str = "deployment_metadata.json",
) -> None:
    """Write deployment metadata to file."""
    metadata = {
        "remote_agent_engine_id": remote_agent.api_resource.name,
        "deployment_target": "agent_engine",
{%- if cookiecutter.is_a2a %}
        "is_a2a": True,
{%- else %}
        "is_a2a": False,
{%- endif %}
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
    """Print deployment success message with console URL."""
    # Extract agent engine ID and project number for console URL
    resource_name_parts = remote_agent.api_resource.name.split("/")
    agent_engine_id = resource_name_parts[-1]
    project_number = resource_name_parts[1]

{%- if cookiecutter.is_adk_live %}
    print("\n✅ Deployment successful! Run your agent with: `make playground-remote`")
{%- elif cookiecutter.is_a2a %}
    print(
        "\n✅ Deployment successful! Test your agent: notebooks/adk_a2a_app_testing.ipynb"
    )
{%- else %}
    print("\n✅ Deployment successful!")
{%- endif %}
    service_account = remote_agent.api_resource.spec.service_account
    if service_account:
        print(f"Service Account: {service_account}")
    else:
        default_sa = (
            f"service-{project_number}@gcp-sa-aiplatform-re.iam.gserviceaccount.com"
        )
        print(f"Service Account: {default_sa}")
{%- if cookiecutter.is_adk and not cookiecutter.is_adk_live and not cookiecutter.is_a2a %}
    playground_url = f"https://console.cloud.google.com/vertex-ai/agents/locations/{location}/agent-engines/{agent_engine_id}/playground?project={project}"
    print(f"\n📊 Open Console Playground: {playground_url}\n")
{%- else %}
    console_url = f"https://console.cloud.google.com/vertex-ai/agents/locations/{location}/agent-engines/{agent_engine_id}?project={project}"
    print(f"\n📊 View in Console: {console_url}\n")
{%- endif %}


@click.command()
@click.option(
    "--project",
    default=None,
    help="GCP project ID (defaults to application default credentials)",
)
@click.option(
    "--location",
    default="us-central1",
    help="GCP region (defaults to us-central1)",
)
@click.option(
    "--display-name",
    default="{{cookiecutter.project_name}}",
    help="Display name for the agent engine",
)
@click.option(
    "--description",
    default="{{cookiecutter.agent_description}}",
    help="Description of the agent",
)
@click.option(
    "--source-packages",
    multiple=True,
    default=["./{{cookiecutter.agent_directory}}"],
    help="Source packages to deploy. Can be specified multiple times (e.g., --source-packages=./app --source-packages=./lib)",
)
@click.option(
    "--entrypoint-module",
    default="{{cookiecutter.agent_directory}}.agent_engine_app",
    help="Python module path for the agent entrypoint (required)",
)
@click.option(
    "--entrypoint-object",
    default="agent_engine",
    help="Name of the agent instance at module level (required)",
)
@click.option(
    "--requirements-file",
    default="{{cookiecutter.agent_directory}}/app_utils/.requirements.txt",
    help="Path to requirements.txt file",
)
@click.option(
    "--env-file",
    default=None,
    help="Path to .env file for environment variables (defaults to {{cookiecutter.agent_directory}}/.env)",
)
@click.option(
    "--set-env-vars",
    default=None,
    help="Comma-separated list of environment variables in KEY=VALUE format (overrides .env file)",
)
@click.option(
    "--labels",
    default=None,
    help="Comma-separated list of labels in KEY=VALUE format",
)
@click.option(
    "--service-account",
    default=None,
    help="Service account email to use for the agent engine",
)
@click.option(
    "--min-instances",
    type=int,
    default=1,
    help="Minimum number of instances (default: 1)",
)
@click.option(
    "--max-instances",
    type=int,
    default=10,
    help="Maximum number of instances (default: 10)",
)
@click.option(
    "--cpu",
    default="4",
    help="CPU limit (default: 4)",
)
@click.option(
    "--memory",
    default="8Gi",
    help="Memory limit (default: 8Gi)",
)
@click.option(
    "--container-concurrency",
    type=int,
    default=9,
    help="Container concurrency (default: 9)",
)
@click.option(
    "--num-workers",
    type=int,
    default=1,
    help="Number of worker processes (default: 1)",
)
def deploy_agent_engine_app(
    project: str | None,
    location: str,
    display_name: str,
    description: str,
    source_packages: tuple[str, ...],
    entrypoint_module: str,
    entrypoint_object: str,
    requirements_file: str,
    env_file: str | None,
    set_env_vars: str | None,
    labels: str | None,
    service_account: str | None,
    min_instances: int,
    max_instances: int,
    cpu: str,
    memory: str,
    container_concurrency: int,
    num_workers: int,
) -> AgentEngine:
    """Deploy the agent engine app to Vertex AI."""

    logging.basicConfig(level=logging.INFO)
    logging.getLogger("httpx").setLevel(logging.WARNING)

    # Determine app directory from entrypoint module (e.g., "app.agent_engine_app" -> "app")
    app_directory = entrypoint_module.split(".")[0]

    # Load environment variables from .env file first
    env_vars = load_env_file(env_file, app_directory)

    # Parse and merge CLI environment variables (these take precedence)
    cli_env_vars = parse_key_value_pairs(set_env_vars)
    env_vars.update(cli_env_vars)

    # Parse labels
    labels_dict = parse_key_value_pairs(labels)

    # Set GOOGLE_CLOUD_REGION to match deployment location
    env_vars["GOOGLE_CLOUD_REGION"] = location

    # Add NUM_WORKERS from CLI argument (can be overridden via --set-env-vars)
    if "NUM_WORKERS" not in env_vars:
        env_vars["NUM_WORKERS"] = str(num_workers)

    # Enable telemetry by default for Agent Engine
    if "GOOGLE_CLOUD_AGENT_ENGINE_ENABLE_TELEMETRY" not in env_vars:
        env_vars["GOOGLE_CLOUD_AGENT_ENGINE_ENABLE_TELEMETRY"] = "true"
    if "OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT" not in env_vars:
        env_vars["OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT"] = "true"

    if not project:
        _, project = google.auth.default()

    print("""
    ╔═══════════════════════════════════════════════════════════╗
    ║                                                           ║
    ║   🤖 DEPLOYING AGENT TO VERTEX AI AGENT ENGINE 🤖         ║
    ║                                                           ║
    ╚═══════════════════════════════════════════════════════════╝
    """)

    # Log deployment parameters
    click.echo("\n📋 Deployment Parameters:")
    click.echo(f"  Project: {project}")
    click.echo(f"  Location: {location}")
    click.echo(f"  Display Name: {display_name}")
    click.echo(f"  Min Instances: {min_instances}")
    click.echo(f"  Max Instances: {max_instances}")
    click.echo(f"  CPU: {cpu}")
    click.echo(f"  Memory: {memory}")
    click.echo(f"  Container Concurrency: {container_concurrency}")
    if service_account:
        click.echo(f"  Service Account: {service_account}")
    if env_vars:
        click.echo("\n🌍 Environment Variables:")
        for key, value in sorted(env_vars.items()):
            click.echo(f"  {key}: {value}")

    source_packages_list = list(source_packages)

    # Initialize vertexai client
    client = vertexai.Client(
        project=project,
        location=location,
    )
    vertexai.init(project=project, location=location)

    # Add agent garden labels if configured
{%- if cookiecutter.agent_garden %}
{%- if cookiecutter.agent_sample_id and cookiecutter.agent_sample_publisher %}
    labels_dict["vertex-agent-sample-id"] = "{{cookiecutter.agent_sample_id}}"
    labels_dict["vertex-agent-sample-publisher"] = "{{cookiecutter.agent_sample_publisher}}"
    labels_dict["deployed-with"] = "agent-garden"
{%- endif %}
{%- endif %}

    # Dynamically import the agent instance to generate class_methods
    logging.info(f"Importing {entrypoint_module}.{entrypoint_object}")
    module = importlib.import_module(entrypoint_module)
    agent_instance = getattr(module, entrypoint_object)

    # If the agent_instance is a coroutine, await it to get the actual instance
    if inspect.iscoroutine(agent_instance):
        logging.info(f"Detected coroutine, awaiting {entrypoint_object}...")
        agent_instance = asyncio.run(agent_instance)

{%- if cookiecutter.is_adk_live %}
    # For adk_live, use pickle-based deployment (source-based not yet supported with EXPERIMENTAL mode)
    # Ensure staging bucket exists for pickle serialization
    staging_bucket_uri = f"gs://{project}-agent-engine"

    create_bucket_if_not_exists(
        bucket_name=staging_bucket_uri, project=project, location=location
    )

    config = AgentEngineConfig(
        display_name=display_name,
        description=description,
        env_vars=env_vars,
        extra_packages=source_packages_list,
        service_account=service_account,
        requirements=requirements_file,
        staging_bucket=staging_bucket_uri,
        labels=labels_dict,
        gcs_dir_name=display_name,
        agent_server_mode=AgentServerMode.EXPERIMENTAL,  # Enable bidi streaming
        resource_limits={"cpu": cpu, "memory": memory},
    )

    agent_config = {
        "agent": agent_instance,
        "config": config,
    }
{%- else %}
    # Generate class methods spec from register_operations
    class_methods_list = generate_class_methods_from_agent(agent_instance)

    config = AgentEngineConfig(
        display_name=display_name,
        description=description,
        source_packages=source_packages_list,
        entrypoint_module=entrypoint_module,
        entrypoint_object=entrypoint_object,
        class_methods=class_methods_list,
        env_vars=env_vars,
        service_account=service_account,
        requirements_file=requirements_file,
        labels=labels_dict,
        min_instances=min_instances,
        max_instances=max_instances,
        resource_limits={"cpu": cpu, "memory": memory},
        container_concurrency=container_concurrency,
{%- if cookiecutter.is_adk %}
        agent_framework="google-adk",
{%- endif %}
    )
{%- endif %}

    # Check if an agent with this name already exists
    existing_agents = list(client.agent_engines.list())
    matching_agents = [
        agent
        for agent in existing_agents
        if agent.api_resource.display_name == display_name
    ]

    # Deploy the agent (create or update)
    if matching_agents:
        click.echo(f"\n📝 Updating existing agent: {display_name}")
    else:
        click.echo(f"\n🚀 Creating new agent: {display_name}")

    click.echo("🚀 Deploying to Vertex AI Agent Engine (this can take 3-5 minutes)...")

{%- if cookiecutter.is_adk_live %}
    if matching_agents:
        remote_agent = client.agent_engines.update(
            name=matching_agents[0].api_resource.name,
            agent=agent_instance,
            config=config,
        )
    else:
        remote_agent = client.agent_engines.create(
            agent=agent_instance,
            config=config,
        )
{%- else %}
    if matching_agents:
        remote_agent = client.agent_engines.update(
            name=matching_agents[0].api_resource.name, config=config
        )
    else:
        remote_agent = client.agent_engines.create(config=config)
{%- endif %}

    write_deployment_metadata(remote_agent)
    print_deployment_success(remote_agent, location, project)

    return remote_agent


if __name__ == "__main__":
    deploy_agent_engine_app()
