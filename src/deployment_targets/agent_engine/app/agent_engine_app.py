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
import os
from collections.abc import Iterable, Mapping, Sequence
from typing import (
    Any,
)

import google.auth
import vertexai
from google.cloud import logging as google_cloud_logging
from langchain_core.runnables import RunnableConfig
from traceloop.sdk import Instruments, Traceloop
from vertexai.preview import reasoning_engines

from app.utils.gcs import create_bucket_if_not_exists
from app.utils.tracing import CloudTraceLoggingSpanExporter
from app.utils.typing import Feedback, InputChat, dumpd, ensure_valid_config

logging.basicConfig(
    level=logging.INFO,
)


class AgentEngineApp:
    """Class for managing agent engine functionality."""

    def __init__(
        self, project_id: str | None = None, env_vars: dict[str, str] | None = None
    ) -> None:
        """Initialize the AgentEngineApp variables"""
        self.project_id = project_id
        self.env_vars = env_vars if env_vars is not None else {}

    def set_up(self) -> None:
        """The set_up method is used to define application initialization logic"""
        import os

        for k, v in self.env_vars.items():
            os.environ[k] = v

        # Lazy import agent at setup time to avoid deployment dependencies
        from app.agent import agent

        logging_client = google_cloud_logging.Client(project=self.project_id)
        self.logger = logging_client.logger(__name__)

        # Initialize Telemetry
        try:
            Traceloop.init(
                app_name="{{cookiecutter.project_name}}",
                disable_batch=False,
                exporter=CloudTraceLoggingSpanExporter(project_id=self.project_id),
                instruments={Instruments.LANGCHAIN, Instruments.CREW},
            )
        except Exception as e:
            logging.error("Failed to initialize Telemetry: %s", str(e))

        self.runnable = agent

    # Add any additional variables here that should be included in the tracing logs
    def set_tracing_properties(self, config: RunnableConfig | None) -> None:
        """Sets tracing association properties for the current request.

        Args:
            config: Optional RunnableConfig containing request metadata
        """
        config = ensure_valid_config(config)
        Traceloop.set_association_properties(
            {
                "log_type": "tracing",
                "run_id": str(config["run_id"]),
                "user_id": config["metadata"].pop("user_id", "None"),
                "session_id": config["metadata"].pop("session_id", "None"),
                "commit_sha": os.environ.get("COMMIT_SHA", "None"),
            }
        )

    def stream_query(
        self,
        *,
        input: str | Mapping,
        config: RunnableConfig | None = None,
        **kwargs: Any,
    ) -> Iterable[Any]:
        """Stream responses from the agent for a given input."""

        config = ensure_valid_config(config)
        self.set_tracing_properties(config=config)
        # Validate input. We assert the input is a list of messages
        input_chat = InputChat.model_validate(input)

        for chunk in self.runnable.stream(
            input=input_chat, config=config, **kwargs, stream_mode="messages"
        ):
            dumped_chunk = dumpd(chunk)
            yield dumped_chunk

    def register_feedback(self, feedback: dict[str, Any]) -> None:
        """Collect and log feedback."""
        feedback_obj = Feedback.model_validate(feedback)
        self.logger.log_struct(feedback_obj.model_dump(), severity="INFO")

    def query(
        self,
        *,
        input: str | Mapping,
        config: RunnableConfig | None = None,
        **kwargs: Any,
    ) -> Any:
        """Process a single input and return the agent's response."""
        return dumpd(self.runnable.invoke(input=input, config=config, **kwargs))

    def register_operations(self) -> Mapping[str, Sequence]:
        """Registers the operations of the Agent.

        This mapping defines how different operation modes (e.g., "", "stream")
        are implemented by specific methods of the Agent.  The "default" mode,
        represented by the empty string ``, is associated with the `query` API,
        while the "stream" mode is associated with the `stream_query` API.

        Returns:
            Mapping[str, Sequence[str]]: A mapping of operation modes to a list
            of method names that implement those operation modes.
        """
        return {
            "": ["query", "register_feedback"],
            "stream": ["stream_query"],
        }


def deploy_agent_engine_app(
    project: str,
    location: str,
    agent_name: str | None = None,
    requirements_file: str = ".requirements.txt",
    extra_packages: list[str] = ["./app"],
    env_vars: dict[str, str] | None = None,
) -> reasoning_engines.ReasoningEngine:
    """Deploy the agent engine app to Vertex AI."""

    staging_bucket = f"gs://{project}-agent-engine"

    create_bucket_if_not_exists(
        bucket_name=staging_bucket, project=project, location=location
    )
    vertexai.init(project=project, location=location, staging_bucket=staging_bucket)

    # Read requirements
    with open(requirements_file) as f:
        requirements = f.read().strip().split("\n")

    agent = AgentEngineApp(project_id=project, env_vars=env_vars)

    # Common configuration for both create and update operations
    agent_config = {
        "reasoning_engine": agent,
        "display_name": agent_name,
        "description": "This is a sample custom application in Agent Engine that uses LangGraph",
        "extra_packages": extra_packages,
    }
    logging.info(f"Agent config: {agent_config}")
    agent_config["requirements"] = requirements

    # Check if an agent with this name already exists
    existing_agents = reasoning_engines.ReasoningEngine.list(
        filter=f"display_name={agent_name}"
    )

    if existing_agents:
        # Update the existing agent with new configuration
        logging.info(f"Updating existing agent: {agent_name}")
        remote_agent = existing_agents[0].update(**agent_config)
    else:
        # Create a new agent if none exists
        logging.info(f"Creating new agent: {agent_name}")
        remote_agent = reasoning_engines.ReasoningEngine.create(**agent_config)

    config = {
        "remote_agent_engine_id": remote_agent.resource_name,
        "deployment_timestamp": datetime.datetime.now().isoformat(),
    }
    config_file = "deployment_metadata.json"

    with open(config_file, "w") as f:
        json.dump(config, f, indent=2)

    logging.info(f"Agent Engine ID written to {config_file}")

    return remote_agent


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Deploy agent engine app to Vertex AI")
    parser.add_argument(
        "--project",
        default=None,
        help="GCP project ID (defaults to application default credentials)",
    )
    parser.add_argument(
        "--location", default="us-central1", help="GCP region (defaults to us-central1)"
    )
    parser.add_argument(
        "--agent-name",
        default="{{cookiecutter.project_name}}",
        help="Name for the agent engine",
    )
    parser.add_argument(
        "--requirements-file",
        default=".requirements.txt",
        help="Path to requirements.txt file",
    )
    parser.add_argument(
        "--extra-packages",
        nargs="+",
        default=["./app"],
        help="Additional packages to include",
    )
    parser.add_argument(
        "--set-env-vars",
        help="Comma-separated list of environment variables in KEY=VALUE format",
    )
    args = parser.parse_args()

    # Parse environment variables if provided
    env_vars = None
    if args.set_env_vars:
        env_vars = {}
        for pair in args.set_env_vars.split(","):
            key, value = pair.split("=", 1)
            env_vars[key] = value

    if not args.project:
        _, args.project = google.auth.default()

    print("""
    ╔═══════════════════════════════════════════════════════════╗
    ║                                                           ║
    ║   🤖 DEPLOYING AGENT TO VERTEX AI AGENT ENGINE 🤖         ║
    ║                                                           ║
    ╚═══════════════════════════════════════════════════════════╝
    """)

    deploy_agent_engine_app(
        project=args.project,
        location=args.location,
        agent_name=args.agent_name,
        requirements_file=args.requirements_file,
        extra_packages=args.extra_packages,
        env_vars=env_vars,
    )
