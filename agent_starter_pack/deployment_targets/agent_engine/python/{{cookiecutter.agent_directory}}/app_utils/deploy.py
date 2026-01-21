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
import warnings
from typing import Any

import click
import google.auth
import vertexai
from google.cloud import resourcemanager_v3
from google.iam.v1 import iam_policy_pb2, policy_pb2
from vertexai._genai import _agent_engines_utils
{%- if cookiecutter.is_adk_live %}
from vertexai._genai.types import (
    AgentEngine,
    AgentEngineConfig,
    AgentServerMode,
    IdentityType,
)
{%- else %}
from vertexai._genai.types import AgentEngine, AgentEngineConfig, IdentityType
{%- endif %}
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

    with open(metadata_file, "w", encoding="utf-8") as f:
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
    agent_card_url = f"https://{location}-aiplatform.googleapis.com/v1beta1/projects/{project}/locations/{location}/reasoningEngines/{agent_engine_id}/a2a/v1/card"
    print(f"🪪 Agent Card URL: {agent_card_url}")
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


def setup_agent_identity(client: Any, project: str, display_name: str) -> Any:
    """Create agent with identity and grant required IAM roles."""
    click.echo(f"\n🔧 Creating agent identity for: {display_name}")
    agent = client.agent_engines.create(
        config={"identity_type": IdentityType.AGENT_IDENTITY}
    )

    roles = [
        "roles/aiplatform.user",
        "roles/serviceusage.serviceUsageConsumer",
        "roles/browser",
        "roles/cloudapiregistry.viewer",
        "roles/logging.logWriter",
        "roles/monitoring.metricWriter",
    ]
    principal = f"principal://{agent.api_resource.spec.effective_identity}"
    click.echo(f"🔐 Granting IAM roles to: {principal}")
    proj_client = resourcemanager_v3.ProjectsClient()
    policy = proj_client.get_iam_policy(
        request=iam_policy_pb2.GetIamPolicyRequest(resource=f"projects/{project}")
    )
    for role in roles:
        policy.bindings.append(policy_pb2.Binding(role=role, members=[principal]))
    proj_client.set_iam_policy(
        request=iam_policy_pb2.SetIamPolicyRequest(
            resource=f"projects/{project}", policy=policy
        )
    )
    click.echo("  ✅ Agent identity ready")
    return agent


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
    "--set-env-vars",
    default=None,
    help="Comma-separated list of environment variables in KEY=VALUE format",
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
@click.option(
    "--agent-identity",
    is_flag=True,
    default=False,
    help="Enable agent identity for per-agent IAM access control (Preview feature)",
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
    set_env_vars: str | None,
    labels: str | None,
    service_account: str | None,
    min_instances: int,
    max_instances: int,
    cpu: str,
    memory: str,
    container_concurrency: int,
    num_workers: int,
    agent_identity: bool,
) -> AgentEngine:
    """Deploy the agent engine app to Vertex AI."""

    logging.basicConfig(level=logging.INFO)
    logging.getLogger("httpx").setLevel(logging.WARNING)

    # Parse CLI environment variables and labels
    env_vars = parse_key_value_pairs(set_env_vars)
    labels_dict = parse_key_value_pairs(labels)

    # Set deployment-specific environment variables
    env_vars["GOOGLE_CLOUD_REGION"] = location
    env_vars["NUM_WORKERS"] = str(num_workers)

    # Enable telemetry by default for Agent Engine
    env_vars.setdefault("GOOGLE_CLOUD_AGENT_ENGINE_ENABLE_TELEMETRY", "true")
    env_vars.setdefault("OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT", "true")

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
    params = [
        ("Project", project),
        ("Location", location),
        ("Display Name", display_name),
        ("Min Instances", min_instances),
        ("Max Instances", max_instances),
        ("CPU", cpu),
        ("Memory", memory),
        ("Container Concurrency", container_concurrency),
    ]
    if service_account:
        params.append(("Service Account", service_account))
    if agent_identity:
        params.append(("Agent Identity", "Enabled (Preview)"))
    for name, value in params:
        click.echo(f"  {name}: {value}")
    if env_vars:
        click.echo("\n🌍 Environment Variables:")
        for key, value in sorted(env_vars.items()):
            click.echo(f"  {key}: {value}")

    source_packages_list = list(source_packages)

    # Initialize vertexai client
    # Use v1beta1 API when agent identity is enabled (required for identity_type)
    http_options = {"api_version": "v1beta1"} if agent_identity else None
    client = vertexai.Client(
        project=project,
        location=location,
        http_options=http_options,
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
        identity_type=IdentityType.AGENT_IDENTITY if agent_identity else None,
    )
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
{%- if cookiecutter.is_adk and not cookiecutter.is_a2a and not cookiecutter.is_adk_live %}
        agent_framework="google-adk",
{%- endif %}
        identity_type=IdentityType.AGENT_IDENTITY if agent_identity else None,
    )
{%- endif %}

    # Check if an agent with this name already exists
    existing_agents = list(client.agent_engines.list())
    matching_agents = [
        agent
        for agent in existing_agents
        if agent.api_resource.display_name == display_name
    ]

    # Setup agent identity on first deployment
    if agent_identity and not matching_agents:
        matching_agents = [setup_agent_identity(client, project, display_name)]

    # Deploy the agent (create or update)
    action = "Updating" if matching_agents else "Creating"
    click.echo(f"\n🚀 {action} agent: {display_name} (this can take 3-5 minutes)...")

    if matching_agents:
{%- if cookiecutter.is_adk_live %}
        remote_agent = client.agent_engines.update(
            name=matching_agents[0].api_resource.name,
            agent=agent_instance,
            config=config,
        )
{%- else %}
        remote_agent = client.agent_engines.update(
            name=matching_agents[0].api_resource.name, config=config
        )
{%- endif %}
    else:
{%- if cookiecutter.is_adk_live %}
        remote_agent = client.agent_engines.create(
            agent=agent_instance,
            config=config,
        )
{%- else %}
        remote_agent = client.agent_engines.create(config=config)
{%- endif %}

    write_deployment_metadata(remote_agent)
    print_deployment_success(remote_agent, location, project)

    return remote_agent


if __name__ == "__main__":
    deploy_agent_engine_app()
