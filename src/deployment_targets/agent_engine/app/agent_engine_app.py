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

# mypy: disable-error-code="attr-defined"
{% if "adk" in cookiecutter.tags %}
import datetime
import json
import logging
import uuid
from collections.abc import Iterable, Mapping, Sequence
from typing import (
    Any,
)

import google.auth
import vertexai
from google.adk.agents.run_config import RunConfig, StreamingMode
from google.adk.events.event import Event
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.cloud import logging as google_cloud_logging
from google.genai.types import Content
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider, export
from vertexai import agent_engines

from app.utils.gcs import create_bucket_if_not_exists
from app.utils.tracing import CloudTraceLoggingSpanExporter
from app.utils.typing import Feedback
{% else %}
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
from vertexai import agent_engines

from app.utils.gcs import create_bucket_if_not_exists
from app.utils.tracing import CloudTraceLoggingSpanExporter
from app.utils.typing import Feedback, InputChat, dumpd, ensure_valid_config
{% endif %}

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
{%- if "adk" in cookiecutter.tags %}
        from app.agent import root_agent

        self.root_agent = root_agent
{%- else %}
        from app.agent import agent
{% endif %}
        logging_client = google_cloud_logging.Client(project=self.project_id)
        self.logger = logging_client.logger(__name__)
{% if "adk" in cookiecutter.tags %}
        provider = TracerProvider()
        processor = export.BatchSpanProcessor(
            CloudTraceLoggingSpanExporter(project_id=self.project_id)
        )
        provider.add_span_processor(processor)
        trace.set_tracer_provider(provider)

        self.app_name = "adk-agent"
{%- else %}
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
{%- endif %}
{%- if "adk" not in cookiecutter.tags %}

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
{%- endif %}
{%- if "adk" in cookiecutter.tags %}

    def stream_query(
        self,
        message: dict[str, Any],
        events: list[dict[Any, Any]],
        user_id: str | None = None,
        session_id: str | None = None,
        **kwargs: Any,
    ) -> Iterable[dict[str, Any]]:
        """Stream responses from the agent for a given input."""
        # Ensure input is valid
        events = [Event.model_validate(event) for event in events]
        message = Content.model_validate(message)
        user_id = user_id or str(uuid.uuid4())
        session_id = session_id or str(uuid.uuid4())

        # Set up stateless session service
        session_service = InMemorySessionService()
        session = session_service.create_session(
            app_name=self.app_name,
            user_id=user_id,
            session_id=session_id,
        )

        # Append each historical event to the session
        for event in events:
            session_service.append_event(session=session, event=event)

        # Initialize runner with the agent
        runner = Runner(
            app_name=self.app_name,
            agent=self.root_agent,
            session_service=session_service,
        )

        # Stream responses
        for event in runner.run(
            user_id=user_id,
            session_id=session_id,
            new_message=message,
            run_config=RunConfig(streaming_mode=StreamingMode.SSE),
        ):
            yield event.model_dump(mode="json")

    def query(
        self,
        message: dict[str, Any],
        events: list[dict[Any, Any]],
        user_id: str | None = None,
        session_id: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Process a single input and return the agent's response."""
        final_response = dict()
        for event_data in self.stream_query(
            message=message,
            events=events,
            user_id=user_id,
            session_id=session_id,
            **kwargs,
        ):
            event = Event.model_validate(event_data)
            if event.is_final_response():
                final_response = event_data
        return final_response
{%- else %}

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

    def query(
        self,
        *,
        input: str | Mapping,
        config: RunnableConfig | None = None,
        **kwargs: Any,
    ) -> Any:
        """Process a single input and return the agent's response."""
        config = ensure_valid_config(config)
        self.set_tracing_properties(config=config)
        return dumpd(self.runnable.invoke(input=input, config=config, **kwargs))
{%- endif %}

    def register_feedback(self, feedback: dict[str, Any]) -> None:
        """Collect and log feedback."""
        feedback_obj = Feedback.model_validate(feedback)
        self.logger.log_struct(feedback_obj.model_dump(), severity="INFO")

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
) -> agent_engines.AgentEngine:
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
        "agent_engine": agent,
        "display_name": agent_name,
        "description": "{{cookiecutter.agent_description}}",
        "extra_packages": extra_packages,
    }
    logging.info(f"Agent config: {agent_config}")
    agent_config["requirements"] = requirements

    # Check if an agent with this name already exists
    existing_agents = list(agent_engines.list(filter=f"display_name={agent_name}"))
    if existing_agents:
        # Update the existing agent with new configuration
        logging.info(f"Updating existing agent: {agent_name}")
        remote_agent = existing_agents[0].update(**agent_config)
    else:
        # Create a new agent if none exists
        logging.info(f"Creating new agent: {agent_name}")
        remote_agent = agent_engines.create(**agent_config)

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
        "--location",
        default="us-central1",
        help="GCP region (defaults to us-central1)",
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
