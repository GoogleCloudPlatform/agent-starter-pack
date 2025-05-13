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

{%- if "adk" in cookiecutter.tags %}
{%- if cookiecutter.deployment_target == 'cloud_run' %}
import uuid
from typing import (
    Literal,
)

from google.adk.events.event import Event
from google.genai.types import Content
from pydantic import (
    BaseModel,
    Field,
)
{%- else %}
from typing import (
    Literal,
)

from pydantic import (
    BaseModel,
)
{%- endif %}
{%- else %}
import json
import uuid
from typing import (
    Annotated,
    Any,
    Literal,
)

from langchain_core.load.serializable import Serializable
from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    ToolMessage,
)
from langchain_core.runnables import RunnableConfig
from pydantic import (
    BaseModel,
    Field,
)
{%- endif %}


{%- if "adk" in cookiecutter.tags %}
{%- if cookiecutter.deployment_target == 'cloud_run' %}


class Request(BaseModel):
    """Represents the input for a chat request with optional configuration."""

    message: Content
    events: list[Event]
    user_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))

    model_config = {"extra": "allow"}
{%- endif %}
{%- else %}


class InputChat(BaseModel):
    """Represents the input for a chat session."""

    messages: list[
        Annotated[HumanMessage | AIMessage | ToolMessage, Field(discriminator="type")]
    ] = Field(
        ..., description="The chat messages representing the current conversation."
    )


class Request(BaseModel):
    """Represents the input for a chat request with optional configuration.

    Attributes:
        input: The chat input containing messages and other chat-related data
        config: Optional configuration for the runnable, including tags, callbacks, etc.
    """

    input: InputChat
    config: RunnableConfig | None = None

{%- endif %}


class Feedback(BaseModel):
    """Represents feedback for a conversation."""

    score: int | float
    text: str | None = ""
{%- if "adk" in cookiecutter.tags %}
    invocation_id: str
{%- else %}
    run_id: str
{%- endif %}
    log_type: Literal["feedback"] = "feedback"
    service_name: Literal["{{cookiecutter.project_name}}"] = "{{cookiecutter.project_name}}"
    user_id: str = ""
{% if "adk" not in cookiecutter.tags %}

def ensure_valid_config(config: RunnableConfig | None) -> RunnableConfig:
    """Ensures a valid RunnableConfig by setting defaults for missing fields."""
    if config is None:
        config = RunnableConfig()
    if config.get("run_id") is None:
        config["run_id"] = uuid.uuid4()
    if config.get("metadata") is None:
        config["metadata"] = {}
    return config


def default_serialization(obj: Any) -> Any:
    """
    Default serialization for LangChain objects.
    Converts BaseModel instances to JSON strings.
    """
    if isinstance(obj, Serializable):
        return obj.to_json()


def dumps(obj: Any) -> str:
    """
    Serialize an object to a JSON string.

    For LangChain objects (BaseModel instances), it converts them to
    dictionaries before serialization.

    Args:
        obj: The object to serialize

    Returns:
        JSON string representation of the object
    """
    return json.dumps(obj, default=default_serialization)
{%- if cookiecutter.deployment_target == 'agent_engine' %}


def dumpd(obj: Any) -> Any:
    """
    Convert an object to a JSON-serializable dict.
    Uses default_serialization for handling BaseModel instances.

    Args:
        obj: The object to convert

    Returns:
        Dict/list representation of the object that can be JSON serialized
    """
    return json.loads(dumps(obj))
{%- endif %}
{% endif %}