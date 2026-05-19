# Cancellation Architecture

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                   LangGraphAgentExecutor                         │
│                                                                  │
│  State:                                                          │
│  ┌────────────────────────────────────────────────────────┐   │
│  │ _cancellation_events: dict[str, asyncio.Event]         │   │
│  │   - Maps task_id → cancellation signal                 │   │
│  │   - Set when cancel() is called                        │   │
│  │                                                         │   │
│  │ _active_tasks: dict[str, asyncio.Task]                 │   │
│  │   - Maps task_id → execution task                      │   │
│  │   - Used for forced cancellation                       │   │
│  └────────────────────────────────────────────────────────┘   │
│                                                                  │
│  Methods:                                                        │
│  ┌────────────────────────────────────────────────────────┐   │
│  │ execute(context, event_queue)                          │   │
│  │   1. Initialize cancellation event                     │   │
│  │   2. Create and track execution task                   │   │
│  │   3. Await task (or catch CancelledError)              │   │
│  │   4. Cleanup resources in finally                      │   │
│  └────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌────────────────────────────────────────────────────────┐   │
│  │ cancel(context, event_queue)                           │   │
│  │   1. Set cancellation event                            │   │
│  │   2. Cancel active task                                │   │
│  │   3. Wait for graceful shutdown (2s timeout)           │   │
│  │   4. Publish cancellation event                        │   │
│  │   5. Cleanup resources                                 │   │
│  └────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌────────────────────────────────────────────────────────┐   │
│  │ _handle_request(context, event_queue)                  │   │
│  │   • Checkpoints at critical points                     │   │
│  │   • Raises CancelledError when cancelled               │   │
│  │   • Handles streaming and non-streaming modes          │   │
│  └────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌────────────────────────────────────────────────────────┐   │
│  │ _is_cancelled(task_id) → bool                          │   │
│  │   • O(1) check of cancellation event                   │   │
│  └────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌────────────────────────────────────────────────────────┐   │
│  │ _cleanup_task_resources(task_id)                       │   │
│  │   • Remove from both tracking dicts                    │   │
│  └────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

## Execution Flow

### Normal Execution

```
                    execute()
                       │
                       ├─ Initialize cancellation_event
                       ├─ Create execution_task
                       ├─ Track in active_tasks
                       │
                       ├─► _handle_request()
                       │      │
                       │      ├─ Checkpoint: _is_cancelled()
                       │      │  └─ No → Continue
                       │      │
                       │      ├─ graph.astream() or ainvoke()
                       │      │  │
                       │      │  ├─ For each chunk (streaming):
                       │      │  │  ├─ Checkpoint: _is_cancelled()
                       │      │  │  └─ No → Process chunk
                       │      │  │
                       │      │  └─ Result produced
                       │      │
                       │      ├─ Checkpoint: _is_cancelled()
                       │      │  └─ No → Continue
                       │      │
                       │      └─ Publish results
                       │
                       ├─ Task completes successfully
                       │
                       └─ finally: cleanup_task_resources()
```

### Cancelled Execution

```
                    execute()
                       │
                       ├─ Initialize cancellation_event
                       ├─ Create execution_task
                       ├─ Track in active_tasks
                       │
    cancel() called ──┼─► Set cancellation_event
         │             │   Cancel active_task
         │             │
         │             ├─► _handle_request()
         │             │      │
         │             │      ├─ Checkpoint: _is_cancelled()
         │             │      │  └─ Yes! → raise CancelledError
         │             │      │
         │             │      └─ (or during streaming)
         │             │         ├─ Checkpoint in loop
         │             │         └─ Yes! → raise CancelledError
         │             │
         │             ├─ Catch CancelledError
         │             ├─ Publish cancellation event
         │             ├─ Re-raise CancelledError
         │             │
         └─────────────┴─ finally: cleanup_task_resources()
```

## State Transitions

```
Task Lifecycle States:

  ┌─────────────┐
  │  Not Started │
  └──────┬───────┘
         │ execute() called
         ▼
  ┌─────────────┐     cancel() called (early)
  │ Initialized  ├────────────────────────────┐
  └──────┬───────┘                            │
         │ start _handle_request()            │
         ▼                                    │
  ┌─────────────┐     cancel() called (mid)  │
  │   Working    ├────────────────────────────┤
  └──────┬───────┘                            │
         │ complete successfully             │
         ▼                                    ▼
  ┌─────────────┐                     ┌─────────────┐
  │  Completed   │                     │  Cancelled  │
  └─────────────┘                     └─────────────┘

All states eventually reach:
  ┌─────────────┐
  │  Cleaned Up  │  (resources removed from dicts)
  └─────────────┘
```

## Cancellation Event States

```
asyncio.Event Lifecycle:

  ┌──────────────────┐
  │ Event Created    │  event = asyncio.Event()
  │ (not set)        │
  └────────┬─────────┘
           │
           │ Normal execution path
           ├─────────────► event.is_set() → False
           │                   │
           │                   ├─ Continue processing
           │                   └─ Eventually complete
           │
           │ Cancellation path
           ├─────────────► cancel() called
           │                   │
           │                   ▼
           │              event.set()
           │                   │
           │                   ▼
           └─────────────► event.is_set() → True
                               │
                               ├─ Raise CancelledError
                               └─ Cleanup resources
```

## Checkpoint Strategy

### Streaming Mode

```
graph.astream() loop:
  ┌────────────────────────────┐
  │ Start streaming            │
  └─────────┬──────────────────┘
            │
            ▼
  ┌────────────────────────────┐
  │ Checkpoint 1:               │  ◄─── Before loop
  │ Check _is_cancelled()       │
  └─────────┬──────────────────┘
            │
            ▼
  ┌────────────────────────────┐
  │ async for chunk:            │
  │   ┌──────────────────────┐ │
  │   │ Checkpoint 2:         │ │  ◄─── Each iteration
  │   │ Check _is_cancelled() │ │
  │   └───────┬──────────────┘ │
  │           │                 │
  │           ├─ Process chunk  │
  │           └─ Publish event  │
  └─────────┬──────────────────┘
            │
            ▼
  ┌────────────────────────────┐
  │ Checkpoint 3:               │  ◄─── Before publishing
  │ Check _is_cancelled()       │
  └─────────┬──────────────────┘
            │
            ▼
  ┌────────────────────────────┐
  │ Publish final results       │
  └────────────────────────────┘
```

### Non-Streaming Mode

```
graph.ainvoke() flow:
  ┌────────────────────────────┐
  │ Checkpoint 1:               │  ◄─── Before invocation
  │ Check _is_cancelled()       │
  └─────────┬──────────────────┘
            │
            ▼
  ┌────────────────────────────┐
  │ await graph.ainvoke()       │  (may take time)
  └─────────┬──────────────────┘
            │
            ▼
  ┌────────────────────────────┐
  │ Checkpoint 2:               │  ◄─── After invocation
  │ Check _is_cancelled()       │
  └─────────┬──────────────────┘
            │
            ▼
  ┌────────────────────────────┐
  │ Process messages            │
  └─────────┬──────────────────┘
            │
            ▼
  ┌────────────────────────────┐
  │ Checkpoint 3:               │  ◄─── Before publishing
  │ Check _is_cancelled()       │
  └─────────┬──────────────────┘
            │
            ▼
  ┌────────────────────────────┐
  │ Publish final results       │
  └────────────────────────────┘
```

## Concurrency Model

### Multiple Tasks

```
Executor Instance:
  ┌────────────────────────────────────────────────────┐
  │ _cancellation_events: {                            │
  │   "task-1": Event(set=False),                      │
  │   "task-2": Event(set=True),   ◄─── Cancelled     │
  │   "task-3": Event(set=False)                       │
  │ }                                                   │
  │                                                     │
  │ _active_tasks: {                                   │
  │   "task-1": Task(<executing>),                     │
  │   "task-2": Task(<cancelled>), ◄─── Cleaned up    │
  │   "task-3": Task(<pending>)                        │
  │ }                                                   │
  └────────────────────────────────────────────────────┘

Properties:
  • Each task has independent cancellation state
  • Cancelling task-2 doesn't affect task-1 or task-3
  • No locks needed (dict operations are atomic)
  • O(1) lookup performance per task
```

## Error Handling Layers

```
Layer 1: cancel() method
  │
  ├─ Try: Set event, cancel task, publish
  ├─ Catch: Log errors during cancellation
  └─ Finally: Always cleanup resources
      │
      └─► _cleanup_task_resources()

Layer 2: execute() method
  │
  ├─ Try: Run execution task
  ├─ Catch CancelledError: Publish cancellation
  ├─ Catch Exception: Publish failure
  └─ Finally: Always cleanup resources
      │
      └─► _cleanup_task_resources()

Layer 3: _handle_request() method
  │
  ├─ Try: Execute graph operations
  ├─ Catch CancelledError: Re-raise (don't suppress)
  └─ Catch Exception: Set failed state, re-raise

Result: Multiple layers ensure cleanup happens
```

## Memory Management

```
Task Creation:
  task_id = "abc-123"
  │
  ├─► _cancellation_events["abc-123"] = Event()  [8 bytes overhead]
  └─► _active_tasks["abc-123"] = Task(...)       [~ 1KB overhead]
                                                  ─────────────────
                                                  Total: ~1KB per task

Task Completion:
  │
  └─► _cleanup_task_resources("abc-123")
      │
      ├─► del _cancellation_events["abc-123"]
      └─► del _active_tasks["abc-123"]
          │
          └─► GC collects memory

Memory usage scales linearly with concurrent tasks:
  • 10 tasks  = ~10KB
  • 100 tasks = ~100KB
  • 1000 tasks = ~1MB
```

## Timing Characteristics

```
Operation Latencies:

_is_cancelled(task_id):
  Dictionary lookup           < 1 µs

cancel() method:
  Set event                   < 1 µs
  Cancel task                 < 10 µs
  Wait for shutdown (max)     2000 ms
  Publish event               10-100 ms (network)
  Cleanup                     < 1 µs
                              ─────────────
  Total (typical):            10-100 ms
  Total (worst case):         2100 ms

Checkpoint overhead:
  Per check                   < 1 µs
  Per 1000 checks            < 1 ms

Cancellation propagation:
  Streaming mode              Next chunk (< 100 ms)
  Non-streaming mode          Variable (depends on graph)
```

## Thread Safety

```
Thread Safety Analysis:

_cancellation_events: dict[str, asyncio.Event]
  • Dictionary: Not thread-safe, but single asyncio loop
  • asyncio.Event: Thread-safe and async-safe
  • Lookup: Atomic from async perspective
  • Modification: Protected by event loop serialization

_active_tasks: dict[str, asyncio.Task]
  • Dictionary: Not thread-safe, but single asyncio loop
  • asyncio.Task: Thread-safe
  • Lookup: Atomic from async perspective
  • Modification: Protected by event loop serialization

Conclusion: Safe for asyncio (single-threaded event loop)
            Not safe for multi-threaded access
```

## Design Patterns Used

1. **Event-Based Signaling**: `asyncio.Event` for cooperative cancellation
2. **Double Tracking**: Event for checking + Task for forcing
3. **Checkpoint Pattern**: Regular cancellation checks at strategic points
4. **Resource Acquisition Is Initialization (RAII)**: Cleanup in finally blocks
5. **Exception Propagation**: Re-raise CancelledError to maintain semantics
6. **Graceful Degradation**: Try cooperative first, force after timeout
