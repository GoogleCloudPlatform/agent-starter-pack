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

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.types import (
    Artifact,
    Message,
    Part,
    Role,
    TaskArtifactUpdateEvent,
    TaskState,
    TaskStatus,
    TaskStatusUpdateEvent,
    TextPart,
    UnsupportedOperationError,
)
from a2a.utils.errors import ServerError
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.graph.state import CompiledStateGraph
from pydantic import BaseModel
from typing_extensions import override

from ..converters import (
    convert_a2a_parts_to_langchain_content,
    convert_langchain_content_to_a2a_parts,
)
from .task_result_aggregator import LangGraphTaskResultAggregator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LangGraphAgentExecutorConfig(BaseModel):
    """Configuration for the LangGraphAgentExecutor."""

    enable_streaming: bool = True


class LangGraphAgentExecutor(AgentExecutor):
    """An AgentExecutor that runs a LangGraph agent against an A2A request and
    publishes updates to an event queue."""

    def __init__(
        self,
        *,
        graph: CompiledStateGraph,
        config: LangGraphAgentExecutorConfig | None = None,
    ):
        super().__init__()
        self._graph = graph
        self._config = config or LangGraphAgentExecutorConfig()

    @override
    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        """Cancel the execution."""
        # TODO: Implement proper cancellation logic if needed
        raise ServerError(error=UnsupportedOperationError())

    @override
    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        """Executes an A2A request and publishes updates to the event queue."""

        if not context.message:
            raise ValueError("A2A request must have a message")

        if not context.task_id:
            raise ValueError("task_id is required")
        if not context.context_id:
            raise ValueError("context_id is required")

        task_id = context.task_id
        context_id = context.context_id

        if not context.current_task:
            await event_queue.enqueue_event(
                TaskStatusUpdateEvent(
                    task_id=task_id,
                    status=TaskStatus(
                        state=TaskState.submitted,
                        message=context.message,
                        timestamp=datetime.now(timezone.utc).isoformat(),
                    ),
                    context_id=context_id,
                    final=False,
                )
            )

        try:
            await self._handle_request(context, event_queue)
        except Exception as e:
            logger.error("Error handling A2A request: %s", e, exc_info=True)
            try:
                await event_queue.enqueue_event(
                    TaskStatusUpdateEvent(
                        task_id=task_id,
                        status=TaskStatus(
                            state=TaskState.failed,
                            timestamp=datetime.now(timezone.utc).isoformat(),
                            message=Message(
                                message_id=str(uuid.uuid4()),
                                role=Role.agent,
                                parts=[Part(root=TextPart(text=str(e)))],
                            ),
                        ),
                        context_id=context_id,
                        final=True,
                    )
                )
            except Exception as enqueue_error:
                logger.error(
                    "Failed to publish failure event: %s", enqueue_error, exc_info=True
                )

    async def _handle_request(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        """Handle the A2A request and publish events."""

        graph = self._graph

        if not context.task_id:
            raise ValueError("task_id is required")
        if not context.context_id:
            raise ValueError("context_id is required")

        task_id = context.task_id
        context_id = context.context_id

        await event_queue.enqueue_event(
            TaskStatusUpdateEvent(
                task_id=task_id,
                status=TaskStatus(
                    state=TaskState.working,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                ),
                context_id=context_id,
                final=False,
            )
        )

        # Convert A2A message parts to LangChain content
        message_content = (
            convert_a2a_parts_to_langchain_content(context.message.parts)
            if context.message
            else ""
        )
        messages = [HumanMessage(content=message_content)]
        input_dict = {"messages": messages}

        task_result_aggregator = LangGraphTaskResultAggregator()

        try:
            if self._config.enable_streaming:
                async for chunk in graph.astream(input_dict, stream_mode="messages"):
                    if isinstance(chunk, tuple) and len(chunk) > 0:
                        message = chunk[0]

                        # Process AIMessage chunks
                        if isinstance(message, AIMessage) and message.content:
                            task_result_aggregator.process_message(message)

                            parts = convert_langchain_content_to_a2a_parts(
                                message.content
                            )
                            await event_queue.enqueue_event(
                                TaskStatusUpdateEvent(
                                    task_id=task_id,
                                    status=TaskStatus(
                                        state=TaskState.working,
                                        timestamp=datetime.now(
                                            timezone.utc
                                        ).isoformat(),
                                        message=Message(
                                            message_id=str(uuid.uuid4()),
                                            role=Role.agent,
                                            parts=parts,
                                        ),
                                    ),
                                    context_id=context_id,
                                    final=False,
                                )
                            )

                        # Process ToolMessage chunks (for multimodal content)
                        elif isinstance(message, ToolMessage):
                            task_result_aggregator.process_message(message)
            else:
                result = await graph.ainvoke(input_dict)
                if "messages" in result:
                    for msg in result["messages"]:
                        if isinstance(msg, (AIMessage, ToolMessage)) and msg.content:
                            task_result_aggregator.process_message(msg)
            if (
                task_result_aggregator.task_state == TaskState.working
                and task_result_aggregator.task_status_message is not None
                and task_result_aggregator.task_status_message.parts
            ):
                # Publish the artifact update event as the final result
                await event_queue.enqueue_event(
                    TaskArtifactUpdateEvent(
                        task_id=task_id,
                        last_chunk=True,
                        context_id=context_id,
                        artifact=Artifact(
                            artifact_id=str(uuid.uuid4()),
                            parts=task_result_aggregator.get_final_parts(),
                        ),
                    )
                )
                # Publish the final status update event
                await event_queue.enqueue_event(
                    TaskStatusUpdateEvent(
                        task_id=task_id,
                        status=TaskStatus(
                            state=TaskState.completed,
                            timestamp=datetime.now(timezone.utc).isoformat(),
                        ),
                        context_id=context_id,
                        final=True,
                    )
                )
            else:
                # Publish final status with current task_state and message
                await event_queue.enqueue_event(
                    TaskStatusUpdateEvent(
                        task_id=task_id,
                        status=TaskStatus(
                            state=task_result_aggregator.task_state,
                            timestamp=datetime.now(timezone.utc).isoformat(),
                            message=task_result_aggregator.task_status_message,
                        ),
                        context_id=context_id,
                        final=True,
                    )
                )

        except Exception as e:
            logger.error("Error during graph execution: %s", e, exc_info=True)
            # Update task state to failed using aggregator
            task_result_aggregator.set_failed(str(e))
            raise
