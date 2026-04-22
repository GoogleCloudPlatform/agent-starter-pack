# Cancellation Quick Reference

## For Users of the Executor

### Basic Usage

```python
from app_utils.executor.a2a_agent_executor import LangGraphAgentExecutor

# Create executor
executor = LangGraphAgentExecutor(graph=my_graph)

# Start execution
task = asyncio.create_task(executor.execute(context, event_queue))

# Cancel anytime
await executor.cancel(context, event_queue)

# Task will raise CancelledError
try:
    await task
except asyncio.CancelledError:
    print("Task was cancelled")
```

### What Happens on Cancel?

1. Task stops processing immediately (at next checkpoint)
2. `TaskState.cancelled` event published to queue
3. All resources cleaned up automatically
4. `CancelledError` raised to caller

### Cancellation Response Time

- **Streaming mode**: < 100ms (checked each chunk)
- **Non-streaming mode**: Depends on graph operation
- **Force timeout**: 2 seconds maximum

## For Developers Extending the Executor

### Adding Cancellation Checkpoints

If you add long-running operations, add checkpoints:

```python
# Before your operation
if self._is_cancelled(task_id):
    raise asyncio.CancelledError()

# Your long-running operation here

# After your operation
if self._is_cancelled(task_id):
    raise asyncio.CancelledError()
```

### Checkpoint Guidelines

Add checkpoints:
- ✅ Before expensive operations
- ✅ Inside loops
- ✅ After I/O operations
- ✅ Before publishing results

Don't add checkpoints:
- ❌ In hot paths (called thousands of times)
- ❌ In finally blocks
- ❌ In error handlers

### Custom Cleanup

If you need custom cleanup logic:

```python
try:
    # Your operation
    pass
except asyncio.CancelledError:
    # Your cleanup code
    cleanup_my_resources()
    raise  # Always re-raise
```

## Debugging Cancellation Issues

### Enable Debug Logging

```python
import logging
logging.getLogger('a2a_agent_executor').setLevel(logging.DEBUG)
```

### Common Issues

**Issue**: Task doesn't cancel
- Check: Are you checking `_is_cancelled()`?
- Check: Are you re-raising `CancelledError`?

**Issue**: Resources not cleaned up
- Check: Is cleanup in a finally block?
- Check: Are you swallowing `CancelledError`?

**Issue**: Cancel takes too long
- Check: Add more checkpoints in long operations
- Check: Graph operations may be blocking

### Log Messages to Look For

```
INFO: Cancelling task: task-123
DEBUG: Cancellation event set for task: task-123
INFO: Task task-123 cancelled during streaming, cleaning up
INFO: Task execution cancelled for task_id: task-123
DEBUG: Cleaned up resources for task: task-123
```

## Testing Cancellation

### Basic Test Pattern

```python
@pytest.mark.asyncio
async def test_my_cancellation():
    executor = LangGraphAgentExecutor(graph=mock_graph)

    # Start task
    task = asyncio.create_task(executor.execute(context, queue))

    # Let it run a bit
    await asyncio.sleep(0.1)

    # Cancel
    await executor.cancel(context, queue)

    # Verify
    with pytest.raises(asyncio.CancelledError):
        await task
```

### Mock Slow Operations

```python
async def slow_operation():
    await asyncio.sleep(10)  # Simulate slow work
    return result

mock_graph.ainvoke = AsyncMock(side_effect=slow_operation)
```

## API Reference

### Methods

#### `cancel(context, event_queue)`
Cancel a running task.

**Parameters**:
- `context`: RequestContext with task_id
- `event_queue`: EventQueue for status updates

**Returns**: None

**Raises**: None (logs errors)

#### `_is_cancelled(task_id)`
Check if task is cancelled.

**Parameters**:
- `task_id`: str - Task identifier

**Returns**: bool - True if cancelled

#### `_cleanup_task_resources(task_id)`
Clean up tracking dictionaries.

**Parameters**:
- `task_id`: str - Task identifier

**Returns**: None

### State

#### `_cancellation_events: dict[str, asyncio.Event]`
Maps task_id to cancellation event.

#### `_active_tasks: dict[str, asyncio.Task]`
Maps task_id to execution task.

## Performance Tips

1. **Checkpoint frequency**: Balance responsiveness vs overhead
2. **Cleanup complexity**: Keep cleanup logic simple and fast
3. **Logging verbosity**: Use DEBUG for detailed logs
4. **Event publishing**: Don't block on event queue operations

## Best Practices

### Do's
- ✅ Always re-raise `CancelledError`
- ✅ Clean up in finally blocks
- ✅ Check cancellation before expensive ops
- ✅ Log cancellation events
- ✅ Test cancellation scenarios

### Don'ts
- ❌ Catch `CancelledError` without re-raising
- ❌ Forget to clean up resources
- ❌ Block cancellation indefinitely
- ❌ Assume cancellation is instant
- ❌ Leave tasks in incomplete state

## Examples

### Example 1: Cancel After Timeout

```python
async def execute_with_timeout(executor, context, queue, timeout=30):
    task = asyncio.create_task(executor.execute(context, queue))

    try:
        await asyncio.wait_for(task, timeout=timeout)
    except asyncio.TimeoutError:
        await executor.cancel(context, queue)
        raise TimeoutError(f"Task timed out after {timeout}s")
```

### Example 2: Cancel on External Event

```python
async def execute_until_signal(executor, context, queue, stop_event):
    task = asyncio.create_task(executor.execute(context, queue))
    signal_task = asyncio.create_task(stop_event.wait())

    done, pending = await asyncio.wait(
        [task, signal_task],
        return_when=asyncio.FIRST_COMPLETED
    )

    if signal_task in done:
        await executor.cancel(context, queue)
        task.cancel()
```

### Example 3: Cancel Multiple Tasks

```python
async def cancel_all(executor, contexts, queue):
    cancel_tasks = [
        executor.cancel(ctx, queue)
        for ctx in contexts
    ]
    await asyncio.gather(*cancel_tasks, return_exceptions=True)
```

## Troubleshooting

### Task Won't Cancel
```python
# Add debug logging
logger.debug("Checkpoint reached, cancelled=%s", self._is_cancelled(task_id))
```

### Memory Leak
```python
# Check cleanup is called
print(f"Active tasks: {len(executor._active_tasks)}")
print(f"Cancellation events: {len(executor._cancellation_events)}")
```

### Race Conditions
```python
# Use locks if needed
async with self._lock:
    if not self._is_cancelled(task_id):
        # Critical operation
        pass
```

## See Also

- `CANCELLATION_IMPLEMENTATION.md` - Detailed technical docs
- `CANCELLATION_SUMMARY.md` - High-level overview
- `test_a2a_agent_executor.py` - Test examples
