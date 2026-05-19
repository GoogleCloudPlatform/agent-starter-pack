# Copyright 2026 Google LLC
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

import asyncio
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
)
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
        # Cancellation tracking: maps task_id to cancellation event
        self._cancellation_events: dict[str, asyncio.Event] = {}
        # Track active execution tasks for cleanup
        self._active_tasks: dict[str, asyncio.Task] = {}

    @override
    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        """Cancel the execution.

        This method sets the cancellation event for the task and attempts to
        gracefully cancel any in-flight operations. It publishes a cancelled
        status event to the queue.

        Args:
            context: The request context containing task_id and context_id
            event_queue: The event queue for publishing status updates
        """
        if not context.task_id:
            logger.warning("Cannot cancel: task_id is missing from context")
            return

        task_id = context.task_id
        context_id = context.context_id or ""

        logger.info("Cancelling task: %s", task_id)

        # Set the cancellation event to signal running operations
        cancellation_event = self._cancellation_events.get(task_id)
        if cancellation_event:
            cancellation_event.set()
            logger.debug("Cancellation event set for task: %s", task_id)

        # Cancel the active task if it exists
        active_task = self._active_tasks.get(task_id)
        if active_task and not active_task.done():
            logger.debug("Cancelling active asyncio task for: %s", task_id)
            active_task.cancel()
            try:
                # Wait briefly for graceful cancellation
                await asyncio.wait_for(asyncio.shield(active_task), timeout=2.0)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                logger.debug("Active task cancelled or timed out for: %s", task_id)
            except Exception as e:
                logger.warning(
                    "Unexpected error during task cancellation for %s: %s",
                    task_id,
                    e,
                    exc_info=True,
                )

        # Publish cancellation event
        try:
            await event_queue.enqueue_event(
                TaskStatusUpdateEvent(
                    task_id=task_id,
                    status=TaskStatus(
                        state=TaskState.cancelled,
                        timestamp=datetime.now(timezone.utc).isoformat(),
                        message=Message(
                            message_id=str(uuid.uuid4()),
                            role=Role.agent,
                            parts=[Part(root=TextPart(text="Task cancelled by user"))],
                        ),
                    ),
                    context_id=context_id,
                    final=True,
                )
            )
            logger.info("Successfully published cancellation event for task: %s", task_id)
        except Exception as e:
            logger.error(
                "Failed to publish cancellation event for task %s: %s",
                task_id,
                e,
                exc_info=True,
            )
        finally:
            # Clean up tracking dictionaries
            self._cleanup_task_resources(task_id)

    def _cleanup_task_resources(self, task_id: str) -> None:
        """Clean up cancellation events and task references.

        Args:
            task_id: The ID of the task to clean up
        """
        self._cancellation_events.pop(task_id, None)
        self._active_tasks.pop(task_id, None)
        logger.debug("Cleaned up resources for task: %s", task_id)

    def _is_cancelled(self, task_id: str) -> bool:
        """Check if a task has been cancelled.

        Args:
            task_id: The ID of the task to check

        Returns:
            True if the task has been cancelled, False otherwise
        """
        event = self._cancellation_events.get(task_id)
        return event.is_set() if event else False

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

        # Initialize cancellation event for this task
        self._cancellation_events[task_id] = asyncio.Event()

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
            # Create and track the execution task
            execution_task = asyncio.create_task(
                self._handle_request(context, event_queue)
            )
            self._active_tasks[task_id] = execution_task

            # Wait for completion or cancellation
            await execution_task

        except asyncio.CancelledError:
            logger.info("Task execution cancelled for task_id: %s", task_id)
            # Publish cancellation status if not already published
            try:
                await event_queue.enqueue_event(
                    TaskStatusUpdateEvent(
                        task_id=task_id,
                        status=TaskStatus(
                            state=TaskState.cancelled,
                            timestamp=datetime.now(timezone.utc).isoformat(),
                            message=Message(
                                message_id=str(uuid.uuid4()),
                                role=Role.agent,
                                parts=[
                                    Part(
                                        root=TextPart(
                                            text="Task execution was cancelled"
                                        )
                                    )
                                ],
                            ),
                        ),
                        context_id=context_id,
                        final=True,
                    )
                )
            except Exception as enqueue_error:
                logger.error(
                    "Failed to publish cancellation event: %s",
                    enqueue_error,
                    exc_info=True,
                )
            raise
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
            raise
        finally:
            # Always clean up resources
            self._cleanup_task_resources(task_id)

    async def _handle_request(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        """Handle the A2A request and publish events.

        This method checks for cancellation at critical points during execution
        and raises CancelledError if cancellation is detected.

        Args:
            context: The request context
            event_queue: The event queue for publishing updates

        Raises:
            asyncio.CancelledError: If the task is cancelled during execution
        """
        graph = self._graph

        if not context.task_id:
            raise ValueError("task_id is required")
        if not context.context_id:
            raise ValueError("context_id is required")

        task_id = context.task_id
        context_id = context.context_id

        # Check for cancellation before starting
        if self._is_cancelled(task_id):
            logger.info("Task %s cancelled before execution started", task_id)
            raise asyncio.CancelledError()

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
                    # Check for cancellation on each streaming chunk
                    if self._is_cancelled(task_id):
                        logger.info(
                            "Task %s cancelled during streaming, cleaning up", task_id
                        )
                        raise asyncio.CancelledError()

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
                # Check for cancellation before invoking
                if self._is_cancelled(task_id):
                    logger.info("Task %s cancelled before graph invocation", task_id)
                    raise asyncio.CancelledError()

                result = await graph.ainvoke(input_dict)

                # Check for cancellation after invocation
                if self._is_cancelled(task_id):
                    logger.info("Task %s cancelled after graph invocation", task_id)
                    raise asyncio.CancelledError()

                if "messages" in result:
                    for msg in result["messages"]:
                        if isinstance(msg, (AIMessage, ToolMessage)) and msg.content:
                            task_result_aggregator.process_message(msg)
            # Final cancellation check before publishing results
            if self._is_cancelled(task_id):
                logger.info("Task %s cancelled before publishing final results", task_id)
                raise asyncio.CancelledError()

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

        except asyncio.CancelledError:
            # Re-raise to be handled by execute() method
            logger.info("Cancellation detected in _handle_request for task: %s", task_id)
            raise
        except Exception as e:
            logger.error("Error during graph execution: %s", e, exc_info=True)
            # Update task state to failed using aggregator
            task_result_aggregator.set_failed(str(e))
            raise
