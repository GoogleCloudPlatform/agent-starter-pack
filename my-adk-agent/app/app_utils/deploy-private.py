# Copyright 2026 Google. This software is provided as-is, without warranty or
# representation for any use or purpose. Your use of it is subject to your
# agreement with Google.

"""Deployment utilities for Vertex AI Agent Engine.
This module provides a CLI and helper functions to deploy ADK-based agents
to Vertex AI Agent Engine, managing configurations, environment variables,
and secrets.
"""

import asyncio
import datetime
import importlib
import inspect
import json
import logging
import warnings
from pathlib import Path
from typing import Any, cast

import click
import google.auth
import vertexai
from vertexai._genai import Client, _agent_engines_utils
from vertexai._genai.types import AgentEngine, AgentEngineConfig
from vertexai._genai.types.common import DnsPeeringConfig, PscInterfaceConfig

from penalty_contest_agent.app_utils.deploy_utils import (
    DeploymentConfig,
    format_env_value,
    parse_key_value_pairs,
    parse_secrets,
)

# =============================================================================
# Configuration & Constants
# =============================================================================

# Suppress google-cloud-storage version compatibility warning
warnings.filterwarnings(
    "ignore", category=FutureWarning, module="google.cloud.aiplatform"
)

METADATA_FILE = "deployment_metadata.json"

# =============================================================================
# Deployment Orchestrator
# =============================================================================


class DeploymentOrchestrator:
    """Manages the end-to-end lifecycle of an Agent Engine deployment.
    This class orchestrates the process of importing the agent, generating
    the required method specifications, handling existing resources,
    managing secrets, and finalizing the deployment on Vertex AI.
    """

    def __init__(self, config: DeploymentConfig):
        self.config = config
        self.client = Client(
            project=config.project,
            location=config.location,
        )
        vertexai.init(project=config.project, location=config.location)

    def _generate_methods_spec(self, agent_instance: Any) -> list[dict[str, Any]]:
        """Generate method specifications from agent's registered operations."""
        registered_ops = _agent_engines_utils._get_registered_operations(
            agent=agent_instance
        )
        spec = _agent_engines_utils._generate_class_methods_spec_or_raise(
            agent=agent_instance,
            operations=registered_ops,
        )
        return [_agent_engines_utils._to_dict(m) for m in spec]

    def _import_agent(self) -> Any:
        """Dynamically imports the agent instance."""
        logging.info(
            f"Importing {self.config.entrypoint_module}.{self.config.entrypoint_object}"
        )
        module = importlib.import_module(self.config.entrypoint_module)
        agent_instance = getattr(module, self.config.entrypoint_object)

        if inspect.iscoroutine(agent_instance):
            logging.info(
                f"Detected coroutine, awaiting {self.config.entrypoint_object}..."
            )
            agent_instance = asyncio.run(agent_instance)
        return agent_instance

    def _get_matching_agents(self) -> list[Any]:
        """Finds existing agents with the same display name."""
        all_agents = list(self.client.agent_engines.list())
        logging.info(f"Found {len(all_agents)} total agents in {self.config.location}")

        matches = []
        for a in all_agents:
            # Check multiple possible attribute locations for robustness
            name = getattr(a, "display_name", None) or getattr(
                a.api_resource, "display_name", None
            )
            if name == self.config.display_name:
                matches.append(a)

        if matches:
            logging.info(f"Matched existing agent: {matches[0].api_resource.name}")
        return matches

    def _handle_secrets_clearing(
        self, remote_agent: Any, has_existing: bool, raw_secrets: str | None
    ) -> None:
        """Explicitly clear secrets if they were removed in the CLI."""
        # If set_secrets was passed as an empty string but we have existing secrets
        if raw_secrets is not None and not self.config.env_vars and has_existing:
            clear_op = self.client.agent_engines._update(
                name=remote_agent.api_resource.name,
                config={
                    "spec": {"deployment_spec": {"secret_env": []}},
                    "update_mask": "spec.deployment_spec.secret_env",
                },
            )
            _agent_engines_utils._await_operation(
                operation_name=cast(str, clear_op.name),
                get_operation_fn=cast(
                    Any, self.client.agent_engines._get_agent_operation
                ),
            )

    def run(self, raw_secrets: str | None) -> AgentEngine:
        """Executes the deployment process."""
        self._print_banner()
        self._log_parameters()

        # 1. Prepare agent and specs
        agent_instance = self._import_agent()
        methods_spec = self._generate_methods_spec(agent_instance)

        # 2. Build configuration
        psc_config = None
        if self.config.network_attachment:
            dns_peering_configs = None
            if self.config.vpc_network and self.config.dns_peering_domains:
                dns_peering_configs = [
                    DnsPeeringConfig(
                        domain=domain if domain.endswith(".") else f"{domain}.",
                        target_project=self.config.project,
                        target_network=self.config.vpc_network,
                    )
                    for domain in self.config.dns_peering_domains
                ]

            psc_config = PscInterfaceConfig(
                network_attachment=self.config.network_attachment,
                dns_peering_configs=dns_peering_configs,
            )

        engine_config = AgentEngineConfig(
            display_name=self.config.display_name,
            description=self.config.description,
            source_packages=self.config.source_packages,
            entrypoint_module=self.config.entrypoint_module,
            entrypoint_object=self.config.entrypoint_object,
            class_methods=methods_spec,
            env_vars=self.config.env_vars,
            service_account=self.config.service_account,
            requirements_file=self.config.requirements_file,
            labels=self.config.labels,
            min_instances=self.config.min_instances,
            max_instances=self.config.max_instances,
            resource_limits={"cpu": self.config.cpu, "memory": self.config.memory},
            container_concurrency=self.config.container_concurrency,
            agent_framework="google-adk",
            psc_interface_config=psc_config,
        )

        # 3. Check for existing agents
        matching_agents = self._get_matching_agents()
        action = "Updating" if matching_agents else "Creating"
        msg = (
            f"\n🚀 {action} agent: {self.config.display_name} "
            "(this can take 3-5 minutes)..."
        )
        click.echo(msg)

        # 4. Perform deployment
        if matching_agents:
            remote_agent = self.client.agent_engines.update(
                name=matching_agents[0].api_resource.name, config=engine_config
            )
        else:
            remote_agent = self.client.agent_engines.create(config=engine_config)

        # 5. Post-deployment tasks
        self._handle_secrets_clearing(remote_agent, bool(matching_agents), raw_secrets)
        self._write_metadata(remote_agent)
        self._print_success(remote_agent)

        return remote_agent

    def _print_banner(self) -> None:
        """Prints the deployment banner."""
        print("""
    ╔═══════════════════════════════════════════════════════════╗
    ║                                                           ║
    ║   🤖 DEPLOYING AGENT TO VERTEX AI AGENT ENGINE 🤖         ║
    ║                                                           ║
    ╚═══════════════════════════════════════════════════════════╝
    """)

    def _log_parameters(self) -> None:
        """Logs the deployment parameters to the console."""
        click.echo("\n📋 Deployment Parameters:")
        params = [
            ("Project", self.config.project),
            ("Location", self.config.location),
            ("Display Name", self.config.display_name),
            ("Min Instances", self.config.min_instances),
            ("Max Instances", self.config.max_instances),
            ("CPU", self.config.cpu),
            ("Memory", self.config.memory),
            ("Container Concurrency", self.config.container_concurrency),
        ]
        if self.config.service_account:
            params.append(("Service Account", self.config.service_account))

        for name, value in params:
            click.echo(f"  {name}: {value}")

        if self.config.env_vars:
            click.echo("\n🌍 Environment Variables:")
            for key, value in sorted(self.config.env_vars.items()):
                click.echo(f"  {key}: {format_env_value(value)}")

    def _write_metadata(self, remote_agent: Any) -> None:
        """Writes deployment metadata to a JSON file."""
        metadata = {
            "remote_agent_engine_id": remote_agent.api_resource.name,
            "deployment_target": "agent_engine",
            "is_a2a": False,
            "deployment_timestamp": datetime.datetime.now().isoformat(),
        }
        with Path(METADATA_FILE).open("w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)
        logging.info(f"Agent Engine ID written to {METADATA_FILE}")

    def _print_success(self, remote_agent: Any) -> None:
        """Prints the success message and URLs."""
        resource_name = remote_agent.api_resource.name
        agent_id = resource_name.split("/")[-1]
        project_num = resource_name.split("/")[1]

        print("\n✅ Deployment successful!")

        # Identify the effective service account
        custom_sa = remote_agent.api_resource.spec.service_account
        if custom_sa:
            print(f"Service Account (Custom): {custom_sa}")
        else:
            default_sa = (
                f"service-{project_num}@gcp-sa-aiplatform-re.iam.gserviceaccount.com"
            )
            print(f"Service Account (Default): {default_sa}")

        url = (
            f"https://console.cloud.google.com/vertex-ai/agents/agent-engines/"
            f"locations/{self.config.location}/agent-engines/{agent_id}/"
            f"playground?project={self.config.project}"
        )
        print(f"\n📊 Open Console Playground: {url}\n")


# =============================================================================
# CLI Entrypoint
# =============================================================================


@click.command()
@click.option("--project", default=None, help="GCP project ID")
@click.option("--location", required=True, help="GCP region (e.g. us-central1)")
@click.option("--display-name", required=True, help="Display name for the agent")
@click.option(
    "--description", default="Agent to analyze Sabesp penalties.", help="Description"
)
@click.option(
    "--source-packages",
    multiple=True,
    default=["./penalty_contest_agent"],
    help="Packages",
)
@click.option(
    "--entrypoint-module",
    default="penalty_contest_agent.agent_engine_app",
    help="Entrypoint",
)
@click.option("--entrypoint-object", default="agent_engine", help="Entrypoint object")
@click.option(
    "--requirements-file",
    default="penalty_contest_agent/app_utils/.requirements.txt",
    help="Reqs",
)
@click.option(
    "--set-env-vars",
    "env_vars_list",
    multiple=True,
    help="KEY=VALUE vars. Can be used multiple times.",
)
@click.option(
    "--set-secrets",
    "secrets_list",
    multiple=True,
    help="KEY=SECRET_ID specs. Can be used multiple times.",
)
@click.option("--labels", default=None, help="KEY=VALUE labels")
@click.option("--service-account", default=None, help="Service account")
@click.option("--min-instances", type=int, default=1, help="Min instances")
@click.option("--max-instances", type=int, default=10, help="Max instances")
@click.option("--cpu", default="4", help="CPU")
@click.option("--memory", default="8Gi", help="Memory")
@click.option("--container-concurrency", type=int, default=9, help="Concurrency")
@click.option("--num-workers", type=int, default=1, help="Workers")
@click.option("--network-attachment", default=None, help="VPC Network Attachment")
@click.option("--vpc-network", default=None, help="VPC Network for DNS Peering")
@click.option(
    "--dns-peering-domains",
    multiple=True,
    help="Private DNS zones for PSC. Can be used multiple times.",
)
def deploy_agent_engine_app(  # noqa: PLR0913
    project: str | None,
    location: str,
    display_name: str,
    description: str,
    source_packages: tuple[str, ...],
    entrypoint_module: str,
    entrypoint_object: str,
    requirements_file: str,
    env_vars_list: tuple[str, ...],
    secrets_list: tuple[str, ...],
    labels: str | None,
    service_account: str | None,
    min_instances: int,
    max_instances: int,
    cpu: str,
    memory: str,
    container_concurrency: int,
    num_workers: int,
    network_attachment: str | None,
    vpc_network: str | None,
    dns_peering_domains: tuple[str, ...],
) -> AgentEngine:
    """CLI to deploy the agent engine app to Vertex AI."""
    logging.basicConfig(level=logging.INFO)
    logging.getLogger("httpx").setLevel(logging.WARNING)

    # 1. Parse Inputs
    # We initialize env_vars as empty. All runtime config is injected via Makefile.
    env_vars: dict[str, Any] = {}

    # Handle DNS Peering Domains
    dns_peering_domains_list = []
    # Support both multiple flags and comma-separated values within a flag
    for d in dns_peering_domains:
        dns_peering_domains_list.extend(
            [item.strip() for item in d.split(",") if item.strip()]
        )

    # Add/Overwrite with CLI provided vars
    for ev in env_vars_list:
        parsed = parse_key_value_pairs(ev)
        env_vars.update({k: v for k, v in parsed.items() if v})

    # Secrets take precedence over plain env vars
    for sec in secrets_list:
        parsed_sec = parse_secrets(sec)
        env_vars.update({k: v for k, v in parsed_sec.items() if v.get("secret")})

    if not project:
        _, project = google.auth.default()
    if not project:
        raise ValueError("Project ID must be specified.")

    # 2. Inject platform-specific variables for observability and runtime scaling.
    # These settings enable the Agent Engine observability dashboard in the
    # Google Cloud Console and configure the container's worker process count.
    env_vars.update(
        {
            "NUM_WORKERS": str(num_workers),
            "GOOGLE_CLOUD_AGENT_ENGINE_ENABLE_TELEMETRY": "true",
            "OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT": "SPAN_AND_EVENT",
        }
    )

    # 3. Create config and run orchestrator
    config = DeploymentConfig(
        project=project,
        location=location,
        display_name=display_name,
        description=description,
        source_packages=list(source_packages),
        entrypoint_module=entrypoint_module,
        entrypoint_object=entrypoint_object,
        requirements_file=requirements_file,
        env_vars=env_vars,
        labels=parse_key_value_pairs(labels),
        service_account=service_account,
        min_instances=min_instances,
        max_instances=max_instances,
        cpu=cpu,
        memory=memory,
        container_concurrency=container_concurrency,
        num_workers=num_workers,
        network_attachment=network_attachment,
        vpc_network=vpc_network,
        dns_peering_domains=dns_peering_domains_list,
    )

    orchestrator = DeploymentOrchestrator(config)
    # Join all secrets into a single string for clearing logic if needed
    all_secrets_str = ",".join(secrets_list) if secrets_list else None
    return orchestrator.run(raw_secrets=all_secrets_str)


if __name__ == "__main__":
    deploy_agent_engine_app()