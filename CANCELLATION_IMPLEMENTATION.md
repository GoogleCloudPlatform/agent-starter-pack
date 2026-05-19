# A2A Agent Executor Cancellation Implementation

## Overview

This document describes the cancellation logic implementation for the `LangGraphAgentExecutor` in the agent-starter-pack base template.

## Implementation Summary

The cancellation implementation provides graceful task cancellation for both streaming and non-streaming execution modes, with proper resource cleanup and event publishing.

### Key Components

#### 1. Cancellation Tracking State

Two dictionaries track cancellation state per task:

```python
self._cancellation_events: dict[str, asyncio.Event] = {}
self._active_tasks: dict[str, asyncio.Task] = {}
```

- `_cancellation_events`: Maps task_id to asyncio.Event for signaling cancellation
- `_active_tasks`: Maps task_id to the active asyncio Task for direct cancellation

#### 2. Cancel Method

**File**: `a2a_agent_executor.py` (lines 74-147)

The `cancel()` method implements graceful cancellation:

1. **Validates context**: Checks for task_id presence
2. **Sets cancellation event**: Signals the running task to stop
3. **Cancels active task**: Calls `.cancel()` on the asyncio task
4. **Waits gracefully**: Uses `asyncio.wait_for()` with 2-second timeout
5. **Publishes event**: Sends `TaskState.cancelled` event to queue
6. **Cleans up**: Removes tracking dictionaries entries

**Error Handling**:
- Logs warnings if task_id is missing
- Catches and logs exceptions during cancellation
- Always cleans up resources in finally block

#### 3. Execution Flow with Cancellation

**File**: `a2a_agent_executor.py` (lines 171-276)

The `execute()` method was modified to:

1. **Initialize cancellation event**: Creates event at start
2. **Track execution task**: Stores task reference for cancellation
3. **Handle CancelledError**: Catches and publishes cancellation status
4. **Clean up resources**: Always calls `_cleanup_task_resources()` in finally

#### 4. Cancellation Checkpoints

**File**: `a2a_agent_executor.py` (lines 278-449)

The `_handle_request()` method checks for cancellation at critical points:

**Streaming Mode**:
- Before starting execution (line 306)
- On each streaming chunk (line 337)
- Before publishing final results (line 393)

**Non-Streaming Mode**:
- Before starting execution (line 306)
- Before graph invocation (line 377)
- After graph invocation (line 384)
- Before publishing final results (line 393)

Each checkpoint calls `_is_cancelled()` and raises `asyncio.CancelledError` if cancelled.

#### 5. Helper Methods

**`_is_cancelled(task_id: str) -> bool`** (lines 159-169)
- Checks if cancellation event is set for a task
- Returns False if event doesn't exist (task not started)

**`_cleanup_task_resources(task_id: str) -> None`** (lines 149-157)
- Removes entries from both tracking dictionaries
- Logs cleanup action for debugging

## Cancellation Flow Diagram

```
User Calls cancel()
    ↓
Set cancellation_event.set()
    ↓
Cancel active_task.cancel()
    ↓
Wait 2 seconds for graceful shutdown
    ↓
Running task checks _is_cancelled()
    ↓
Raises asyncio.CancelledError
    ↓
execute() catches CancelledError
    ↓
Publishes TaskState.cancelled event
    ↓
Cleanup resources in finally block
```

## Testing

Comprehensive test suite in `tests/unit/test_a2a_agent_executor.py`:

### Test Coverage

1. **test_cancellation_before_execution**: Cancel immediately after start
2. **test_cancellation_during_streaming**: Cancel mid-stream processing
3. **test_cancellation_during_non_streaming**: Cancel during long operation
4. **test_is_cancelled_flag**: Verify cancellation flag behavior
5. **test_cleanup_task_resources**: Verify resource cleanup
6. **test_cancel_without_task_id**: Handle missing task_id gracefully
7. **test_cancel_nonexistent_task**: Cancel task that never started
8. **test_execution_completes_before_cancel**: Handle race condition
9. **test_exception_during_cancellation**: Handle errors during cancel
10. **test_cancellation_with_multiple_tasks**: Verify isolation between tasks

### Running Tests

```bash
cd agent-starter-pack
python3 -m pytest agent_starter_pack/base_template/tests/unit/test_a2a_agent_executor.py -v
```

Note: Tests require the `a2a` package and dependencies to be installed.

## Design Decisions

### 1. Event-Based Signaling

Used `asyncio.Event` instead of a simple boolean flag because:
- Thread-safe and async-safe
- Can be awaited if needed
- Standard asyncio pattern

### 2. Dual Tracking (Event + Task)

Maintained both `_cancellation_events` and `_active_tasks` because:
- Event: For cooperative cancellation (checking _is_cancelled)
- Task: For forced cancellation (task.cancel())
- Provides both graceful and forceful cancellation options

### 3. Cancellation Checkpoints

Placed checkpoints at:
- **Before operations**: Avoid starting unnecessary work
- **During streaming**: Allow responsive cancellation
- **After operations**: Check before committing results

### 4. Graceful Timeout

2-second timeout for graceful cancellation:
- Long enough for cleanup operations
- Short enough to be responsive
- Uses `asyncio.shield()` to prevent premature timeout

### 5. Always Cleanup

Resources cleaned up in finally block:
- Ensures no memory leaks
- Prevents task_id collision on retry
- Maintains clean state

## Error Scenarios

### Scenario 1: Cancel Before Start
- Cancellation event set before task starts
- First checkpoint detects cancellation
- Task never executes graph operations

### Scenario 2: Cancel During Streaming
- Task is yielding streaming chunks
- Next iteration checks cancellation
- Raises CancelledError immediately

### Scenario 3: Cancel During Long Operation
- Task is in `graph.ainvoke()` call
- Task cancellation propagates to graph
- May take time but eventually cancels

### Scenario 4: Event Queue Failure
- Cancellation event publish fails
- Error logged but doesn't prevent cleanup
- Resources still cleaned up properly

## Performance Considerations

### Memory
- Two dictionaries scale with concurrent tasks
- Entries removed immediately after completion
- No memory leaks from uncleaned tasks

### CPU
- Cancellation checks are O(1) dictionary lookups
- Minimal overhead on hot path
- Logging only at INFO level for cancellation

### Latency
- Streaming mode: Responsive (checked each chunk)
- Non-streaming mode: Checked at strategic points
- 2-second max delay for forceful cancellation

## Future Enhancements

Potential improvements:

1. **Configurable timeout**: Allow custom cancellation timeout
2. **Cancellation callbacks**: Hook for custom cleanup logic
3. **Partial results**: Option to return partial results on cancel
4. **Cancellation reasons**: Track why task was cancelled
5. **Metrics**: Track cancellation rates and timing

## Related Files

- **Implementation**: `{{cookiecutter.agent_directory}}/app_utils/executor/a2a_agent_executor.py`
- **Tests**: `tests/unit/test_a2a_agent_executor.py`
- **Base Class**: `a2a.server.agent_execution.AgentExecutor`

## References

- [Python asyncio.CancelledError](https://docs.python.org/3/library/asyncio-exceptions.html#asyncio.CancelledError)
- [asyncio Task Cancellation](https://docs.python.org/3/library/asyncio-task.html#task-cancellation)
- [asyncio.Event](https://docs.python.org/3/library/asyncio-sync.html#asyncio.Event)
