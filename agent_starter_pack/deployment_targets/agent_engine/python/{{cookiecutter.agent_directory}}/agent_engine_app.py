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

{%- if cookiecutter.is_adk %}
{%- if cookiecutter.is_a2a %}
import asyncio
{%- endif %}
import logging
import os
from typing import Any

{% if cookiecutter.is_a2a -%}
import nest_asyncio
{% endif -%}
import vertexai
{%- if cookiecutter.is_a2a %}
from a2a.types import AgentCapabilities, AgentCard, TransportProtocol
{%- endif %}
from dotenv import load_dotenv
{%- if cookiecutter.is_a2a %}
from google.adk.a2a.executor.a2a_agent_executor import A2aAgentExecutor
from google.adk.a2a.utils.agent_card_builder import AgentCardBuilder
from google.adk.apps import App
{%- endif %}
from google.adk.artifacts import GcsArtifactService, InMemoryArtifactService
{%- if cookiecutter.is_a2a %}
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
{%- endif %}
from google.cloud import logging as google_cloud_logging
{%- if cookiecutter.is_adk_live %}
from vertexai.agent_engines.templates.adk import AdkApp
from vertexai.preview.reasoning_engines import AdkApp as PreviewAdkApp
{%- elif cookiecutter.is_a2a %}
from vertexai.preview.reasoning_engines import A2aAgent
{%- else %}
from vertexai.agent_engines.templates.adk import AdkApp
{%- endif %}
{%- if cookiecutter.is_adk or cookiecutter.is_adk_live %}

from {{cookiecutter.agent_directory}}.agent import app as adk_app
{%- else %}

{%- endif %}
from {{cookiecutter.agent_directory}}.app_utils.telemetry import setup_telemetry
from {{cookiecutter.agent_directory}}.app_utils.typing import Feedback

# Load environment variables from .env file at runtime
load_dotenv()
{%- if cookiecutter.is_a2a %}


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
        """Initialize the agent engine app with logging and telemetry."""
        vertexai.init()
        setup_telemetry()
        super().set_up()
        logging.basicConfig(level=logging.INFO)
        logging_client = google_cloud_logging.Client()
        self.logger = logging_client.logger(__name__)
        if gemini_location:
            os.environ["GOOGLE_CLOUD_LOCATION"] = gemini_location

    def register_feedback(self, feedback: dict[str, Any]) -> None:
        """Collect and log feedback."""
        feedback_obj = Feedback.model_validate(feedback)
        self.logger.log_struct(feedback_obj.model_dump(), severity="INFO")

    def register_operations(self) -> dict[str, list[str]]:
        """Registers the operations of the Agent."""
        operations = super().register_operations()
        operations[""] = operations.get("", []) + ["register_feedback"]
{%- if cookiecutter.is_adk_live %}
        # Add bidi_stream_query for adk_live
        operations["bidi_stream"] = ["bidi_stream_query"]
{%- endif %}
        return operations
{%- if cookiecutter.is_a2a %}

    def clone(self) -> "AgentEngineApp":
        """Returns a clone of the Agent Engine application."""
        return self
{%- endif %}
{%- if cookiecutter.is_adk_live %}


# Add bidi_stream_query support from preview AdkApp for adk_live
AgentEngineApp.bidi_stream_query = PreviewAdkApp.bidi_stream_query
{%- endif %}


gemini_location = os.environ.get("GOOGLE_CLOUD_LOCATION")
logs_bucket_name = os.environ.get("LOGS_BUCKET_NAME")
{%- if cookiecutter.is_a2a %}
agent_engine = AgentEngineApp.create(
    app=adk_app,
    artifact_service=(
        GcsArtifactService(bucket_name=logs_bucket_name)
        if logs_bucket_name
        else InMemoryArtifactService()
    ),
    session_service=InMemorySessionService(),
)
{%- else %}
agent_engine = AgentEngineApp(
    app=adk_app,
    artifact_service_builder=lambda: GcsArtifactService(bucket_name=logs_bucket_name)
    if logs_bucket_name
    else InMemoryArtifactService(),
)
{%- endif -%}
{% else %}

import asyncio
import logging
import os
from typing import Any

import nest_asyncio
import vertexai
from a2a.types import AgentCapabilities, AgentCard, AgentSkill, TransportProtocol
from dotenv import load_dotenv
from google.cloud import logging as google_cloud_logging
from vertexai.preview.reasoning_engines import A2aAgent

from {{cookiecutter.agent_directory}}.agent import root_agent
from {{cookiecutter.agent_directory}}.app_utils.executor.a2a_agent_executor import (
    LangGraphAgentExecutor,
)
from {{cookiecutter.agent_directory}}.app_utils.telemetry import setup_telemetry
from {{cookiecutter.agent_directory}}.app_utils.typing import Feedback

# Load environment variables from .env file at runtime
load_dotenv()

# Capture the location before vertexai.init() might change it
gemini_location = os.environ.get("GOOGLE_CLOUD_LOCATION")


class AgentEngineApp(A2aAgent):
    """Agent Engine App with A2A Protocol support for LangGraph agents."""

    @staticmethod
    def create() -> "AgentEngineApp":
        """Create an AgentEngineApp instance with A2A support.

        This method handles agent card creation in async context.
        """
        # Handle nested asyncio contexts (like notebooks or Agent Engine)
        try:
            asyncio.get_running_loop()
            nest_asyncio.apply()
        except RuntimeError:
            pass

        agent_card = asyncio.run(AgentEngineApp.build_agent_card())

        return AgentEngineApp(
            agent_executor_builder=lambda: LangGraphAgentExecutor(graph=root_agent),
            agent_card=agent_card,
        )

    @staticmethod
    async def build_agent_card() -> AgentCard:
        """Build the Agent Card for the LangGraph agent."""
        skill = AgentSkill(
            id="root_agent-get_weather",
            name="get_weather",
            description="Simulates a web search. Use it get information on weather.",
            tags=["llm", "tools"],
            examples=["Hi!"],
        )
        agent_card = AgentCard(
            name="root_agent",
            description="A base ReAct agent using LangGraph with Agent2Agent (A2A) Protocol support",
            url="http://localhost:9999/",  # RPC URL for Agent Engine
            version=os.getenv("AGENT_VERSION", "0.1.0"),
            default_input_modes=["text/plain"],
            default_output_modes=["text/plain"],
            capabilities=AgentCapabilities(
                streaming=False
            ),  # Agent Engine does not support streaming yet
            skills=[skill],
        )

        agent_card.preferred_transport = TransportProtocol.http_json  # Http Only.
        agent_card.supports_authenticated_extended_card = True

        return agent_card

    def set_up(self) -> None:
        """Initialize the agent engine app with logging and telemetry."""
        vertexai.init()
        setup_telemetry()
        super().set_up()
        logging.basicConfig(level=logging.INFO)
        logging_client = google_cloud_logging.Client()
        self.logger = logging_client.logger(__name__)
        # Restore the original location after set_up() may have changed it
        if gemini_location:
            os.environ["GOOGLE_CLOUD_LOCATION"] = gemini_location

    def register_feedback(self, feedback: dict[str, Any]) -> None:
        """Collect and log feedback."""
        feedback_obj = Feedback.model_validate(feedback)
        self.logger.log_struct(feedback_obj.model_dump(), severity="INFO")

    def register_operations(self) -> dict[str, list[str]]:
        """Registers the operations of the Agent."""
        operations = super().register_operations()
        operations[""] = operations.get("", []) + ["register_feedback"]
        return operations

    def clone(self) -> "AgentEngineApp":
        """Returns a clone of the Agent Engine application."""
        return self


agent_engine = AgentEngineApp.create()
{%- endif %}
