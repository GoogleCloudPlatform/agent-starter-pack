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

# mypy: disable-error-code="attr-defined,arg-type"
{%- if cookiecutter.is_adk %}
{%- if cookiecutter.is_adk_a2a %}
import asyncio
{%- endif %}
import logging
import os
from typing import Any

import google.auth
{%- if cookiecutter.is_adk_a2a %}
import nest_asyncio
{%- endif %}
{%- if cookiecutter.is_adk_a2a %}
from a2a.types import AgentCapabilities, AgentCard, TransportProtocol
from google.adk.a2a.executor.a2a_agent_executor import A2aAgentExecutor
from google.adk.a2a.utils.agent_card_builder import AgentCardBuilder
from google.adk.apps.app import App
{%- endif %}
from google.adk.artifacts import GcsArtifactService
{%- if cookiecutter.is_adk_a2a %}
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
{%- endif %}
from google.cloud import logging as google_cloud_logging
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider, export
{%- if cookiecutter.is_adk_live %}
from vertexai.agent_engines.templates.adk import AdkApp
from vertexai.preview.reasoning_engines import AdkApp as PreviewAdkApp
{%- elif cookiecutter.is_adk_a2a %}
from vertexai.preview.reasoning_engines import A2aAgent
{%- else %}
from vertexai.agent_engines.templates.adk import AdkApp
{%- endif %}
{%- if cookiecutter.is_adk or cookiecutter.is_adk_live %}

from {{cookiecutter.agent_directory}}.agent import app as adk_app
{%- else %}

{%- endif %}
from {{cookiecutter.agent_directory}}.app_utils.tracing import CloudTraceLoggingSpanExporter
from {{cookiecutter.agent_directory}}.app_utils.typing import Feedback
{%- if cookiecutter.is_adk_a2a %}


class AgentEngineApp(A2aAgent):
    @staticmethod
    def create(
        app: App | None = None,
        artifact_service: Any = None,
        session_service: Any = None,
    ) -> Any:
        """Create an AgentEngineApp instance.

        This method detects whether it's being called in an async context (like notebooks
        or Agent Engine) and handles agent card creation appropriately.
        """
        if app is None:
            app = adk_app

        def create_runner() -> Runner:
            """Create a Runner for the AgentEngineApp."""
            return Runner(
                app=app,
                session_service=session_service,
                artifact_service=artifact_service,
            )

        # Build agent card in an async context if needed
        try:
            asyncio.get_running_loop()
            # Running event loop detected - enable nested asyncio.run()
            nest_asyncio.apply()
        except RuntimeError:
            pass

        agent_card = asyncio.run(AgentEngineApp.build_agent_card(app=app))

        return AgentEngineApp(
            agent_executor_builder=lambda: A2aAgentExecutor(runner=create_runner()),
            agent_card=agent_card,
        )

    @staticmethod
    async def build_agent_card(app: App) -> AgentCard:
        """Builds the Agent Card dynamically from the app."""
        agent_card_builder = AgentCardBuilder(
            agent=app.root_agent,
            # Agent Engine does not support streaming yet
            capabilities=AgentCapabilities(streaming=False),
            rpc_url="http://localhost:9999/",
            agent_version=os.getenv("AGENT_VERSION", "0.1.0"),
        )
        agent_card = await agent_card_builder.build()
        agent_card.preferred_transport = TransportProtocol.http_json  # Http Only.
        agent_card.supports_authenticated_extended_card = True
        return agent_card
{% else %}


class AgentEngineApp(AdkApp):
{%- endif %}
    def set_up(self) -> None:
        """Set up logging and tracing for the agent engine app."""
        super().set_up()
        logging.basicConfig(level=logging.INFO)
        logging_client = google_cloud_logging.Client()
        self.logger = logging_client.logger(__name__)
        provider = TracerProvider()
        processor = export.BatchSpanProcessor(
            CloudTraceLoggingSpanExporter(
                project_id=os.environ.get("GOOGLE_CLOUD_PROJECT")
            )
        )
        provider.add_span_processor(processor)
        trace.set_tracer_provider(provider)

    def register_feedback(self, feedback: dict[str, Any]) -> None:
        """Collect and log feedback."""
        feedback_obj = Feedback.model_validate(feedback)
        self.logger.log_struct(feedback_obj.model_dump(), severity="INFO")

    def register_operations(self) -> dict[str, list[str]]:
        """Registers the operations of the Agent.

        Extends the base operations to include feedback registration functionality.
        """
        operations = super().register_operations()
        operations[""] = operations.get("", []) + ["register_feedback"]
{%- if cookiecutter.is_adk_live %}
        # Add bidi_stream_query for adk_live
        operations["bidi_stream"] = ["bidi_stream_query"]
{%- endif %}
        return operations
{%- if cookiecutter.is_adk_a2a %}

    def clone(self) -> "AgentEngineApp":
        """Returns a clone of the Agent Engine application."""
        return self
{%- endif %}
{%- if cookiecutter.is_adk_live %}


# Add bidi_stream_query support from preview AdkApp for adk_live
AgentEngineApp.bidi_stream_query = PreviewAdkApp.bidi_stream_query
{%- endif %}


_, project_id = google.auth.default()
artifacts_bucket_name = os.environ.get("ARTIFACTS_BUCKET_NAME")
{%- if cookiecutter.is_adk_a2a %}
agent_engine = AgentEngineApp.create(
    app=adk_app,
    artifact_service=(
        GcsArtifactService(bucket_name=artifacts_bucket_name)
        if artifacts_bucket_name
        else None
    ),
    session_service=InMemorySessionService(),
)
{%- else %}
artifact_service_builder = (
    lambda: GcsArtifactService(bucket_name=artifacts_bucket_name)
    if artifacts_bucket_name
    else None
)

agent_engine = AgentEngineApp(
    app=adk_app,
    artifact_service_builder=artifact_service_builder,
)
{%- endif -%}
{% else %}

import logging
import os
from collections.abc import Iterable, Mapping
from typing import (
    Any,
)

import google.auth
from google.cloud import logging as google_cloud_logging
from langchain_core.runnables import RunnableConfig
from traceloop.sdk import Instruments, Traceloop

from {{cookiecutter.agent_directory}}.app_utils.tracing import CloudTraceLoggingSpanExporter
from {{cookiecutter.agent_directory}}.app_utils.typing import Feedback, InputChat, dumpd, ensure_valid_config


class AgentEngineApp:
    """Class for managing agent engine functionality."""

    def __init__(self, project_id: str | None = None) -> None:
        """Initialize the AgentEngineApp variables"""
        self.project_id = project_id

    def set_up(self) -> None:
        """The set_up method is used to define application initialization logic"""
        # Lazy import agent at setup time to avoid deployment dependencies
        from {{cookiecutter.agent_directory}}.agent import agent

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

    def register_feedback(self, feedback: dict[str, Any]) -> None:
        """Collect and log feedback."""
        feedback_obj = Feedback.model_validate(feedback)
        self.logger.log_struct(feedback_obj.model_dump(), severity="INFO")

    def register_operations(self) -> dict[str, list[str]]:
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


_, project_id = google.auth.default()
agent_engine = AgentEngineApp(project_id=project_id)
{%- endif %}
