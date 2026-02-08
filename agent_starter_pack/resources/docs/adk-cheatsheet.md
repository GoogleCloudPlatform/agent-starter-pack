# ADK Cheatsheet

---

## 1. Core Concepts & Project Structure

### Essential Primitives

*   **`Agent`**: The core intelligent unit. Can be `LlmAgent` (LLM-driven) or `BaseAgent` (custom/workflow).
*   **`Tool`**: Callable function providing external capabilities (`FunctionTool`, `AgentTool`, etc.).
*   **`Session`**: A stateful conversation thread with history (`events`) and short-term memory (`state`).
*   **`State`**: Key-value dictionary within a `Session` for transient conversation data.
*   **`Runner`**: The execution engine; orchestrates agent activity and event flow.
*   **`Event`**: Atomic unit of communication; carries content and side-effect `actions`.

### Standard Project Layout

```
your_project_root/
├── my_agent/
│   ├── __init__.py
│   ├── agent.py          # Contains root_agent definition
│   ├── tools.py           # Custom tool functions
│   └── .env               # Environment variables
├── requirements.txt
└── tests/
```

---

## 2. Agent Definitions (`LlmAgent`)

### Basic Setup

```python
from google.adk.agents import Agent

def get_weather(city: str) -> dict:
    """Returns weather for a city."""
    return {"status": "success", "weather": "sunny", "temp": 72}

my_agent = Agent(
    name="weather_agent",
    model="gemini-2.0-flash",
    instruction="You help users check the weather. Use the get_weather tool.",
    description="Provides weather information.",  # Important for multi-agent delegation
    tools=[get_weather]
)
```

### Key Configuration Options

```python
from google.genai import types as genai_types
from google.adk.agents import Agent

agent = Agent(
    name="my_agent",
    model="gemini-2.0-flash",
    instruction="Your instructions here. Use {state_key} for dynamic injection.",
    description="Description for delegation.",

    # LLM generation parameters
    generate_content_config=genai_types.GenerateContentConfig(
        temperature=0.2,
        max_output_tokens=1024,
    ),

    # Save final output to state
    output_key="agent_response",

    # Control history sent to LLM
    include_contents='default',  # 'default' or 'none'

    # Delegation control
    disallow_transfer_to_parent=False,
    disallow_transfer_to_peers=False,

    # Sub-agents for delegation
    sub_agents=[specialist_agent],

    # Tools
    tools=[my_tool],

    # Callbacks
    before_agent_callback=my_callback,
    after_agent_callback=my_callback,
    before_model_callback=my_callback,
    after_model_callback=my_callback,
    before_tool_callback=my_callback,
    after_tool_callback=my_callback,
)
```

### Structured Output with Pydantic

> **Warning**: Using `output_schema` disables tool calling and delegation.

```python
from pydantic import BaseModel, Field
from typing import Literal

class Evaluation(BaseModel):
    grade: Literal["pass", "fail"] = Field(description="The evaluation result.")
    comment: str = Field(description="Explanation of the grade.")

evaluator = Agent(
    name="evaluator",
    model="gemini-2.0-flash",
    instruction="Evaluate the input and provide structured feedback.",
    output_schema=Evaluation,
    output_key="evaluation_result",
)
```

### Instruction Best Practices

```python
# Use dynamic state injection
instruction = """
You are a {role} assistant.
User preferences: {user_preferences}

Rules:
- Always use tools when available
- Never make up information
"""

# Constrain tool usage
instruction = """
You help with research.
ONLY use google_search when the user explicitly asks for current information.
For general knowledge, answer directly.
"""
```

---

## 3. Orchestration with Workflow Agents

Workflow agents provide deterministic control flow without LLM orchestration.

### SequentialAgent

Executes sub-agents in order. State changes propagate to subsequent agents.

```python
from google.adk.agents import SequentialAgent, Agent

summarizer = Agent(
    name="summarizer",
    model="gemini-2.0-flash",
    instruction="Summarize the input.",
    output_key="summary"
)

question_gen = Agent(
    name="question_generator",
    model="gemini-2.0-flash",
    instruction="Generate questions based on: {summary}"
)

pipeline = SequentialAgent(
    name="pipeline",
    sub_agents=[summarizer, question_gen],
)
```

### ParallelAgent

Executes sub-agents concurrently. Use distinct `output_key`s to avoid race conditions.

```python
from google.adk.agents import ParallelAgent, SequentialAgent, Agent

fetch_a = Agent(name="fetch_a", ..., output_key="data_a")
fetch_b = Agent(name="fetch_b", ..., output_key="data_b")

merger = Agent(
    name="merger",
    instruction="Combine data_a: {data_a} and data_b: {data_b}"
)

pipeline = SequentialAgent(
    name="full_pipeline",
    sub_agents=[
        ParallelAgent(name="fetchers", sub_agents=[fetch_a, fetch_b]),
        merger
    ]
)
```

### LoopAgent

Repeats sub-agents until `max_iterations` or an event with `escalate=True`.

```python
from google.adk.agents import LoopAgent

refinement_loop = LoopAgent(
    name="refinement_loop",
    sub_agents=[evaluator, refiner, escalation_checker],
    max_iterations=5,
)
```

---

## 4. Multi-Agent Systems & Communication

### Communication Methods

1.  **Shared State**: Agents read/write `session.state`. Use `output_key` for convenience.

2.  **LLM Delegation**: Agent transfers control to a sub-agent based on reasoning.
    ```python
    coordinator = Agent(
        name="coordinator",
        instruction="Route to sales_agent for sales, support_agent for help.",
        sub_agents=[sales_agent, support_agent],
    )
    ```

3.  **AgentTool**: Invoke another agent as a tool (parent stays in control).
    ```python
    from google.adk.tools import AgentTool

    root = Agent(
        name="root",
        tools=[AgentTool(specialist_agent)],
    )
    ```

### Delegation vs AgentTool

```python
# Delegation: transfers control, sub-agent talks to user
root = Agent(name="root", sub_agents=[specialist])

# AgentTool: parent calls specialist, gets result, summarizes for user
root = Agent(name="root", tools=[AgentTool(specialist)])
```

---

## 5. Building Custom Agents (`BaseAgent`)

For custom orchestration logic beyond workflow agents.

```python
from google.adk.agents import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event, EventActions
from typing import AsyncGenerator

class ConditionalRouter(BaseAgent):
    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        # Read state
        user_type = ctx.session.state.get("user_type", "regular")

        # Custom routing logic
        if user_type == "premium":
            agent = self.premium_agent
        else:
            agent = self.regular_agent

        # Run selected agent
        async for event in agent.run_async(ctx):
            yield event

class EscalationChecker(BaseAgent):
    """Stops a LoopAgent when condition is met."""
    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        result = ctx.session.state.get("evaluation")
        if result and result.get("grade") == "pass":
            yield Event(author=self.name, actions=EventActions(escalate=True))
        else:
            yield Event(author=self.name)
```

---

## 6. Models Configuration

### Google Gemini (Default)

```python
# AI Studio (dev)
# Set: GOOGLE_API_KEY, GOOGLE_GENAI_USE_VERTEXAI=False

# Vertex AI (prod)
# Set: GOOGLE_CLOUD_PROJECT, GOOGLE_CLOUD_LOCATION, GOOGLE_GENAI_USE_VERTEXAI=True

agent = Agent(model="gemini-2.0-flash", ...)
```

### Other Models via LiteLLM

```python
from google.adk.models.lite_llm import LiteLlm

agent = Agent(model=LiteLlm(model="openai/gpt-4o"), ...)
agent = Agent(model=LiteLlm(model="anthropic/claude-3-haiku-20240307"), ...)
agent = Agent(model=LiteLlm(model="ollama_chat/llama3:instruct"), ...)
```

---

## 7. Tools: The Agent's Capabilities

### Function Tool Basics

```python
from google.adk.tools import ToolContext

def search_database(
    query: str,
    limit: int,
    tool_context: ToolContext  # Optional, for state access
) -> dict:
    """Searches the database for records matching the query.

    Args:
        query: The search query string.
        limit: Maximum number of results to return.

    Returns:
        dict with 'status' and 'results' keys.
    """
    # Access state if needed
    user_id = tool_context.state.get("user_id")

    # Tool logic here
    results = db.search(query, limit=limit, user=user_id)

    return {"status": "success", "results": results}
```

**Tool Rules:**
- Use clear docstrings (sent to LLM)
- Type hints required, NO default values
- Return a dict (JSON-serializable)
- Don't mention `tool_context` in docstring

### ToolContext Capabilities

```python
def my_tool(query: str, tool_context: ToolContext) -> dict:
    # Read/write state
    tool_context.state["key"] = "value"

    # Trigger escalation (stops LoopAgent)
    tool_context.actions.escalate = True

    # Artifacts
    tool_context.save_artifact("file.txt", part)
    data = tool_context.load_artifact("file.txt")

    # Memory search
    results = tool_context.search_memory("query")

    return {"status": "success"}
```

### Built-in Tools

```python
from google.adk.tools import google_search
from google.adk.tools.load_web_page import load_web_page
from google.adk.code_executors import BuiltInCodeExecutor

# Google Search grounding
agent = Agent(tools=[google_search], ...)

# Web page loading
agent = Agent(tools=[load_web_page], ...)

# Code execution
agent = Agent(code_executor=BuiltInCodeExecutor(), ...)
```

### Tool Confirmation

```python
from google.adk.tools import FunctionTool

# Simple confirmation
sensitive_tool = FunctionTool(delete_record, require_confirmation=True)

# Conditional confirmation
def needs_approval(amount: float, **kwargs) -> bool:
    return amount > 1000

transfer_tool = FunctionTool(transfer_money, require_confirmation=needs_approval)
```

---

## 8. Context, State, and Memory

### State Prefixes

```python
# Session-specific (default)
state["booking_step"] = 2

# User-persistent (across sessions)
state["user:preferred_language"] = "en"

# App-wide (all users)
state["app:total_queries"] = 1000

# Temporary (current invocation only)
state["temp:intermediate_result"] = data
```

### Session Service Options

```python
from google.adk.sessions import InMemorySessionService
# For dev: InMemorySessionService()
# For prod: VertexAiSessionService(), DatabaseSessionService()
```

### Memory (Long-term Knowledge)

```python
from google.adk.memory import InMemoryMemoryService

memory_service = InMemoryMemoryService()
# Add session to memory after conversation
await memory_service.add_session_to_memory(session)
# Search later
results = await memory_service.search_memory(app_name, user_id, "query")
```

---

## 9. Callbacks

### Callback Types

```python
from google.adk.agents.callback_context import CallbackContext
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.genai import types as genai_types

# Agent lifecycle
async def before_agent_callback(ctx: CallbackContext) -> None:
    ctx.state["started"] = True

async def after_agent_callback(ctx: CallbackContext) -> genai_types.Content | None:
    # Return None to continue, or Content to override
    return None

# Model interaction
async def before_model_callback(ctx: CallbackContext, request: LlmRequest) -> LlmResponse | None:
    # Return None to continue, or LlmResponse to skip model call
    return None

async def after_model_callback(ctx: CallbackContext, response: LlmResponse) -> LlmResponse | None:
    # Return None to continue, or modified LlmResponse
    return None

# Tool execution
async def before_tool_callback(ctx: CallbackContext, tool_name: str, args: dict) -> dict | None:
    # Return None to continue, or dict to skip tool and use as result
    return None

async def after_tool_callback(ctx: CallbackContext, tool_name: str, result: dict) -> dict | None:
    # Return None to continue, or modified dict
    return None
```

### Common Patterns

```python
# Initialize state before agent runs
async def init_state(ctx: CallbackContext) -> None:
    if "preferences" not in ctx.state:
        ctx.state["preferences"] = {}

agent = Agent(before_agent_callback=init_state, ...)

# Collect data after agent runs
async def collect_sources(ctx: CallbackContext) -> None:
    session = ctx._invocation_context.session
    sources = []
    for event in session.events:
        if event.grounding_metadata:
            sources.extend(event.grounding_metadata.grounding_chunks)
    ctx.state["sources"] = sources

agent = Agent(after_agent_callback=collect_sources, ...)
```

---

## Quick Reference

### Running Agents Programmatically

```python
import asyncio
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types as genai_types

async def run_agent(agent, query: str):
    session_service = InMemorySessionService()
    await session_service.create_session(
        app_name="app", user_id="user", session_id="session"
    )
    runner = Runner(agent=agent, app_name="app", session_service=session_service)

    async for event in runner.run_async(
        user_id="user",
        session_id="session",
        new_message=genai_types.Content(
            role="user",
            parts=[genai_types.Part.from_text(text=query)]
        ),
    ):
        if event.is_final_response():
            return event.content.parts[0].text

result = asyncio.run(run_agent(my_agent, "Hello!"))
```

### CLI Commands

```bash
adk web /path/to/project    # Web UI
adk run /path/to/agent      # CLI chat
adk api_server /path/to     # FastAPI server
adk eval agent/ evalset.json  # Run evaluations
```

### Further Reading

- [ADK Documentation](https://google.github.io/adk-docs/llms.txt)
- [ADK Samples](https://github.com/google/adk-samples)
