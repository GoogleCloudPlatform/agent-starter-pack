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
{% if cookiecutter.agent_name == "adk_live" %}
import asyncio
import json
import logging
import os
from collections.abc import Callable
from pathlib import Path

import backoff
import google.auth
from fastapi import FastAPI, HTTPException, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from google.adk.agents.live_request_queue import LiveRequest, LiveRequestQueue
from google.adk.artifacts import GcsArtifactService, InMemoryArtifactService
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.cloud import logging as google_cloud_logging
from vertexai.agent_engines import _utils
from websockets.exceptions import ConnectionClosedError

from .agent import app as adk_app
from .app_utils.telemetry import setup_telemetry
from .app_utils.typing import Feedback

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Get the path to the frontend build directory
current_dir = Path(__file__).parent
frontend_build_dir = current_dir.parent / "frontend" / "build"

# Mount assets if build directory exists
if frontend_build_dir.exists():
    app.mount(
        "/assets",
        StaticFiles(directory=str(frontend_build_dir / "assets")),
        name="assets",
    )
logging_client = google_cloud_logging.Client()
logger = logging_client.logger(__name__)
logging.basicConfig(level=logging.INFO)

setup_telemetry()
_, project_id = google.auth.default()


# Initialize ADK services
session_service = InMemorySessionService()
logs_bucket_name = os.environ.get("LOGS_BUCKET_NAME")
artifact_service = (
    GcsArtifactService(bucket_name=logs_bucket_name)
    if logs_bucket_name
    else InMemoryArtifactService()
)
memory_service = InMemoryMemoryService()

# Initialize ADK runner
runner = Runner(
    app=adk_app,
    session_service=session_service,
    artifact_service=artifact_service,
    memory_service=memory_service,
)


class AgentSession:
    """Manages bidirectional communication between a client and the agent."""

    def __init__(self, websocket: WebSocket) -> None:
        """Initialize the agent session.

        Args:
            websocket: The client websocket connection
        """
        self.websocket = websocket
        self.input_queue: asyncio.Queue[dict] = asyncio.Queue()
        self.user_id: str | None = None
        self.session_id: str | None = None

    async def receive_from_client(self) -> None:
        """Listen for messages from the client and put them in the queue."""
        while True:
            try:
                message = await self.websocket.receive()

                if "text" in message:
                    data = json.loads(message["text"])

                    if isinstance(data, dict):
                        # Skip setup messages - they're for backend logging only
                        if "setup" in data:
                            logger.log_struct(
                                {**data["setup"], "type": "setup"}, severity="INFO"
                            )
                            logging.info(
                                "Received setup message (not forwarding to agent)"
                            )
                            continue

                        # Forward message to agent engine
                        await self.input_queue.put(data)
                    else:
                        logging.warning(
                            f"Received unexpected JSON structure from client: {data}"
                        )

                elif "bytes" in message:
                    # Handle binary data
                    await self.input_queue.put({"binary_data": message["bytes"]})

                else:
                    logging.warning(
                        f"Received unexpected message type from client: {message}"
                    )

            except ConnectionClosedError as e:
                logging.warning(f"Client closed connection: {e}")
                break
            except json.JSONDecodeError as e:
                logging.error(f"Error parsing JSON from client: {e}")
                break
            except Exception as e:
                logging.error(f"Error receiving from client: {e!s}")
                break

    async def run_agent(self) -> None:
        """Run the agent with the input queue using bidi_stream_query protocol."""
        try:
            # Send setupComplete immediately
            setup_complete_response: dict = {"setupComplete": {}}
            await self.websocket.send_json(setup_complete_response)

            # Wait for first request with user_id
            first_request = await self.input_queue.get()
            self.user_id = first_request.get("user_id")
            if not self.user_id:
                raise ValueError("The first request must have a user_id.")

            self.session_id = first_request.get("session_id")
            first_live_request = first_request.get("live_request")

            # Create session if needed
            if not self.session_id:
                session = await session_service.create_session(
                    app_name=adk_app.name,
                    user_id=self.user_id,
                )
                self.session_id = session.id

            # Create LiveRequestQueue
            live_request_queue = LiveRequestQueue()

            # Add first live request if present
            if first_live_request and isinstance(first_live_request, dict):
                live_request_queue.send(LiveRequest.model_validate(first_live_request))

            # Forward requests from input_queue to live_request_queue
            async def _forward_requests() -> None:
                while True:
                    request = await self.input_queue.get()
                    live_request = LiveRequest.model_validate(request)
                    live_request_queue.send(live_request)

            # Forward events from agent to websocket
            async def _forward_events() -> None:
                events_async = runner.run_live(
                    user_id=self.user_id,
                    session_id=self.session_id,
                    live_request_queue=live_request_queue,
                )
                async for event in events_async:
                    event_dict = _utils.dump_event_for_json(event)
                    await self.websocket.send_json(event_dict)

                    # Check for error responses
                    if isinstance(event_dict, dict) and "error" in event_dict:
                        logging.error(f"Agent error: {event_dict['error']}")
                        break

            # Run both tasks
            requests_task = asyncio.create_task(_forward_requests())

            try:
                await _forward_events()
            finally:
                requests_task.cancel()
                try:
                    await requests_task
                except asyncio.CancelledError:
                    pass

        except Exception as e:
            logging.error(f"Error in agent: {e}")
            await self.websocket.send_json({"error": str(e)})


def get_connect_and_run_callable(websocket: WebSocket) -> Callable:
    """Create a callable that handles agent connection with retry logic.

    Args:
        websocket: The client websocket connection

    Returns:
        Callable: An async function that establishes and manages the agent connection
    """

    async def on_backoff(details: backoff._typing.Details) -> None:
        await websocket.send_json(
            {
                "status": f"Model connection error, retrying in {details['wait']} seconds..."
            }
        )

    @backoff.on_exception(
        backoff.expo, ConnectionClosedError, max_tries=10, on_backoff=on_backoff
    )
    async def connect_and_run() -> None:
        logging.info("Starting ADK agent")
        session = AgentSession(websocket)

        logging.info("Starting bidirectional communication with agent")
        await asyncio.gather(
            session.receive_from_client(),
            session.run_agent(),
        )

    return connect_and_run


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """Handle new websocket connections."""
    await websocket.accept()
    connect_and_run = get_connect_and_run_callable(websocket)
    await connect_and_run()


@app.get("/health")
async def health_check() -> dict:
    """Health check endpoint."""
    return {"status": "ok"}


@app.get("/", response_model=None)
async def serve_frontend_root() -> FileResponse | dict:
    """Serve the frontend index.html at the root path."""
    index_file = frontend_build_dir / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    logging.warning(
        "Frontend not built. Run 'npm run build' in the frontend directory."
    )
    return {"status": "ok", "message": "Backend running. Frontend not built."}


@app.get("/{full_path:path}", response_model=None)
async def serve_frontend_spa(full_path: str) -> FileResponse | dict:
    """Catch-all route to serve the frontend for SPA routing.

    This ensures that client-side routes are handled by the React app.
    Excludes API routes (ws, feedback) and assets.
    """
    # Don't intercept API routes
    if full_path.startswith(("ws", "feedback", "assets", "api")):
        raise HTTPException(status_code=404, detail="Not found")

    # Serve index.html for all other routes (SPA routing)
    index_file = frontend_build_dir / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    logging.warning(
        "Frontend not built. Run 'npm run build' in the frontend directory."
    )
    return {"status": "ok", "message": "Backend running. Frontend not built."}
{% elif cookiecutter.is_adk %}
import os
{%- if cookiecutter.is_a2a %}
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
{%- endif %}
{%- if cookiecutter.session_type == "cloud_sql" %}
from urllib.parse import quote
{%- endif %}

import google.auth
{%- if cookiecutter.is_a2a %}
from a2a.server.apps import A2AFastAPIApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard
from a2a.utils.constants import (
    AGENT_CARD_WELL_KNOWN_PATH,
    EXTENDED_AGENT_CARD_PATH,
)
{%- endif %}
from fastapi import FastAPI
{%- if cookiecutter.is_a2a %}
from google.adk.a2a.executor.a2a_agent_executor import A2aAgentExecutor
from google.adk.a2a.utils.agent_card_builder import AgentCardBuilder
from google.adk.artifacts import GcsArtifactService, InMemoryArtifactService
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
{%- else %}
from google.adk.cli.fast_api import get_fast_api_app
{%- endif %}
from google.cloud import logging as google_cloud_logging
{% if cookiecutter.session_type == "agent_engine" -%}
from vertexai import agent_engines
{% endif %}

{%- if cookiecutter.is_a2a %}
from {{cookiecutter.agent_directory}}.agent import app as adk_app
{%- endif %}
from {{cookiecutter.agent_directory}}.app_utils.telemetry import setup_telemetry
from {{cookiecutter.agent_directory}}.app_utils.typing import Feedback

setup_telemetry()
_, project_id = google.auth.default()
logging_client = google_cloud_logging.Client()
logger = logging_client.logger(__name__)
{%- if not cookiecutter.is_a2a %}
allow_origins = (
    os.getenv("ALLOW_ORIGINS", "").split(",") if os.getenv("ALLOW_ORIGINS") else None
)
{%- endif %}

# Artifact bucket for ADK (created by Terraform, passed via env var)
logs_bucket_name = os.environ.get("LOGS_BUCKET_NAME")
{%- if cookiecutter.is_a2a %}
artifact_service = (
    GcsArtifactService(bucket_name=logs_bucket_name)
    if logs_bucket_name
    else InMemoryArtifactService()
)

runner = Runner(
    app=adk_app,
    artifact_service=artifact_service,
    session_service=InMemorySessionService(),
)

request_handler = DefaultRequestHandler(
    agent_executor=A2aAgentExecutor(runner=runner), task_store=InMemoryTaskStore()
)

A2A_RPC_PATH = f"/a2a/{adk_app.name}"


async def build_dynamic_agent_card() -> AgentCard:
    """Builds the Agent Card dynamically from the root_agent."""
    agent_card_builder = AgentCardBuilder(
        agent=adk_app.root_agent,
        capabilities=AgentCapabilities(streaming=True),
        rpc_url=f"{os.getenv('APP_URL', 'http://0.0.0.0:8000')}{A2A_RPC_PATH}",
        agent_version=os.getenv("AGENT_VERSION", "0.1.0"),
    )
    agent_card = await agent_card_builder.build()
    return agent_card


@asynccontextmanager
async def lifespan(app_instance: FastAPI) -> AsyncIterator[None]:
    agent_card = await build_dynamic_agent_card()
    a2a_app = A2AFastAPIApplication(agent_card=agent_card, http_handler=request_handler)
    a2a_app.add_routes_to_app(
        app_instance,
        agent_card_url=f"{A2A_RPC_PATH}{AGENT_CARD_WELL_KNOWN_PATH}",
        rpc_url=A2A_RPC_PATH,
        extended_agent_card_url=f"{A2A_RPC_PATH}{EXTENDED_AGENT_CARD_PATH}",
    )
    yield


app = FastAPI(
    title="{{cookiecutter.project_name}}",
    description="API for interacting with the Agent {{cookiecutter.project_name}}",
    lifespan=lifespan,
)
{%- else %}

AGENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

{%- if cookiecutter.session_type == "cloud_sql" %}
# Cloud SQL session configuration
db_user = os.environ.get("DB_USER", "postgres")
db_name = os.environ.get("DB_NAME", "postgres")
db_pass = os.environ.get("DB_PASS")
instance_connection_name = os.environ.get("INSTANCE_CONNECTION_NAME")

session_service_uri = None
if instance_connection_name and db_pass:
    # Use Unix socket for Cloud SQL
    # URL-encode username and password to handle special characters (e.g., '[', '?', '#', '$')
    # These characters can cause URL parsing errors, especially '[' which triggers IPv6 validation
    encoded_user = quote(db_user, safe="")
    encoded_pass = quote(db_pass, safe="")
    # URL-encode the connection name to prevent colons from being misinterpreted
    encoded_instance = instance_connection_name.replace(":", "%3A")

    session_service_uri = (
        f"postgresql+asyncpg://{encoded_user}:{encoded_pass}@"
        f"/{db_name}"
        f"?host=/cloudsql/{encoded_instance}"
    )
{%- elif cookiecutter.session_type == "agent_engine" %}
# Agent Engine session configuration
# Check if we should use in-memory session for testing (set USE_IN_MEMORY_SESSION=true for E2E tests)
use_in_memory_session = os.environ.get("USE_IN_MEMORY_SESSION", "").lower() in (
    "true",
    "1",
    "yes",
)

if use_in_memory_session:
    # Use in-memory session for local testing
    session_service_uri = None
else:
    # Use environment variable for agent name, default to project name
    default_agent_name = "{{cookiecutter.project_name}}"
    agent_name = os.environ.get("AGENT_ENGINE_SESSION_NAME", default_agent_name)

    # Check if an agent with this name already exists
    existing_agents = list(agent_engines.list(filter=f"display_name={agent_name}"))

    if existing_agents:
        # Use the existing agent
        agent_engine = existing_agents[0]
    else:
        # Create a new agent if none exists
        agent_engine = agent_engines.create(display_name=agent_name)

    session_service_uri = f"agentengine://{agent_engine.resource_name}"
{%- else %}
# In-memory session configuration - no persistent storage
session_service_uri = None
{%- endif %}

artifact_service_uri = f"gs://{logs_bucket_name}" if logs_bucket_name else None

app: FastAPI = get_fast_api_app(
    agents_dir=AGENT_DIR,
    web=True,
    artifact_service_uri=artifact_service_uri,
    allow_origins=allow_origins,
    session_service_uri=session_service_uri,
    otel_to_cloud=True,
)
app.title = "{{cookiecutter.project_name}}"
app.description = "API for interacting with the Agent {{cookiecutter.project_name}}"
{%- endif %}
{% else %}
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from a2a.server.apps import A2AFastAPIApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentSkill
from a2a.utils.constants import (
    AGENT_CARD_WELL_KNOWN_PATH,
    EXTENDED_AGENT_CARD_PATH,
)
from fastapi import FastAPI
from google.cloud import logging as google_cloud_logging

from {{cookiecutter.agent_directory}}.agent import root_agent
from {{cookiecutter.agent_directory}}.app_utils.executor.a2a_agent_executor import (
    LangGraphAgentExecutor,
)
from {{cookiecutter.agent_directory}}.app_utils.telemetry import setup_telemetry
from {{cookiecutter.agent_directory}}.app_utils.typing import Feedback

setup_telemetry()

request_handler = DefaultRequestHandler(
    agent_executor=LangGraphAgentExecutor(graph=root_agent),
    task_store=InMemoryTaskStore(),
)

A2A_RPC_PATH = "/a2a/{{cookiecutter.agent_directory}}"


def build_agent_card() -> AgentCard:
    """Builds the Agent Card for the LangGraph agent."""
    skill = AgentSkill(
        id="root_agent-get_weather",
        name="get_weather",
        description="Simulates a web search. Use it get information on weather.",
        tags=["llm", "tools"],
        examples=["What's the weather in San Francisco?"],
    )
    agent_card = AgentCard(
        name="root_agent",
        description="API for interacting with the Agent {{cookiecutter.project_name}}",
        url=f"{os.getenv('APP_URL', 'http://0.0.0.0:8000')}{A2A_RPC_PATH}",
        version=os.getenv("AGENT_VERSION", "0.1.0"),
        default_input_modes=["text/plain"],
        default_output_modes=["text/plain"],
        capabilities=AgentCapabilities(streaming=True),
        skills=[skill],
    )
    return agent_card


@asynccontextmanager
async def lifespan(app_instance: FastAPI) -> AsyncIterator[None]:
    agent_card = build_agent_card()
    a2a_app = A2AFastAPIApplication(agent_card=agent_card, http_handler=request_handler)
    a2a_app.add_routes_to_app(
        app_instance,
        agent_card_url=f"{A2A_RPC_PATH}{AGENT_CARD_WELL_KNOWN_PATH}",
        rpc_url=A2A_RPC_PATH,
        extended_agent_card_url=f"{A2A_RPC_PATH}{EXTENDED_AGENT_CARD_PATH}",
    )
    yield


# Initialize FastAPI app and logging
app = FastAPI(
    title="{{cookiecutter.project_name}}",
    description="API for interacting with the Agent {{cookiecutter.project_name}}",
    lifespan=lifespan,
)

logging_client = google_cloud_logging.Client()
logger = logging_client.logger(__name__)
{% endif %}

@app.post("/feedback")
def collect_feedback(feedback: Feedback) -> dict[str, str]:
    """Collect and log feedback.

    Args:
        feedback: The feedback data to log

    Returns:
        Success message
    """
    logger.log_struct(feedback.model_dump(), severity="INFO")
    return {"status": "success"}


# Main execution
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
