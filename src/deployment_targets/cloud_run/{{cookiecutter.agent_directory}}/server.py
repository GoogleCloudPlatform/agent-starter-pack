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
{% if cookiecutter.agent_name == "live_api" %}
import asyncio
import json
import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any, Literal

import backoff
from fastapi import FastAPI, HTTPException, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from google.cloud import logging as google_cloud_logging
from google.genai import types
from google.genai.types import LiveServerToolCall
from pydantic import BaseModel
from websockets.exceptions import ConnectionClosedError

from .agent import MODEL_ID, genai_client, live_connect_config, tool_functions

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

# Mount static files if build directory exists
if frontend_build_dir.exists():
    app.mount(
        "/static",
        StaticFiles(directory=str(frontend_build_dir / "static")),
        name="static",
    )
logging_client = google_cloud_logging.Client()
logger = logging_client.logger(__name__)
logging.basicConfig(level=logging.INFO)


class GeminiSession:
    """Manages bidirectional communication between a client and the Gemini model."""

    def __init__(
        self, session: Any, websocket: WebSocket, tool_functions: dict[str, Callable]
    ) -> None:
        """Initialize the Gemini session.

        Args:
            session: The Gemini session
            websocket: The client websocket connection
            user_id: Unique identifier for this client
            tool_functions: Dictionary of available tool functions
        """
        self.session = session
        self.websocket = websocket
        self.run_id = "n/a"
        self.user_id = "n/a"
        self.tool_functions = tool_functions
        self._tool_tasks: list[asyncio.Task] = []

    async def receive_from_client(self) -> None:
        """Listen for and process messages from the client.

        Continuously receives messages and forwards audio data to Gemini.
        Handles connection errors gracefully.
        """
        while True:
            try:
                data = await self.websocket.receive_json()

                if isinstance(data, dict) and (
                    "realtimeInput" in data or "clientContent" in data
                ):
                    await self.session._ws.send(json.dumps(data))
                elif "setup" in data:
                    self.run_id = data["setup"]["run_id"]
                    self.user_id = data["setup"]["user_id"]
                    logger.log_struct(
                        {**data["setup"], "type": "setup"}, severity="INFO"
                    )
                else:
                    logging.warning(f"Received unexpected input from client: {data}")
            except ConnectionClosedError as e:
                logging.warning(f"Client {self.user_id} closed connection: {e}")
                break
            except Exception as e:
                logging.error(f"Error receiving from client {self.user_id}: {e!s}")
                break

    def _get_func(self, action_label: str | None) -> Callable | None:
        """Get the tool function for a given action label."""
        if action_label is None or action_label == "":
            return None
        return self.tool_functions.get(action_label)

    async def _handle_tool_call(
        self, session: Any, tool_call: LiveServerToolCall
    ) -> None:
        """Process tool calls from Gemini and send back responses."""
        if tool_call.function_calls is None:
            logging.debug("No function calls in tool_call")
            return

        for fc in tool_call.function_calls:
            logging.debug(f"Calling tool function: {fc.name} with args: {fc.args}")
            func = self._get_func(fc.name)
            if func is None:
                logging.error(f"Function {fc.name} not found")
                continue
            args = fc.args if fc.args is not None else {}

            # Handle both async and sync functions appropriately
            if asyncio.iscoroutinefunction(func):
                # Function is already async
                response = await func(**args)
            else:
                # Run sync function in a thread pool to avoid blocking
                response = await asyncio.to_thread(func, **args)

            tool_response = types.LiveClientToolResponse(
                function_responses=[
                    types.FunctionResponse(name=fc.name, id=fc.id, response=response)
                ]
            )
            logging.debug(f"Tool response: {tool_response}")
            await session.send(input=tool_response)

    async def receive_from_gemini(self) -> None:
        """Listen for and process messages from Gemini without blocking."""
        while result := await self.session._ws.recv(decode=False):
            await self.websocket.send_bytes(result)
            raw_message = json.loads(result)
            if "toolCall" in raw_message:
                message = types.LiveServerMessage.model_validate(raw_message)
                tool_call = LiveServerToolCall.model_validate(message.tool_call)
                # Create a separate task to handle the tool call without blocking
                task = asyncio.create_task(
                    self._handle_tool_call(self.session, tool_call)
                )
                self._tool_tasks.append(task)


def get_connect_and_run_callable(websocket: WebSocket) -> Callable:
    """Create a callable that handles Gemini connection with retry logic.

    Args:
        websocket: The client websocket connection

    Returns:
        Callable: An async function that establishes and manages the Gemini connection
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
        async with genai_client.aio.live.connect(
            model=MODEL_ID, config=live_connect_config
        ) as session:
            await websocket.send_json({"status": "Backend is ready for conversation"})
            gemini_session = GeminiSession(
                session=session, websocket=websocket, tool_functions=tool_functions
            )
            logging.info("Starting bidirectional communication")
            await asyncio.gather(
                gemini_session.receive_from_client(),
                gemini_session.receive_from_gemini(),
            )

    return connect_and_run


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """Handle new websocket connections."""
    await websocket.accept()
    connect_and_run = get_connect_and_run_callable(websocket)
    await connect_and_run()


class Feedback(BaseModel):
    """Represents feedback for a conversation."""

    score: int | float
    text: str | None = ""
    run_id: str
    user_id: str | None
    log_type: Literal["feedback"] = "feedback"
{% elif "adk" in cookiecutter.tags %}
import os

import google.auth
from fastapi import FastAPI
from google.adk.cli.fast_api import get_fast_api_app
from google.cloud import logging as google_cloud_logging
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider, export
{%- if cookiecutter.session_type == "agent_engine" %}
from vertexai import agent_engines
{%- endif %}

from {{cookiecutter.agent_directory}}.utils.gcs import create_bucket_if_not_exists
from {{cookiecutter.agent_directory}}.utils.tracing import CloudTraceLoggingSpanExporter
from {{cookiecutter.agent_directory}}.utils.typing import Feedback

_, project_id = google.auth.default()
logging_client = google_cloud_logging.Client()
logger = logging_client.logger(__name__)
allow_origins = (
    os.getenv("ALLOW_ORIGINS", "").split(",") if os.getenv("ALLOW_ORIGINS") else None
)

bucket_name = f"gs://{project_id}-{{cookiecutter.project_name}}-logs"
create_bucket_if_not_exists(
    bucket_name=bucket_name, project=project_id, location="us-central1"
)

provider = TracerProvider()
processor = export.BatchSpanProcessor(CloudTraceLoggingSpanExporter())
provider.add_span_processor(processor)
trace.set_tracer_provider(provider)

AGENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

{%- if cookiecutter.session_type == "alloydb" %}
# AlloyDB session configuration
db_user = os.environ.get("DB_USER", "postgres")
db_name = os.environ.get("DB_NAME", "postgres")
db_pass = os.environ.get("DB_PASS")
db_host = os.environ.get("DB_HOST")

# Set session_service_uri if database credentials are available
session_service_uri = None
if db_host and db_pass:
    session_service_uri = f"postgresql://{db_user}:{db_pass}@{db_host}:5432/{db_name}"
{%- elif cookiecutter.session_type == "agent_engine" %}
# Agent Engine session configuration
# Use environment variable for agent name, default to project name
agent_name = os.environ.get("AGENT_ENGINE_SESSION_NAME", "{{cookiecutter.project_name}}")

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

app: FastAPI = get_fast_api_app(
    agents_dir=AGENT_DIR,
    web=True,
    artifact_service_uri=bucket_name,
    allow_origins=allow_origins,
    session_service_uri=session_service_uri,
)
app.title = "{{cookiecutter.project_name}}"
app.description = "API for interacting with the Agent {{cookiecutter.project_name}}"
{% else %}
import logging
import os
from collections.abc import Generator

from fastapi import FastAPI
from fastapi.responses import RedirectResponse, StreamingResponse
from google.cloud import logging as google_cloud_logging
from langchain_core.runnables import RunnableConfig
from traceloop.sdk import Instruments, Traceloop

from {{cookiecutter.agent_directory}}.agent import agent
from {{cookiecutter.agent_directory}}.utils.tracing import CloudTraceLoggingSpanExporter
from {{cookiecutter.agent_directory}}.utils.typing import Feedback, InputChat, Request, dumps, ensure_valid_config

# Initialize FastAPI app and logging
app = FastAPI(
    title="{{cookiecutter.project_name}}",
    description="API for interacting with the Agent {{cookiecutter.project_name}}",
)
logging_client = google_cloud_logging.Client()
logger = logging_client.logger(__name__)

# Initialize Telemetry
try:
    Traceloop.init(
        app_name=app.title,
        disable_batch=False,
        exporter=CloudTraceLoggingSpanExporter(),
        instruments={Instruments.LANGCHAIN, Instruments.CREW},
    )
except Exception as e:
    logging.error("Failed to initialize Telemetry: %s", str(e))


def set_tracing_properties(config: RunnableConfig) -> None:
    """Sets tracing association properties for the current request.

    Args:
        config: Optional RunnableConfig containing request metadata
    """
    Traceloop.set_association_properties(
        {
            "log_type": "tracing",
            "run_id": str(config.get("run_id", "None")),
            "user_id": config["metadata"].pop("user_id", "None"),
            "session_id": config["metadata"].pop("session_id", "None"),
            "commit_sha": os.environ.get("COMMIT_SHA", "None"),
        }
    )


def stream_messages(
    input: InputChat,
    config: RunnableConfig | None = None,
) -> Generator[str, None, None]:
    """Stream events in response to an input chat.

    Args:
        input: The input chat messages
        config: Optional configuration for the runnable

    Yields:
        JSON serialized event data
    """
    config = ensure_valid_config(config=config)
    set_tracing_properties(config)
    input_dict = input.model_dump()

    for data in agent.stream(input_dict, config=config, stream_mode="messages"):  # type: ignore[arg-type]
        yield dumps(data) + "\n"


# Routes
@app.get("/", response_class=RedirectResponse)
def redirect_root_to_docs() -> RedirectResponse:
    """Redirect the root URL to the API documentation."""
    return RedirectResponse(url="/docs")


@app.post("/stream_messages")
def stream_chat_events(request: Request) -> StreamingResponse:
    """Stream chat events in response to an input request.

    Args:
        request: The chat request containing input and config

    Returns:
        Streaming response of chat events
    """
    return StreamingResponse(
        stream_messages(input=request.input, config=request.config),
        media_type="text/event-stream",
    )
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
{% if cookiecutter.agent_name == "live_api" %}

@app.get("/")
async def serve_frontend_root() -> FileResponse:
    """Serve the frontend index.html at the root path."""
    index_file = frontend_build_dir / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    raise HTTPException(
        status_code=404,
        detail="Frontend not built. Run 'npm run build' in the frontend directory.",
    )


@app.get("/{full_path:path}")
async def serve_frontend_spa(full_path: str) -> FileResponse:
    """Catch-all route to serve the frontend for SPA routing.

    This ensures that client-side routes are handled by the React app.
    Excludes API routes (ws, feedback) and static assets.
    """
    # Don't intercept API routes
    if full_path.startswith(("ws", "feedback", "static", "api")):
        raise HTTPException(status_code=404, detail="Not found")

    # Serve index.html for all other routes (SPA routing)
    index_file = frontend_build_dir / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    raise HTTPException(
        status_code=404,
        detail="Frontend not built. Run 'npm run build' in the frontend directory.",
    )
{% endif %}

# Main execution
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
