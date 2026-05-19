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
"""
Unit tests for the LangGraphAgentExecutor cancellation logic.
"""

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from a2a.server.agent_execution import RequestContext
from a2a.server.events import EventQueue
from a2a.types import Message, Part, Role, TaskState, TextPart


@pytest.fixture
def mock_graph():
    """Create a mock CompiledStateGraph."""
    graph = MagicMock()
    graph.astream = AsyncMock()
    graph.ainvoke = AsyncMock()
    return graph


@pytest.fixture
def mock_event_queue():
    """Create a mock EventQueue."""
    queue = AsyncMock(spec=EventQueue)
    queue.enqueue_event = AsyncMock()
    return queue


@pytest.fixture
def request_context():
    """Create a basic request context."""
    return RequestContext(
        task_id="test-task-123",
        context_id="test-context-456",
        message=Message(
            message_id=str(uuid.uuid4()),
            role=Role.user,
            parts=[Part(root=TextPart(text="Test message"))],
        ),
    )


@pytest.fixture
def executor_module():
    """Import the executor module dynamically."""
    import sys
    from pathlib import Path

    # Get the base_template directory
    base_template = Path(__file__).parent.parent.parent / "{{cookiecutter.agent_directory}}"
    sys.path.insert(0, str(base_template))

    try:
        from app_utils.executor.a2a_agent_executor import (
            LangGraphAgentExecutor,
            LangGraphAgentExecutorConfig,
        )

        return {
            "LangGraphAgentExecutor": LangGraphAgentExecutor,
            "LangGraphAgentExecutorConfig": LangGraphAgentExecutorConfig,
        }
    finally:
        sys.path.pop(0)


@pytest.mark.asyncio
async def test_cancellation_before_execution(
    executor_module, mock_graph, mock_event_queue, request_context
):
    """Test cancellation before execution starts."""
    LangGraphAgentExecutor = executor_module["LangGraphAgentExecutor"]

    executor = LangGraphAgentExecutor(graph=mock_graph)

    # Start execution task
    execution_task = asyncio.create_task(
        executor.execute(request_context, mock_event_queue)
    )

    # Give it a moment to initialize
    await asyncio.sleep(0.01)

    # Cancel immediately
    await executor.cancel(request_context, mock_event_queue)

    # Wait for execution to complete
    with pytest.raises(asyncio.CancelledError):
        await execution_task

    # Verify cancellation event was published
    assert mock_event_queue.enqueue_event.called
    events = [call.args[0] for call in mock_event_queue.enqueue_event.call_args_list]
    cancelled_events = [e for e in events if e.status.state == TaskState.cancelled]
    assert len(cancelled_events) > 0


@pytest.mark.asyncio
async def test_cancellation_during_streaming(
    executor_module, mock_graph, mock_event_queue, request_context
):
    """Test cancellation during streaming execution."""
    LangGraphAgentExecutor = executor_module["LangGraphAgentExecutor"]
    LangGraphAgentExecutorConfig = executor_module["LangGraphAgentExecutorConfig"]

    # Mock streaming response that yields multiple chunks
    async def mock_stream(*args, **kwargs):
        for i in range(10):
            await asyncio.sleep(0.1)  # Simulate slow streaming
            yield (MagicMock(content=f"chunk {i}"),)

    mock_graph.astream.return_value = mock_stream()

    config = LangGraphAgentExecutorConfig(enable_streaming=True)
    executor = LangGraphAgentExecutor(graph=mock_graph, config=config)

    # Start execution
    execution_task = asyncio.create_task(
        executor.execute(request_context, mock_event_queue)
    )

    # Let some chunks process
    await asyncio.sleep(0.25)

    # Cancel mid-stream
    await executor.cancel(request_context, mock_event_queue)

    # Verify task was cancelled
    with pytest.raises(asyncio.CancelledError):
        await execution_task

    # Verify cleanup
    assert request_context.task_id not in executor._cancellation_events
    assert request_context.task_id not in executor._active_tasks


@pytest.mark.asyncio
async def test_cancellation_during_non_streaming(
    executor_module, mock_graph, mock_event_queue, request_context
):
    """Test cancellation during non-streaming execution."""
    LangGraphAgentExecutor = executor_module["LangGraphAgentExecutor"]
    LangGraphAgentExecutorConfig = executor_module["LangGraphAgentExecutorConfig"]

    # Mock slow ainvoke
    async def mock_invoke(*args, **kwargs):
        await asyncio.sleep(1.0)  # Simulate long operation
        return {"messages": []}

    mock_graph.ainvoke = AsyncMock(side_effect=mock_invoke)

    config = LangGraphAgentExecutorConfig(enable_streaming=False)
    executor = LangGraphAgentExecutor(graph=mock_graph, config=config)

    # Start execution
    execution_task = asyncio.create_task(
        executor.execute(request_context, mock_event_queue)
    )

    # Let it start processing
    await asyncio.sleep(0.1)

    # Cancel during execution
    await executor.cancel(request_context, mock_event_queue)

    # Verify cancellation
    with pytest.raises(asyncio.CancelledError):
        await execution_task


@pytest.mark.asyncio
async def test_is_cancelled_flag(executor_module, mock_graph):
    """Test the _is_cancelled method."""
    LangGraphAgentExecutor = executor_module["LangGraphAgentExecutor"]

    executor = LangGraphAgentExecutor(graph=mock_graph)
    task_id = "test-task"

    # Initially not cancelled
    assert not executor._is_cancelled(task_id)

    # Create cancellation event
    executor._cancellation_events[task_id] = asyncio.Event()
    assert not executor._is_cancelled(task_id)

    # Set cancellation
    executor._cancellation_events[task_id].set()
    assert executor._is_cancelled(task_id)


@pytest.mark.asyncio
async def test_cleanup_task_resources(executor_module, mock_graph):
    """Test resource cleanup."""
    LangGraphAgentExecutor = executor_module["LangGraphAgentExecutor"]

    executor = LangGraphAgentExecutor(graph=mock_graph)
    task_id = "test-task"

    # Set up resources
    executor._cancellation_events[task_id] = asyncio.Event()
    executor._active_tasks[task_id] = asyncio.create_task(asyncio.sleep(0))

    # Clean up
    executor._cleanup_task_resources(task_id)

    # Verify cleanup
    assert task_id not in executor._cancellation_events
    assert task_id not in executor._active_tasks


@pytest.mark.asyncio
async def test_cancel_without_task_id(executor_module, mock_graph, mock_event_queue):
    """Test cancel with missing task_id."""
    LangGraphAgentExecutor = executor_module["LangGraphAgentExecutor"]

    executor = LangGraphAgentExecutor(graph=mock_graph)
    context = RequestContext(task_id=None, context_id="test-context")

    # Should not raise, just log warning
    await executor.cancel(context, mock_event_queue)


@pytest.mark.asyncio
async def test_cancel_nonexistent_task(
    executor_module, mock_graph, mock_event_queue, request_context
):
    """Test cancelling a task that doesn't exist."""
    LangGraphAgentExecutor = executor_module["LangGraphAgentExecutor"]

    executor = LangGraphAgentExecutor(graph=mock_graph)

    # Cancel task that was never started
    await executor.cancel(request_context, mock_event_queue)

    # Should handle gracefully
    assert mock_event_queue.enqueue_event.called


@pytest.mark.asyncio
async def test_execution_completes_before_cancel(
    executor_module, mock_graph, mock_event_queue, request_context
):
    """Test cancellation attempt after task completes normally."""
    LangGraphAgentExecutor = executor_module["LangGraphAgentExecutor"]
    LangGraphAgentExecutorConfig = executor_module["LangGraphAgentExecutorConfig"]

    # Mock fast completion
    mock_graph.ainvoke.return_value = {"messages": []}

    config = LangGraphAgentExecutorConfig(enable_streaming=False)
    executor = LangGraphAgentExecutor(graph=mock_graph, config=config)

    # Execute and let it complete
    await executor.execute(request_context, mock_event_queue)

    # Try to cancel after completion
    await executor.cancel(request_context, mock_event_queue)

    # Should handle gracefully (task already done)
    assert request_context.task_id not in executor._cancellation_events


@pytest.mark.asyncio
async def test_exception_during_cancellation(
    executor_module, mock_graph, mock_event_queue, request_context
):
    """Test handling of exceptions during cancellation."""
    LangGraphAgentExecutor = executor_module["LangGraphAgentExecutor"]

    executor = LangGraphAgentExecutor(graph=mock_graph)

    # Set up a task
    executor._cancellation_events[request_context.task_id] = asyncio.Event()
    executor._active_tasks[request_context.task_id] = asyncio.create_task(
        asyncio.sleep(10)
    )

    # Mock event queue to raise exception
    mock_event_queue.enqueue_event.side_effect = Exception("Queue error")

    # Cancel should handle exception gracefully
    await executor.cancel(request_context, mock_event_queue)

    # Cleanup should still happen
    assert request_context.task_id not in executor._cancellation_events
    assert request_context.task_id not in executor._active_tasks


@pytest.mark.asyncio
async def test_cancellation_with_multiple_tasks(
    executor_module, mock_graph, mock_event_queue
):
    """Test that cancellation only affects the target task."""
    LangGraphAgentExecutor = executor_module["LangGraphAgentExecutor"]

    executor = LangGraphAgentExecutor(graph=mock_graph)

    # Create multiple task contexts
    context1 = RequestContext(
        task_id="task-1",
        context_id="ctx-1",
        message=Message(
            message_id=str(uuid.uuid4()),
            role=Role.user,
            parts=[Part(root=TextPart(text="Task 1"))],
        ),
    )
    context2 = RequestContext(
        task_id="task-2",
        context_id="ctx-2",
        message=Message(
            message_id=str(uuid.uuid4()),
            role=Role.user,
            parts=[Part(root=TextPart(text="Task 2"))],
        ),
    )

    # Set up cancellation events for both
    executor._cancellation_events["task-1"] = asyncio.Event()
    executor._cancellation_events["task-2"] = asyncio.Event()

    # Cancel only task-1
    await executor.cancel(context1, mock_event_queue)

    # Verify task-1 is cancelled
    assert "task-1" not in executor._cancellation_events

    # Verify task-2 is unaffected
    assert "task-2" in executor._cancellation_events
    assert not executor._cancellation_events["task-2"].is_set()
