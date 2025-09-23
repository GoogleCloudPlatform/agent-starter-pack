Coding Agent guidance:
# Google Agent Development Kit (ADK) Python Cheatsheet

This document serves as a long-form, comprehensive reference for building, orchestrating, and deploying AI agents using the Python Agent Development Kit (ADK). It aims to cover every significant aspect with greater detail, more code examples, and in-depth best practices.

## Table of Contents

1.  [Core Concepts & Project Structure](#1-core-concepts--project-structure)
    *   1.1 ADK's Foundational Principles
    *   1.2 Essential Primitives
    *   1.3 Standard Project Layout
    *   1.A Build Agents without Code (Agent Config)
2.  [Agent Definitions (`LlmAgent`)](#2-agent-definitions-llmagent)
    *   2.1 Basic `LlmAgent` Setup
    *   2.2 Advanced `LlmAgent` Configuration
    *   2.3 LLM Instruction Crafting
3.  [Orchestration with Workflow Agents](#3-orchestration-with-workflow-agents)
    *   3.1 `SequentialAgent`: Linear Execution
    *   3.2 `ParallelAgent`: Concurrent Execution
    *   3.3 `LoopAgent`: Iterative Processes
4.  [Multi-Agent Systems & Communication](#4-multi-agent-systems--communication)
    *   4.1 Agent Hierarchy
    *   4.2 Inter-Agent Communication Mechanisms
    *   4.3 Common Multi-Agent Patterns
    *   4.A Distributed Communication (A2A Protocol)
5.  [Building Custom Agents (`BaseAgent`)](#5-building-custom-agents-baseagent)
    *   5.1 When to Use Custom Agents
    *   5.2 Implementing `_run_async_impl`
6.  [Models: Gemini, LiteLLM, and Vertex AI](#6-models-gemini-litellm-and-vertex-ai)
    *   6.1 Google Gemini Models (AI Studio & Vertex AI)
    *   6.2 Other Cloud & Proprietary Models via LiteLLM
    *   6.3 Open & Local Models via LiteLLM (Ollama, vLLM)
    *   6.4 Customizing LLM API Clients
7.  [Tools: The Agent's Capabilities](#7-tools-the-agents-capabilities)
    *   7.1 Defining Function Tools: Principles & Best Practices
    *   7.2 The `ToolContext` Object: Accessing Runtime Information
    *   7.3 All Tool Types & Their Usage
8.  [Context, State, and Memory Management](#8-context-state-and-memory-management)
    *   8.1 The `Session` Object & `SessionService`
    *   8.2 `State`: The Conversational Scratchpad
    *   8.3 `Memory`: Long-Term Knowledge & Retrieval
    *   8.4 `Artifacts`: Binary Data Management
9.  [Runtime, Events, and Execution Flow](#9-runtime-events-and-execution-flow)
    *   9.1 The `Runner`: The Orchestrator
    *   9.2 The Event Loop: Core Execution Flow
    *   9.3 `Event` Object: The Communication Backbone
    *   9.4 Asynchronous Programming (Python Specific)
10. [Control Flow with Callbacks](#10-control-flow-with-callbacks)
    *   10.1 Callback Mechanism: Interception & Control
    *   10.2 Types of Callbacks
    *   10.3 Callback Best Practices
    *   10.A Global Control with Plugins
11. [Authentication for Tools](#11-authentication-for-tools)
    *   11.1 Core Concepts: `AuthScheme` & `AuthCredential`
    *   11.2 Interactive OAuth/OIDC Flows
    *   11.3 Custom Tool Authentication
12. [Deployment Strategies](#12-deployment-strategies)
    *   12.1 Local Development & Testing (`adk web`, `adk run`, `adk api_server`)
    *   12.2 Vertex AI Agent Engine
    *   12.3 Cloud Run
    *   12.4 Google Kubernetes Engine (GKE)
    *   12.5 CI/CD Integration
13. [Evaluation and Safety](#13-evaluation-and-safety)
    *   13.1 Agent Evaluation (`adk eval`)
    *   13.2 Safety & Guardrails
14. [Debugging, Logging & Observability](#14-debugging-logging--observability)
15. [Streaming & Advanced I/O](#15-streaming--advanced-io)
16. [Performance Optimization](#16-performance-optimization)
17. [General Best Practices & Common Pitfalls](#17-general-best-practices--common-pitfalls)
18. [Official API & CLI References](#18-official-api--cli-references)

---

## 1. Core Concepts & Project Structure

### 1.1 ADK's Foundational Principles

*   **Modularity**: Break down complex problems into smaller, manageable agents and tools.
*   **Composability**: Combine simple agents and tools to build sophisticated systems.
*   **Observability**: Detailed event logging and tracing capabilities to understand agent behavior.
*   **Extensibility**: Easily integrate with external services, models, and frameworks.
*   **Deployment-Agnostic**: Design agents once, deploy anywhere.

### 1.2 Essential Primitives

*   **`Agent`**: The core intelligent unit. Can be `LlmAgent` (LLM-driven) or `BaseAgent` (custom/workflow).
*   **`Tool`**: Callable function/class providing external capabilities (`FunctionTool`, `OpenAPIToolset`, etc.).
*   **`Session`**: A unique, stateful conversation thread with history (`events`) and short-term memory (`state`).
*   **`State`**: Key-value dictionary within a `Session` for transient conversation data.
*   **`Memory`**: Long-term, searchable knowledge base beyond a single session (`MemoryService`).
*   **`Artifact`**: Named, versioned binary data (files, images) associated with a session or user.
*   **`Runner`**: The execution engine; orchestrates agent activity and event flow.
*   **`Event`**: Atomic unit of communication and history; carries content and side-effect `actions`.
*   **`InvocationContext`**: The comprehensive root context object holding all runtime information for a single `run_async` call.

### 1.3 Standard Project Layout

A well-structured ADK project is crucial for maintainability and leveraging `adk` CLI tools.

```
your_project_root/
├── my_first_agent/             # Each folder is a distinct agent app
│   ├── __init__.py             # Makes `my_first_agent` a Python package (`from . import agent`)
│   ├── agent.py                # Contains `root_agent` definition and `LlmAgent`/WorkflowAgent instances
│   ├── tools.py                # Custom tool function definitions
│   ├── data/                   # Optional: static data, templates
│   └── .env                    # Environment variables (API keys, project IDs)
├── my_second_agent/
│   ├── __init__.py
│   └── agent.py
├── requirements.txt            # Project's Python dependencies (e.g., google-adk, litellm)
├── tests/                      # Unit and integration tests
│   ├── unit/
│   │   └── test_tools.py
│   └── integration/
│       └── test_my_first_agent.py
│       └── my_first_agent.evalset.json # Evaluation dataset for `adk eval`
└── main.py                     # Optional: Entry point for custom FastAPI server deployment
```
*   `adk web` and `adk run` automatically discover agents in subdirectories with `__init__.py` and `agent.py`.
*   `.env` files are automatically loaded by `adk` tools when run from the root or agent directory.

### 1.A Build Agents without Code (Agent Config)

ADK allows you to define agents, tools, and even multi-agent workflows using a simple YAML format, eliminating the need to write Python code for orchestration. This is ideal for rapid prototyping and for non-programmers to configure agents.

#### **Getting Started with Agent Config**

*   **Create a Config-based Agent**:
    ```bash
    adk create --type=config my_yaml_agent
    ```
    This generates a `my_yaml_agent/` folder with `root_agent.yaml` and `.env` files.

*   **Environment Setup** (in `.env` file):
    ```bash
    # For Google AI Studio (simpler setup)
    GOOGLE_GENAI_USE_VERTEXAI=0
    GOOGLE_API_KEY=<your-Google-Gemini-API-key>
    
    # For Google Cloud Vertex AI (production)
    GOOGLE_GENAI_USE_VERTEXAI=1
    GOOGLE_CLOUD_PROJECT=<your_gcp_project>
    GOOGLE_CLOUD_LOCATION=us-central1
    ```

#### **Core Agent Config Structure**

*   **Basic Agent (`root_agent.yaml`)**:
    ```yaml
    # yaml-language-server: $schema=https://raw.githubusercontent.com/google/adk-python/refs/heads/main/src/google/adk/agents/config_schemas/AgentConfig.json
    name: assistant_agent
    model: gemini-2.5-flash
    description: A helper agent that can answer users' various questions.
    instruction: You are an agent to help answer users' various questions.
    ```

*   **Agent with Built-in Tools**:
    ```yaml
    name: search_agent
    model: gemini-2.0-flash
    description: 'an agent whose job it is to perform Google search queries and answer questions about the results.'
    instruction: You are an agent whose job is to perform Google search queries and answer questions about the results.
    tools:
      - name: google_search # Built-in ADK tool
    ```

*   **Agent with Custom Tools**:
    ```yaml
    agent_class: LlmAgent
    model: gemini-2.5-flash
    name: prime_agent
    description: Handles checking if numbers are prime.
    instruction: |
      You are responsible for checking whether numbers are prime.
      When asked to check primes, you must call the check_prime tool with a list of integers.
      Never attempt to determine prime numbers manually.
    tools:
      - name: ma_llm.check_prime # Reference to Python function
    ```

*   **Multi-Agent System with Sub-Agents**:
    ```yaml
    agent_class: LlmAgent
    model: gemini-2.5-flash
    name: root_agent
    description: Learning assistant that provides tutoring in code and math.
    instruction: |
      You are a learning assistant that helps students with coding and math questions.
      
      You delegate coding questions to the code_tutor_agent and math questions to the math_tutor_agent.
      
      Follow these steps:
      1. If the user asks about programming or coding, delegate to the code_tutor_agent.
      2. If the user asks about math concepts or problems, delegate to the math_tutor_agent.
      3. Always provide clear explanations and encourage learning.
    sub_agents:
      - config_path: code_tutor_agent.yaml
      - config_path: math_tutor_agent.yaml
    ```

#### **Loading Agent Config in Python**

```python
from google.adk.agents import config_agent_utils
root_agent = config_agent_utils.from_config("{agent_folder}/root_agent.yaml")
```

#### **Running Agent Config Agents**

From the agent directory, use any of these commands:
*   `adk web` - Launch web UI interface
*   `adk run` - Run in terminal without UI
*   `adk api_server` - Run as a service for other applications

#### **Deployment Support**

Agent Config agents can be deployed using:
*   `adk deploy cloud_run` - Deploy to Google Cloud Run
*   `adk deploy agent_engine` - Deploy to Vertex AI Agent Engine

#### **Key Features & Capabilities**

*   **Supported Built-in Tools**: `google_search`, `load_artifacts`, `url_context`, `exit_loop`, `preload_memory`, `get_user_choice`, `enterprise_web_search`, `load_web_page`
*   **Custom Tool Integration**: Reference Python functions using fully qualified module paths
*   **Multi-Agent Orchestration**: Link agents via `config_path` references
*   **Schema Validation**: Built-in YAML schema for IDE support and validation

#### **Current Limitations** (Experimental Feature)

*   **Model Support**: Only Gemini models currently supported
*   **Language Support**: Custom tools must be written in Python
*   **Unsupported Agent Types**: `LangGraphAgent`, `A2aAgent`
*   **Unsupported Tools**: `AgentTool`, `LongRunningFunctionTool`, `VertexAiSearchTool`, `MCPToolset`, `CrewaiTool`, `LangchainTool`, `ExampleTool`

For complete examples and reference, see the [ADK samples repository](https://github.com/search?q=repo%3Agoogle%2Fadk-python+path%3A%2F%5Econtributing%5C%2Fsamples%5C%2F%2F+.yaml&type=code).

---

## 2. Agent Definitions (`LlmAgent`)

The `LlmAgent` is the cornerstone of intelligent behavior, leveraging an LLM for reasoning and decision-making.

### 2.1 Basic `LlmAgent` Setup

```python
from google.adk.agents import Agent

def get_current_time(city: str) -> dict:
    """Returns the current time in a specified city."""
    # Mock implementation
    if city.lower() == "new york":
        return {"status": "success", "time": "10:30 AM EST"}
    return {"status": "error", "message": f"Time for {city} not available."}

my_first_llm_agent = Agent(
    name="time_teller_agent",
    model="gemini-2.5-flash", # Essential: The LLM powering the agent
    instruction="You are a helpful assistant that tells the current time in cities. Use the 'get_current_time' tool for this purpose.",
    description="Tells the current time in a specified city.", # Crucial for multi-agent delegation
    tools=[get_current_time] # List of callable functions/tool instances
)
```

### 2.2 Advanced `LlmAgent` Configuration

*   **`generate_content_config`**: Controls LLM generation parameters (temperature, token limits, safety).
    ```python
    from google.genai import types as genai_types
    from google.adk.agents import Agent

    gen_config = genai_types.GenerateContentConfig(
        temperature=0.2,            # Controls randomness (0.0-1.0), lower for more deterministic.
        top_p=0.9,                  # Nucleus sampling: sample from top_p probability mass.
        top_k=40,                   # Top-k sampling: sample from top_k most likely tokens.
        max_output_tokens=1024,     # Max tokens in LLM's response.
        stop_sequences=["## END"]   # LLM will stop generating if these sequences appear.
    )
    agent = Agent(
        # ... basic config ...
        generate_content_config=gen_config
    )
    ```

*   **`output_key`**: Automatically saves the agent's final text or structured (if `output_schema` is used) response to the `session.state` under this key. Facilitates data flow between agents.
    ```python
    agent = Agent(
        # ... basic config ...
        output_key="llm_final_response_text"
    )
    # After agent runs, session.state['llm_final_response_text'] will contain its output.
    ```

*   **`input_schema` & `output_schema`**: Define strict JSON input/output formats using Pydantic models.
    > **Warning**: Using `output_schema` forces the LLM to generate JSON and **disables** its ability to use tools or delegate to other agents.

#### **Example: Defining and Using Structured Output**

This is the most reliable way to make an LLM produce predictable, parseable JSON, which is essential for multi-agent workflows.

1.  **Define the Schema with Pydantic:**
    ```python
    from pydantic import BaseModel, Field
    from typing import Literal

    class SearchQuery(BaseModel):
        """Model representing a specific search query for web search."""
        search_query: str = Field(
            description="A highly specific and targeted query for web search."
        )

    class Feedback(BaseModel):
        """Model for providing evaluation feedback on research quality."""
        grade: Literal["pass", "fail"] = Field(
            description="Evaluation result. 'pass' if the research is sufficient, 'fail' if it needs revision."
        )
        comment: str = Field(
            description="Detailed explanation of the evaluation, highlighting strengths and/or weaknesses of the research."
        )
        follow_up_queries: list[SearchQuery] | None = Field(
            default=None,
            description="A list of specific, targeted follow-up search queries needed to fix research gaps. This should be null or empty if the grade is 'pass'."
        )
    ```
    *   **`BaseModel` & `Field`**: Define data types, defaults, and crucial `description` fields. These descriptions are sent to the LLM to guide its output.
    *   **`Literal`**: Enforces strict enum-like values (`"pass"` or `"fail"`), preventing the LLM from hallucinating unexpected values.

2.  **Assign the Schema to an `LlmAgent`:**
    ```python
    research_evaluator = LlmAgent(
        name="research_evaluator",
        model="gemini-2.5-pro",
        instruction="""You are a meticulous quality assurance analyst. Evaluate the research findings in 'section_research_findings' and be very critical.
        If you find significant gaps, assign a grade of 'fail', write a detailed comment, and generate 5-7 specific follow-up queries.
        If the research is thorough, grade it 'pass'.
        Your response must be a single, raw JSON object validating against the 'Feedback' schema.
        """,
        output_schema=Feedback, # This forces the LLM to output JSON matching the Feedback model.
        output_key="research_evaluation", # The resulting JSON object will be saved to state.
        disallow_transfer_to_peers=True, # Prevents this agent from delegating. Its job is only to evaluate.
    )
    ```

*   **`include_contents`**: Controls whether the conversation history is sent to the LLM.
    *   `'default'` (default): Sends relevant history.
    *   `'none'`: Sends no history; agent operates purely on current turn's input and `instruction`. Useful for stateless API wrapper agents.
    ```python
    agent = Agent(..., include_contents='none')
    ```

*   **`planner`**: Assign a `BasePlanner` instance to enable multi-step reasoning.
    *   **`BuiltInPlanner`**: Leverages a model's native "thinking" or planning capabilities (e.g., Gemini).
        ```python
        from google.adk.planners import BuiltInPlanner
        from google.genai.types import ThinkingConfig

        agent = Agent(
            model="gemini-2.5-flash",
            planner=BuiltInPlanner(
                thinking_config=ThinkingConfig(include_thoughts=True)
            ),
            # ... tools ...
        )
        ```
    *   **`PlanReActPlanner`**: Instructs the model to follow a structured Plan-Reason-Act output format, useful for models without built-in planning.

*   **`code_executor`**: Assign a `BaseCodeExecutor` to allow the agent to execute code blocks.
    *   **`BuiltInCodeExecutor`**: The standard, sandboxed code executor provided by ADK for safe execution.
        ```python
        from google.adk.code_executors import BuiltInCodeExecutor
        agent = Agent(
            name="code_agent",
            model="gemini-2.5-flash",
            instruction="Write and execute Python code to solve math problems.",
            code_executor=BuiltInCodeExecutor() # Corrected from a list to an instance
        )
        ```

*   **Callbacks**: Hooks for observing and modifying agent behavior at key lifecycle points (`before_model_callback`, `after_tool_callback`, etc.). (Covered in Callbacks).

### 2.3 LLM Instruction Crafting (`instruction`)

The `instruction` is critical. It guides the LLM's behavior, persona, and tool usage. The following examples demonstrate powerful techniques for creating specialized, reliable agents.

**Best Practices & Examples:**

*   **Be Specific & Concise**: Avoid ambiguity.
*   **Define Persona & Role**: Give the LLM a clear role.
*   **Constrain Behavior & Tool Use**: Explicitly state what the LLM should *and should not* do.
*   **Define Output Format**: Tell the LLM *exactly* what its output should look like, especially when not using `output_schema`.
*   **Dynamic Injection**: Use `{state_key}` to inject runtime data from `session.state` into the prompt.
*   **Iteration**: Test, observe, and refine instructions.

**Example 1: Constraining Tool Use and Output Format**
```python
import datetime
from google.adk.tools import google_search   


plan_generator = LlmAgent(
    model="gemini-2.5-flash",
    name="plan_generator",
    description="Generates a 4-5 line action-oriented research plan.",
    instruction=f"""
    You are a research strategist. Your job is to create a high-level RESEARCH PLAN, not a summary.
    **RULE: Your output MUST be a bulleted list of 4-5 action-oriented research goals or key questions.**
    - A good goal starts with a verb like "Analyze," "Identify," "Investigate."
    - A bad output is a statement of fact like "The event was in April 2024."
    **TOOL USE IS STRICTLY LIMITED:**
    Your goal is to create a generic, high-quality plan *without searching*.
    Only use `google_search` if a topic is ambiguous and you absolutely cannot create a plan without it.
    You are explicitly forbidden from researching the *content* or *themes* of the topic.
    Current date: {datetime.datetime.now().strftime("%Y-%m-%d")}
    """,
    tools=[google_search],
)
```

**Example 2: Injecting Data from State and Specifying Custom Tags**
This agent's `instruction` relies on data placed in `session.state` by previous agents.
```python
report_composer = LlmAgent(
    model="gemini-2.5-pro",
    name="report_composer_with_citations",
    include_contents="none", # History not needed; all data is injected.
    description="Transforms research data and a markdown outline into a final, cited report.",
    instruction="""
    Transform the provided data into a polished, professional, and meticulously cited research report.

    ---
    ### INPUT DATA
    *   Research Plan: `{research_plan}`
    *   Research Findings: `{section_research_findings}`
    *   Citation Sources: `{sources}`
    *   Report Structure: `{report_sections}`

    ---
    ### CRITICAL: Citation System
    To cite a source, you MUST insert a special citation tag directly after the claim it supports.

    **The only correct format is:** `<cite source="src-ID_NUMBER" />`

    ---
    ### Final Instructions
    Generate a comprehensive report using ONLY the `<cite source="src-ID_NUMBER" />` tag system for all citations.
    The final report must strictly follow the structure provided in the **Report Structure** markdown outline.
    Do not include a "References" or "Sources" section; all citations must be in-line.
    """,
    output_key="final_cited_report",
)
```

---

## 3. Orchestration with Workflow Agents

Workflow agents (`SequentialAgent`, `ParallelAgent`, `LoopAgent`) provide deterministic control flow, combining LLM capabilities with structured execution. They do **not** use an LLM for their own orchestration logic.

### 3.1 `SequentialAgent`: Linear Execution

Executes `sub_agents` one after another in the order defined. The `InvocationContext` is passed along, allowing state changes to be visible to subsequent agents.

```python
from google.adk.agents import SequentialAgent, Agent

# Agent 1: Summarizes a document and saves to state
summarizer = Agent(
    name="DocumentSummarizer",
    model="gemini-2.5-flash",
    instruction="Summarize the provided document in 3 sentences.",
    output_key="document_summary" # Output saved to session.state['document_summary']
)

# Agent 2: Generates questions based on the summary from state
question_generator = Agent(
    name="QuestionGenerator",
    model="gemini-2.5-flash",
    instruction="Generate 3 comprehension questions based on this summary: {document_summary}",
    # 'document_summary' is dynamically injected from session.state
)

document_pipeline = SequentialAgent(
    name="SummaryQuestionPipeline",
    sub_agents=[summarizer, question_generator], # Order matters!
    description="Summarizes a document then generates questions."
)
```

### 3.2 `ParallelAgent`: Concurrent Execution

Executes `sub_agents` simultaneously. Useful for independent tasks to reduce overall latency. All sub-agents share the same `session.state`.

```python
from google.adk.agents import ParallelAgent, Agent, SequentialAgent

# Agents to fetch data concurrently
fetch_stock_price = Agent(name="StockPriceFetcher", ..., output_key="stock_data")
fetch_news_headlines = Agent(name="NewsFetcher", ..., output_key="news_data")
fetch_social_sentiment = Agent(name="SentimentAnalyzer", ..., output_key="sentiment_data")

# Agent to merge results (runs after ParallelAgent, usually in a SequentialAgent)
merger_agent = Agent(
    name="ReportGenerator",
    model="gemini-2.5-flash",
    instruction="Combine stock data: {stock_data}, news: {news_data}, and sentiment: {sentiment_data} into a market report."
)

# Pipeline to run parallel fetching then sequential merging
market_analysis_pipeline = SequentialAgent(
    name="MarketAnalyzer",
    sub_agents=[
        ParallelAgent(
            name="ConcurrentFetch",
            sub_agents=[fetch_stock_price, fetch_news_headlines, fetch_social_sentiment]
        ),
        merger_agent # Runs after all parallel agents complete
    ]
)
```
*   **Concurrency Caution**: When parallel agents write to the same `state` key, race conditions can occur. Always use distinct `output_key`s or manage concurrent writes explicitly.

### 3.3 `LoopAgent`: Iterative Processes

Repeatedly executes its `sub_agents` (sequentially within each loop iteration) until a condition is met or `max_iterations` is reached.

#### **Termination of `LoopAgent`**
A `LoopAgent` terminates when:
1.  `max_iterations` is reached.
2.  Any `Event` yielded by a sub-agent (or a tool within it) sets `actions.escalate = True`. This provides dynamic, content-driven loop termination.

#### **Example: Iterative Refinement Loop with a Custom `BaseAgent` for Control**
This example shows a loop that continues until a condition, determined by an evaluation agent, is met.

```python
from google.adk.agents import LoopAgent, Agent, BaseAgent
from google.adk.events import Event, EventActions
from google.adk.agents.invocation_context import InvocationContext
from typing import AsyncGenerator

# An LLM Agent that evaluates research and produces structured JSON output
research_evaluator = Agent(
    name="research_evaluator",
    # ... configuration from Section 2.2 ...
    output_schema=Feedback,
    output_key="research_evaluation",
)

# An LLM Agent that performs additional searches based on feedback
enhanced_search_executor = Agent(
    name="enhanced_search_executor",
    instruction="Execute the follow-up queries from 'research_evaluation' and combine with existing findings.",
    # ... other configurations ...
)

# A custom BaseAgent to check the evaluation and stop the loop
class EscalationChecker(BaseAgent):
    """Checks research evaluation and escalates to stop the loop if grade is 'pass'."""
    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        evaluation = ctx.session.state.get("research_evaluation")
        if evaluation and evaluation.get("grade") == "pass":
            # The key to stopping the loop: yield an Event with escalate=True
            yield Event(author=self.name, actions=EventActions(escalate=True))
        else:
            # Let the loop continue
            yield Event(author=self.name)

# Define the loop
iterative_refinement_loop = LoopAgent(
    name="IterativeRefinementLoop",
    sub_agents=[
        research_evaluator, # Step 1: Evaluate
        EscalationChecker(name="EscalationChecker"), # Step 2: Check and maybe stop
        enhanced_search_executor, # Step 3: Refine (only runs if loop didn't stop)
    ],
    max_iterations=5, # Fallback to prevent infinite loops
    description="Iteratively evaluates and refines research until it passes quality checks."
)
```

---

## 4. Multi-Agent Systems & Communication

Building complex applications by composing multiple, specialized agents.

### 4.1 Agent Hierarchy

A hierarchical (tree-like) structure of parent-child relationships defined by the `sub_agents` parameter during `BaseAgent` initialization. An agent can only have one parent.

```python
# Conceptual Hierarchy
# Root
# └── Coordinator (LlmAgent)
#     ├── SalesAgent (LlmAgent)
#     └── SupportAgent (LlmAgent)
#     └── DataPipeline (SequentialAgent)
#         ├── DataFetcher (LlmAgent)
#         └── DataProcessor (LlmAgent)
```

### 4.2 Inter-Agent Communication Mechanisms

1.  **Shared Session State (`session.state`)**: The most common and robust method. Agents read from and write to the same mutable dictionary.
    *   **Mechanism**: Agent A sets `ctx.session.state['key'] = value`. Agent B later reads `ctx.session.state.get('key')`. `output_key` on `LlmAgent` is a convenient auto-setter.
    *   **Best for**: Passing intermediate results, shared configurations, and flags in pipelines (Sequential, Loop agents).

2.  **LLM-Driven Delegation (`transfer_to_agent`)**: A `LlmAgent` can dynamically hand over control to another agent based on its reasoning.
    *   **Mechanism**: The LLM generates a special `transfer_to_agent` function call. The ADK framework intercepts this, routes the next turn to the target agent.
    *   **Prerequisites**:
        *   The initiating `LlmAgent` needs `instruction` to guide delegation and `description` of the target agent(s).
        *   Target agents need clear `description`s to help the LLM decide.
        *   Target agent must be discoverable within the current agent's hierarchy (direct `sub_agent` or a descendant).
    *   **Configuration**: Can be enabled/disabled via `disallow_transfer_to_parent` and `disallow_transfer_to_peers` on `LlmAgent`.

3.  **Explicit Invocation (`AgentTool`)**: An `LlmAgent` can treat another `BaseAgent` instance as a callable tool.
    *   **Mechanism**: Wrap the target agent (`target_agent`) in `AgentTool(agent=target_agent)` and add it to the calling `LlmAgent`'s `tools` list. The `AgentTool` generates a `FunctionDeclaration` for the LLM. When called, `AgentTool` runs the target agent and returns its final response as the tool result.
    *   **Best for**: Hierarchical task decomposition, where a higher-level agent needs a specific output from a lower-level agent.

### 4.3 Common Multi-Agent Patterns

*   **Coordinator/Dispatcher**: A central agent routes requests to specialized sub-agents (often via LLM-driven delegation).
*   **Sequential Pipeline**: `SequentialAgent` orchestrates a fixed sequence of tasks, passing data via shared state.
*   **Parallel Fan-Out/Gather**: `ParallelAgent` runs concurrent tasks, followed by a final agent that synthesizes results from state.
*   **Review/Critique (Generator-Critic)**: `SequentialAgent` with a generator followed by a critic, often in a `LoopAgent` for iterative refinement.
*   **Hierarchical Task Decomposition (Planner/Executor)**: High-level agents break down complex problems, delegating sub-tasks to lower-level agents (often via `AgentTool` and delegation).

#### **Example: Hierarchical Planner/Executor Pattern**
This pattern combines several mechanisms. A top-level `interactive_planner_agent` uses another agent (`plan_generator`) as a tool to create a plan, then delegates the execution of that plan to a complex `SequentialAgent` (`research_pipeline`).

```python
from google.adk.agents import LlmAgent, SequentialAgent, LoopAgent
from google.adk.tools.agent_tool import AgentTool

# Assume plan_generator, section_planner, research_evaluator, etc. are defined.

# The execution pipeline itself is a complex agent.
research_pipeline = SequentialAgent(
    name="research_pipeline",
    description="Executes a pre-approved research plan. It performs iterative research, evaluation, and composes a final, cited report.",
    sub_agents=[
        section_planner,
        section_researcher,
        LoopAgent(
            name="iterative_refinement_loop",
            max_iterations=3,
            sub_agents=[
                research_evaluator,
                EscalationChecker(name="escalation_checker"),
                enhanced_search_executor,
            ],
        ),
        report_composer,
    ],
)

# The top-level agent that interacts with the user.
interactive_planner_agent = LlmAgent(
    name="interactive_planner_agent",
    model="gemini-2.5-flash",
    description="The primary research assistant. It collaborates with the user to create a research plan, and then executes it upon approval.",
    instruction="""
    You are a research planning assistant. Your workflow is:
    1.  **Plan:** Use the `plan_generator` tool to create a draft research plan.
    2.  **Refine:** Incorporate user feedback until the plan is approved.
    3.  **Execute:** Once the user gives EXPLICIT approval (e.g., "looks good, run it"), you MUST delegate the task to the `research_pipeline` agent.
    Your job is to Plan, Refine, and Delegate. Do not do the research yourself.
    """,
    # The planner delegates to the pipeline.
    sub_agents=[research_pipeline],
    # The planner uses another agent as a tool.
    tools=[AgentTool(plan_generator)],
    output_key="research_plan",
)

# The root agent of the application is the top-level planner.
root_agent = interactive_planner_agent
```

### 4.A. Distributed Communication (A2A Protocol)

The Agent-to-Agent (A2A) Protocol enables agents to communicate over a network, even if they are written in different languages or run as separate services. Use A2A for integrating with third-party agents, building microservice-based agent architectures, or when a strong, formal API contract is needed. For internal code organization, prefer local sub-agents.

*   **Exposing an Agent**: Make an existing ADK agent available to others over A2A.
    *   **`to_a2a()` Utility**: The simplest method. Wraps your `root_agent` and creates a runnable FastAPI app, auto-generating the required `agent.json` card.
        ```python
        from google.adk.a2a.utils.agent_to_a2a import to_a2a
        # root_agent is your existing ADK Agent instance
        a2a_app = to_a2a(root_agent, port=8001)
        # Run with: uvicorn your_module:a2a_app --host localhost --port 8001
        ```
    *   **`adk api_server --a2a`**: A CLI command that serves agents from a directory. Requires you to manually create an `agent.json` card for each agent you want to expose.

*   **Consuming a Remote Agent**: Use a remote A2A agent as if it were a local agent.
    *   **`RemoteA2aAgent`**: This agent acts as a client proxy. You initialize it with the URL to the remote agent's card.
        ```python
        from google.adk.a2a.remote_a2a_agent import RemoteA2aAgent

        # This agent can now be used as a sub-agent or tool
        prime_checker_agent = RemoteA2aAgent(
            name="prime_agent",
            description="A remote agent that checks if numbers are prime.",
            agent_card="http://localhost:8001/a2a/check_prime_agent/.well-known/agent.json"
        )
        ```

---

## 5. Building Custom Agents (`BaseAgent`)

For unique orchestration logic that doesn't fit standard workflow agents, inherit directly from `BaseAgent`.

### 5.1 When to Use Custom Agents

*   **Complex Conditional Logic**: `if/else` branching based on multiple state variables.
*   **Dynamic Agent Selection**: Choosing which sub-agent to run based on runtime evaluation.
*   **Direct External Integrations**: Calling external APIs or libraries directly within the orchestration flow.
*   **Custom Loop/Retry Logic**: More sophisticated iteration patterns than `LoopAgent`, such as the `EscalationChecker` example.

### 5.2 Implementing `_run_async_impl`

This is the core asynchronous method you must override.

#### **Example: A Custom Agent for Loop Control**
This agent reads state, applies simple Python logic, and yields an `Event` with an `escalate` action to control a `LoopAgent`.

```python
from google.adk.agents import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event, EventActions
from typing import AsyncGenerator
import logging

class EscalationChecker(BaseAgent):
    """Checks research evaluation and escalates to stop the loop if grade is 'pass'."""

    def __init__(self, name: str):
        super().__init__(name=name)

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        # 1. Read from session state.
        evaluation_result = ctx.session.state.get("research_evaluation")

        # 2. Apply custom Python logic.
        if evaluation_result and evaluation_result.get("grade") == "pass":
            logging.info(
                f"[{self.name}] Research passed. Escalating to stop loop."
            )
            # 3. Yield an Event with a control Action.
            yield Event(author=self.name, actions=EventActions(escalate=True))
        else:
            logging.info(
                f"[{self.name}] Research failed or not found. Loop continues."
            )
            # Yielding an event without actions lets the flow continue.
            yield Event(author=self.name)
```
*   **Asynchronous Generator**: `async def ... yield Event`. This allows pausing and resuming execution.
*   **`ctx: InvocationContext`**: Provides access to all session state (`ctx.session.state`).
*   **Calling Sub-Agents**: Use `async for event in self.sub_agent_instance.run_async(ctx): yield event`.
*   **Control Flow**: Use standard Python `if/else`, `for/while` loops for complex logic.

---

## 6. Models: Gemini, LiteLLM, and Vertex AI

ADK's model flexibility allows integrating various LLMs for different needs.

### 6.1 Google Gemini Models (AI Studio & Vertex AI)

*   **Default Integration**: Native support via `google-genai` library.
*   **AI Studio (Easy Start)**:
    *   Set `GOOGLE_API_KEY="YOUR_API_KEY"` (environment variable).
    *   Set `GOOGLE_GENAI_USE_VERTEXAI="False"`.
    *   Model strings: `"gemini-2.5-flash"`, `"gemini-2.5-pro"`, etc.
*   **Vertex AI (Production)**:
    *   Authenticate via `gcloud auth application-default login` (recommended).
    *   Set `GOOGLE_CLOUD_PROJECT="YOUR_PROJECT_ID"`, `GOOGLE_CLOUD_LOCATION="your-region"` (environment variables).
    *   Set `GOOGLE_GENAI_USE_VERTEXAI="True"`.
    *   Model strings: `"gemini-2.5-flash"`, `"gemini-2.5-pro"`, or full Vertex AI endpoint resource names for specific deployments.

### 6.2 Other Cloud & Proprietary Models via LiteLLM

`LiteLlm` provides a unified interface to 100+ LLMs (OpenAI, Anthropic, Cohere, etc.).

*   **Installation**: `pip install litellm`
*   **API Keys**: Set environment variables as required by LiteLLM (e.g., `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`).
*   **Usage**:
    ```python
    from google.adk.models.lite_llm import LiteLlm
    agent_openai = Agent(model=LiteLlm(model="openai/gpt-4o"), ...)
    agent_claude = Agent(model=LiteLlm(model="anthropic/claude-3-haiku-20240307"), ...)
    ```

### 6.3 Open & Local Models via LiteLLM (Ollama, vLLM)

For self-hosting, cost savings, privacy, or offline use.

*   **Ollama Integration**: Run Ollama locally (`ollama run <model>`).
    ```bash
    export OLLAMA_API_BASE="http://localhost:11434" # Ensure Ollama server is running
    ```
    ```python
    from google.adk.models.lite_llm import LiteLlm
    # Use 'ollama_chat' provider for tool-calling capabilities with Ollama models
    agent_ollama = Agent(model=LiteLlm(model="ollama_chat/llama3:instruct"), ...)
    ```

*   **Self-Hosted Endpoint (e.g., vLLM)**:
    ```python
    from google.adk.models.lite_llm import LiteLlm
    api_base_url = "https://your-vllm-endpoint.example.com/v1"
    agent_vllm = Agent(
        model=LiteLlm(
            model="your-model-name-on-vllm",
            api_base=api_base_url,
            extra_headers={"Authorization": "Bearer YOUR_TOKEN"},
        ),
        ...
    )
    ```

### 6.4 Customizing LLM API Clients

For `google-genai` (used by Gemini models), you can configure the underlying client.

```python
import os
from google.genai import configure as genai_configure

genai_configure.use_defaults(
    timeout=60, # seconds
    client_options={"api_key": os.getenv("GOOGLE_API_KEY")},
)
```

---

## 7. Tools: The Agent's Capabilities

Tools extend an agent's abilities beyond text generation.

### 7.1 Defining Function Tools: Principles & Best Practices

*   **Signature**: `def my_tool(param1: Type, param2: Type, tool_context: ToolContext) -> dict:`
*   **Function Name**: Descriptive verb-noun (e.g., `schedule_meeting`).
*   **Parameters**: Clear names, required type hints, **NO DEFAULT VALUES**.
*   **Return Type**: **Must** be a `dict` (JSON-serializable), preferably with a `'status'` key.
*   **Docstring**: **CRITICAL**. Explain purpose, when to use, arguments, and return value structure. **AVOID** mentioning `tool_context`.

    ```python
    def calculate_compound_interest(
        principal: float,
        rate: float,
        years: int,
        compounding_frequency: int,
        tool_context: ToolContext
    ) -> dict:
        """Calculates the future value of an investment with compound interest.

        Use this tool to calculate the future value of an investment given a
        principal amount, interest rate, number of years, and how often the
        interest is compounded per year.

        Args:
            principal (float): The initial amount of money invested.
            rate (float): The annual interest rate (e.g., 0.05 for 5%).
            years (int): The number of years the money is invested.
            compounding_frequency (int): The number of times interest is compounded
                                         per year (e.g., 1 for annually, 12 for monthly).
            
        Returns:
            dict: Contains the calculation result.
                  - 'status' (str): "success" or "error".
                  - 'future_value' (float, optional): The calculated future value.
                  - 'error_message' (str, optional): Description of error, if any.
        """
        # ... implementation ...
    ```

### 7.2 The `ToolContext` Object: Accessing Runtime Information

`ToolContext` is the gateway for tools to interact with the ADK runtime.

*   `tool_context.state`: Read and write to the current `Session`'s `state` dictionary.
*   `tool_context.actions`: Modify the `EventActions` object (e.g., `tool_context.actions.escalate = True`).
*   `tool_context.load_artifact(filename)` / `tool_context.save_artifact(filename, part)`: Manage binary data.
*   `tool_context.search_memory(query)`: Query the long-term `MemoryService`.

### 7.3 All Tool Types & Their Usage

1.  **Custom Function Tools**:
    *   **`FunctionTool`**: The most common type, wrapping a standard Python function.
    *   **`LongRunningFunctionTool`**: Wraps an `async` function that `yields` intermediate results, for tasks that provide progress updates.
    *   **`AgentTool`**: Wraps another `BaseAgent` instance, allowing it to be invoked as a tool by a parent agent.

2.  **Built-in Tools**: Ready-to-use tools provided by ADK.
    *   `google_search`: Provides Google Search grounding.
    *   `BuiltInCodeExecutor`: Enables sandboxed code execution.
    *   `VertexAiSearchTool`: Provides grounding from your private Vertex AI Search data stores.
    *   `BigQueryToolset`: A collection of tools for interacting with BigQuery (e.g., `list_datasets`, `execute_sql`).
    > **Warning**: An agent can only use one type of built-in tool at a time and they cannot be used in sub-agents.

3.  **Third-Party Tool Wrappers**: For seamless integration with other frameworks.
    *   `LangchainTool`: Wraps a tool from the LangChain ecosystem.
    *   `CrewaiTool`: Wraps a tool from the CrewAI library.

4.  **OpenAPI & Protocol Tools**: For interacting with APIs and services.
    *   **`OpenAPIToolset`**: Automatically generates a set of `RestApiTool`s from an OpenAPI (Swagger) v3 specification.
    *   **`MCPToolset`**: Connects to an external Model Context Protocol (MCP) server to dynamically load its tools.

5.  **Google Cloud Tools**: For deep integration with Google Cloud services.
    *   **`ApiHubToolset`**: Turns any documented API from Apigee API Hub into a tool.
    *   **`ApplicationIntegrationToolset`**: Turns Application Integration workflows and Integration Connectors (e.g., Salesforce, SAP) into callable tools.
    *   **Toolbox for Databases**: An open-source MCP server that ADK can connect to for database interactions.

---

## 8. Context, State, and Memory Management

Effective context management is crucial for coherent, multi-turn conversations.

### 8.1 The `Session` Object & `SessionService`

*   **`Session`**: The container for a single, ongoing conversation (`id`, `state`, `events`).
*   **`SessionService`**: Manages the lifecycle of `Session` objects (`create_session`, `get_session`, `append_event`).
*   **Implementations**: `InMemorySessionService` (dev), `VertexAiSessionService` (prod), `DatabaseSessionService` (self-managed).

### 8.2 `State`: The Conversational Scratchpad

A mutable dictionary within `session.state` for short-term, dynamic data.

*   **Update Mechanism**: Always update via `context.state` (in callbacks/tools) or `LlmAgent.output_key`.
*   **Prefixes for Scope**:
    *   **(No prefix)**: Session-specific (e.g., `session.state['booking_step']`).
    *   `user:`: Persistent for a `user_id` across all their sessions (e.g., `session.state['user:preferred_currency']`).
    *   `app:`: Persistent for `app_name` across all users and sessions.
    *   `temp:`: Volatile, for the current `Invocation` turn only.

### 8.3 `Memory`: Long-Term Knowledge & Retrieval

For knowledge beyond a single conversation.

*   **`BaseMemoryService`**: Defines the interface (`add_session_to_memory`, `search_memory`).
*   **Implementations**: `InMemoryMemoryService`, `VertexAiRagMemoryService`.
*   **Usage**: Agents interact via tools (e.g., the built-in `load_memory` tool).

### 8.4 `Artifacts`: Binary Data Management

For named, versioned binary data (files, images).

*   **Representation**: `google.genai.types.Part` (containing a `Blob` with `data: bytes` and `mime_type: str`).
*   **`BaseArtifactService`**: Manages storage (`save_artifact`, `load_artifact`).
*   **Implementations**: `InMemoryArtifactService`, `GcsArtifactService`.

---

## 9. Runtime, Events, and Execution Flow

The `Runner` is the central orchestrator of an ADK application.

### 9.1 The `Runner`: The Orchestrator

*   **Role**: Manages the agent's lifecycle, the event loop, and coordinates with services.
*   **Entry Point**: `runner.run_async(user_id, session_id, new_message)`.

### 9.2 The Event Loop: Core Execution Flow

1.  User input becomes a `user` `Event`.
2.  `Runner` calls `agent.run_async(invocation_context)`.
3.  Agent `yield`s an `Event` (e.g., tool call, text response). Execution pauses.
4.  `Runner` processes the `Event` (applies state changes, etc.) and yields it to the client.
5.  Execution resumes. This cycle repeats until the agent is done.

### 9.3 `Event` Object: The Communication Backbone

`Event` objects carry all information and signals.

*   `Event.author`: Source of the event (`'user'`, agent name, `'system'`).
*   `Event.content`: The primary payload (text, function calls, function responses).
*   `Event.actions`: Signals side effects (`state_delta`, `transfer_to_agent`, `escalate`).
*   `Event.is_final_response()`: Helper to identify the complete, displayable message.

### 9.4 Asynchronous Programming (Python Specific)

ADK is built on `asyncio`. Use `async def`, `await`, and `async for` for all I/O-bound operations.

---

## 10. Control Flow with Callbacks

Callbacks are functions that intercept and control agent execution at specific points.

### 10.1 Callback Mechanism: Interception & Control

*   **Definition**: A Python function assigned to an agent's `callback` parameter (e.g., `after_agent_callback=my_func`).
*   **Context**: Receives a `CallbackContext` (or `ToolContext`) with runtime info.
*   **Return Value**: **Crucially determines flow.**
    *   `return None`: Allow the default action to proceed.
    *   `return <Specific Object>`: **Override** the default action/result.

### 10.2 Types of Callbacks

1.  **Agent Lifecycle**: `before_agent_callback`, `after_agent_callback`.
2.  **LLM Interaction**: `before_model_callback`, `after_model_callback`.
3.  **Tool Execution**: `before_tool_callback`, `after_tool_callback`.

### 10.3 Callback Best Practices

*   **Keep Focused**: Each callback for a single purpose.
*   **Performance**: Avoid blocking I/O or heavy computation.
*   **Error Handling**: Use `try...except` to prevent crashes.

#### **Example 1: Data Aggregation with `after_agent_callback`**
This callback runs after an agent, inspects the `session.events` to find structured data from tool calls (like `google_search` results), and saves it to state for later use.

```python
from google.adk.agents.callback_context import CallbackContext

def collect_research_sources_callback(callback_context: CallbackContext) -> None:
    """Collects and organizes web research sources from agent events."""
    session = callback_context._invocation_context.session
    # Get existing sources from state to append to them.
    url_to_short_id = callback_context.state.get("url_to_short_id", {})
    sources = callback_context.state.get("sources", {})
    id_counter = len(url_to_short_id) + 1

    # Iterate through all events in the session to find grounding metadata.
    for event in session.events:
        if not (event.grounding_metadata and event.grounding_metadata.grounding_chunks):
            continue
        # ... logic to parse grounding_chunks and grounding_supports ...
        # (See full implementation in the original code snippet)

    # Save the updated source map back to state.
    callback_context.state["url_to_short_id"] = url_to_short_id
    callback_context.state["sources"] = sources

# Used in an agent like this:
# section_researcher = LlmAgent(..., after_agent_callback=collect_research_sources_callback)
```

#### **Example 2: Output Transformation with `after_agent_callback`**
This callback takes an LLM's raw output (containing custom tags), uses Python to format it into markdown, and returns the modified content, overriding the original.

```python
import re
from google.adk.agents.callback_context import CallbackContext
from google.genai import types as genai_types

def citation_replacement_callback(callback_context: CallbackContext) -> genai_types.Content:
    """Replaces <cite> tags in a report with Markdown-formatted links."""
    # 1. Get raw report and sources from state.
    final_report = callback_context.state.get("final_cited_report", "")
    sources = callback_context.state.get("sources", {})

    # 2. Define a replacer function for regex substitution.
    def tag_replacer(match: re.Match) -> str:
        short_id = match.group(1)
        if not (source_info := sources.get(short_id)):
            return "" # Remove invalid tags
        title = source_info.get("title", short_id)
        return f" [{title}]({source_info['url']})"

    # 3. Use regex to find all <cite> tags and replace them.
    processed_report = re.sub(
        r'<cite\s+source\s*=\s*["\']?(src-\d+)["\']?\s*/>',
        tag_replacer,
        final_report,
    )
    processed_report = re.sub(r"\s+([.,;:])", r"\1", processed_report) # Fix spacing

    # 4. Save the new version to state and return it to override the original agent output.
    callback_context.state["final_report_with_citations"] = processed_report
    return genai_types.Content(parts=[genai_types.Part(text=processed_report)])

# Used in an agent like this:
# report_composer = LlmAgent(..., after_agent_callback=citation_replacement_callback)
```

### 10.A. Global Control with Plugins

Plugins are stateful, reusable modules for implementing cross-cutting concerns that apply globally to all agents, tools, and model calls managed by a `Runner`. Unlike Callbacks which are configured per-agent, Plugins are registered once on the `Runner`.

*   **Use Cases**: Ideal for universal logging, application-wide policy enforcement, global caching, and collecting metrics.
*   **Execution Order**: Plugin callbacks run **before** their corresponding agent-level callbacks. If a plugin callback returns a value, the agent-level callback is skipped.
*   **Defining a Plugin**: Inherit from `BasePlugin` and implement callback methods.
    ```python
    from google.adk.plugins.base_plugin import BasePlugin
    from google.adk.agents.callback_context import CallbackContext

    class InvocationCounterPlugin(BasePlugin):
        def __init__(self):
            super().__init__(name="invocation_counter")
            self.agent_runs = 0

        async def before_agent_callback(self, callback_context: CallbackContext, **kwargs):
            self.agent_runs += 1
            print(f"[Plugin] Total agent runs: {self.agent_runs}")
    ```
*   **Registering a Plugin**:
    ```python
    from google.adk.runners import Runner
    # runner = Runner(agent=root_agent, ..., plugins=[InvocationCounterPlugin()])
    ```
*   **Error Handling Callbacks**: Plugins support unique error hooks like `on_model_error_callback` and `on_tool_error_callback` for centralized error management.
*   **Limitation**: Plugins are not supported by the `adk web` interface.

---

## 11. Authentication for Tools

Enabling agents to securely access protected external resources.

### 11.1 Core Concepts: `AuthScheme` & `AuthCredential`

*   **`AuthScheme`**: Defines *how* an API expects authentication (e.g., `APIKey`, `HTTPBearer`, `OAuth2`, `OpenIdConnectWithConfig`).
*   **`AuthCredential`**: Holds *initial* information to *start* the auth process (e.g., API key value, OAuth client ID/secret).

### 11.2 Interactive OAuth/OIDC Flows

When a tool requires user interaction (OAuth consent), ADK pauses and signals your `Agent Client` application.

1.  **Detect Auth Request**: `runner.run_async()` yields an event with a special `adk_request_credential` function call.
2.  **Redirect User**: Extract `auth_uri` from `auth_config` in the event. Your client app redirects the user's browser to this `auth_uri` (appending `redirect_uri`).
3.  **Handle Callback**: Your client app has a pre-registered `redirect_uri` to receive the user after authorization. It captures the full callback URL (containing `authorization_code`).
4.  **Send Auth Result to ADK**: Your client prepares a `FunctionResponse` for `adk_request_credential`, setting `auth_config.exchanged_auth_credential.oauth2.auth_response_uri` to the captured callback URL.
5.  **Resume Execution**: `runner.run_async()` is called again with this `FunctionResponse`. ADK performs the token exchange, stores the access token, and retries the original tool call.

### 11.3 Custom Tool Authentication

If building a `FunctionTool` that needs authentication:

1.  **Check for Cached Creds**: `tool_context.state.get("my_token_cache_key")`.
2.  **Check for Auth Response**: `tool_context.get_auth_response(my_auth_config)`.
3.  **Initiate Auth**: If no creds, call `tool_context.request_credential(my_auth_config)` and return a pending status. This triggers the external flow.
4.  **Cache Credentials**: After obtaining, store in `tool_context.state`.
5.  **Make API Call**: Use the valid credentials (e.g., `google.oauth2.credentials.Credentials`).

---

## 12. Deployment Strategies

From local dev to production.

### 12.1 Local Development & Testing (`adk web`, `adk run`, `adk api_server`)

*   **`adk web`**: Launches a local web UI for interactive chat, session inspection, and visual tracing.
    ```bash
    adk web /path/to/your/project_root
    ```
*   **`adk run`**: Command-line interactive chat.
    ```bash
    adk run /path/to/your/agent_folder
    ```
*   **`adk api_server`**: Launches a local FastAPI server exposing `/run`, `/run_sse`, `/list-apps`, etc., for API testing with `curl` or client libraries.
    ```bash
    adk api_server /path/to/your/project_root
    ```

### 12.2 Vertex AI Agent Engine

Fully managed, scalable service for ADK agents on Google Cloud.

*   **Features**: Auto-scaling, session management, observability integration.
*   **ADK CLI**: `adk deploy agent_engine --project <id> --region <loc> ... /path/to/agent`
*   **Deployment**: Use `vertexai.agent_engines.create()`.
    ```python
    from vertexai.preview import reasoning_engines # or agent_engines directly in later versions
    
    # Wrap your root_agent for deployment
    app_for_engine = reasoning_engines.AdkApp(agent=root_agent, enable_tracing=True)
    
    # Deploy
    remote_app = agent_engines.create(
        agent_engine=app_for_engine,
        requirements=["google-cloud-aiplatform[adk,agent_engines]"],
        display_name="My Production Agent"
    )
    print(remote_app.resource_name) # projects/PROJECT_NUM/locations/REGION/reasoningEngines/ID
    ```
*   **Interaction**: Use `remote_app.stream_query()`, `create_session()`, etc.

### 12.3 Cloud Run

Serverless container platform for custom web applications.

*   **ADK CLI**: `adk deploy cloud_run --project <id> --region <loc> ... /path/to/agent`
*   **Deployment**:
    1.  Create a `Dockerfile` for your FastAPI app (using `google.adk.cli.fast_api.get_fast_api_app`).
    2.  Use `gcloud run deploy --source .`.
    3.  Alternatively, `adk deploy cloud_run` (simpler, opinionated).
*   **Example `main.py`**:
    ```python
    import os
    from fastapi import FastAPI
    from google.adk.cli.fast_api import get_fast_api_app

    # Ensure your agent_folder (e.g., 'my_first_agent') is in the same directory as main.py
    app: FastAPI = get_fast_api_app(
        agents_dir=os.path.dirname(os.path.abspath(__file__)),
        session_service_uri="sqlite:///./sessions.db", # In-container SQLite, for simple cases
        # For production: use a persistent DB (Cloud SQL) or VertexAiSessionService
        allow_origins=["*"],
        web=True # Serve ADK UI
    )
    # uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080))) # If running directly
    ```

### 12.4 Google Kubernetes Engine (GKE)

For maximum control, run your containerized agent in a Kubernetes cluster.

*   **ADK CLI**: `adk deploy gke --project <id> --cluster_name <name> ... /path/to/agent`
*   **Deployment**:
    1.  Build Docker image (`gcloud builds submit`).
    2.  Create Kubernetes Deployment and Service YAMLs.
    3.  Apply with `kubectl apply -f deployment.yaml`.
    4.  Configure Workload Identity for GCP permissions.

### 12.5 CI/CD Integration

*   Automate testing (`pytest`, `adk eval`) in CI.
*   Automate container builds and deployments (e.g., Cloud Build, GitHub Actions).
*   Use environment variables for secrets.

---

## 13. Evaluation and Safety

Critical for robust, production-ready agents.

### 13.1 Agent Evaluation (`adk eval`)

Systematically assess agent performance using predefined test cases.

*   **Evalset File (`.evalset.json`)**: Contains `eval_cases`, each with a `conversation` (user queries, expected tool calls, expected intermediate/final responses) and `session_input` (initial state).
    ```json
    {
      "eval_set_id": "weather_bot_eval",
      "eval_cases": [
        {
          "eval_id": "london_weather_query",
          "conversation": [
            {
              "user_content": {"parts": [{"text": "What's the weather in London?"}]},
              "final_response": {"parts": [{"text": "The weather in London is cloudy..."}]},
              "intermediate_data": {
                "tool_uses": [{"name": "get_weather", "args": {"city": "London"}}]
              }
            }
          ],
          "session_input": {"app_name": "weather_app", "user_id": "test_user", "state": {}}
        }
      ]
    }
    ```
*   **Running Evaluation**:
    *   `adk web`: Interactive UI for creating/running eval cases.
    *   `adk eval /path/to/agent_folder /path/to/evalset.json`: CLI execution.
    *   `pytest`: Integrate `AgentEvaluator.evaluate()` into unit/integration tests.
*   **Metrics**: `tool_trajectory_avg_score` (tool calls match expected), `response_match_score` (final response similarity using ROUGE). Configurable via `test_config.json`.

### 13.2 Safety & Guardrails

Multi-layered defense against harmful content, misalignment, and unsafe actions.

1.  **Identity and Authorization**:
    *   **Agent-Auth**: Tool acts with the agent's service account (e.g., `Vertex AI User` role). Simple, but all users share access level. Logs needed for attribution.
    *   **User-Auth**: Tool acts with the end-user's identity (via OAuth tokens). Reduces risk of abuse.
2.  **In-Tool Guardrails**: Design tools defensively. Tools can read policies from `tool_context.state` (set deterministically by developer) and validate model-provided arguments before execution.
    ```python
    def execute_sql(query: str, tool_context: ToolContext) -> dict:
        policy = tool_context.state.get("user:sql_policy", {})
        if not policy.get("allow_writes", False) and ("INSERT" in query.upper() or "DELETE" in query.upper()):
            return {"status": "error", "message": "Policy: Write operations are not allowed."}
        # ... execute query ...
    ```
3.  **Built-in Gemini Safety Features**:
    *   **Content Safety Filters**: Automatically block harmful content (CSAM, PII, hate speech, etc.). Configurable thresholds.
    *   **System Instructions**: Guide model behavior, define prohibited topics, brand tone, disclaimers.
4.  **Model and Tool Callbacks (LLM as a Guardrail)**: Use callbacks to inspect inputs/outputs.
    *   `before_model_callback`: Intercept `LlmRequest` before it hits the LLM. Block (return `LlmResponse`) or modify.
    *   `before_tool_callback`: Intercept tool calls (name, args) before execution. Block (return `dict`) or modify.
    *   **LLM-based Safety**: Use a cheap/fast LLM (e.g., Gemini Flash) in a callback to classify input/output safety.
        ```python
        def safety_checker_callback(context: CallbackContext, llm_request: LlmRequest) -> Optional[LlmResponse]:
            # Use a separate, small LLM to classify safety
            safety_llm_agent = Agent(name="SafetyChecker", model="gemini-2.5-flash-001", instruction="Classify input as 'safe' or 'unsafe'. Output ONLY the word.")
            # Run the safety agent (might need a new runner instance or direct model call)
            # For simplicity, a mock:
            user_input = llm_request.contents[-1].parts[0].text
            if "dangerous_phrase" in user_input.lower():
                context.state["safety_violation"] = True
                return LlmResponse(content=genai_types.Content(parts=[genai_types.Part(text="I cannot process this request due to safety concerns.")]))
            return None
        ```
5.  **Sandboxed Code Execution**:
    *   `BuiltInCodeExecutor`: Uses secure, sandboxed execution environments.
    *   Vertex AI Code Interpreter Extension.
    *   If custom, ensure hermetic environments (no network, isolated).
6.  **Network Controls & VPC-SC**: Confine agent activity within secure perimeters (VPC Service Controls) to prevent data exfiltration.
7.  **Output Escaping in UIs**: Always properly escape LLM-generated content in web UIs to prevent XSS attacks and indirect prompt injections.

**Grounding**: A key safety and reliability feature that connects agent responses to verifiable information.
*   **Mechanism**: Uses tools like `google_search` or `VertexAiSearchTool` to fetch real-time or private data.
*   **Benefit**: Reduces model hallucination by basing responses on retrieved facts.
*   **Requirement**: When using `google_search`, your application UI **must** display the provided search suggestions and citations to comply with terms of service.

---

## 14. Debugging, Logging & Observability

*   **`adk web` UI**: Best first step. Provides visual trace, session history, and state inspection.
*   **Event Stream Logging**: Iterate `runner.run_async()` events and print relevant fields.
    ```python
    async for event in runner.run_async(...):
        print(f"[{event.author}] Event ID: {event.id}, Invocation: {event.invocation_id}")
        if event.content and event.content.parts:
            if event.content.parts[0].text:
                print(f"  Text: {event.content.parts[0].text[:100]}...")
            if event.get_function_calls():
                print(f"  Tool Call: {event.get_function_calls()[0].name} with {event.get_function_calls()[0].args}")
            if event.get_function_responses():
                print(f"  Tool Response: {event.get_function_responses()[0].response}")
        if event.actions:
            if event.actions.state_delta:
                print(f"  State Delta: {event.actions.state_delta}")
            if event.actions.transfer_to_agent:
                print(f"  TRANSFER TO: {event.actions.transfer_to_agent}")
        if event.error_message:
            print(f"  ERROR: {event.error_message}")
    ```
*   **Tool/Callback `print` statements**: Simple logging directly within your functions.
*   **Logging**: Use Python's standard `logging` module. Control verbosity with `adk web --log_level DEBUG` or `adk web -v`.
*   **Observability Integrations**: ADK supports OpenTelemetry, enabling integration with platforms like:
    *   Google Cloud Trace
    *   AgentOps
    *   Arize AX
    *   Phoenix
    *   Weave by WandB
    ```python
    # Example using Comet Opik integration (conceptual)
    # pip install comet_opik_adk
    # from comet_opik_adk import enable_opik_tracing
    # enable_opik_tracing() # Call at app startup
    # Then run your ADK app, traces appear in Comet workspace.
    ```
*   **Session History (`session.events`)**: Persisted for detailed post-mortem analysis.

---

## 15. Streaming & Advanced I/O

ADK supports real-time, bidirectional communication for interactive experiences like live voice conversations.

*   **Bidirectional Streaming**: Enables low-latency, two-way data flow (text, audio, video) between the client and agent, allowing for interruptions.
*   **Core Components**:
    *   **`Runner.run_live()`**: The entry point for starting a streaming session.
    *   **`LiveRequestQueue`**: A queue for sending data (e.g., audio chunks) from the client to the agent during a live session.
    *   **`RunConfig`**: A configuration object passed to `run_live()` to specify modalities (`['TEXT', 'AUDIO']`), speech synthesis options, etc.
*   **Streaming Tools**: A special type of `FunctionTool` that can stream intermediate results back to the agent.
    *   **Definition**: Must be an `async` function with a return type of `AsyncGenerator`.
        ```python
        from typing import AsyncGenerator

        async def monitor_stock_price(symbol: str) -> AsyncGenerator[str, None]:
            """Yields stock price updates as they occur."""
            while True:
                price = await get_live_price(symbol)
                yield f"Update for {symbol}: ${price}"
                await asyncio.sleep(5)
        ```

*   **Advanced I/O Modalities**: ADK (especially with Gemini Live API models) supports richer interactions.
    *   **Audio**: Input via `Blob(mime_type="audio/pcm", data=bytes)`, Output via `genai_types.SpeechConfig` in `RunConfig`.
    *   **Vision (Images/Video)**: Input via `Blob(mime_type="image/jpeg", data=bytes)` or `Blob(mime_type="video/mp4", data=bytes)`. Models like `gemini-2.5-flash-exp` can process these.
    *   **Multimodal Input in `Content`**:
        ```python
        multimodal_content = genai_types.Content(
            parts=[
                genai_types.Part(text="Describe this image:"),
                genai_types.Part(inline_data=genai_types.Blob(mime_type="image/jpeg", data=image_bytes))
            ]
        )
        ```
    *   **Streaming Modalities**: `RunConfig.response_modalities=['TEXT', 'AUDIO']`.

---

## 16. Performance Optimization

*   **Model Selection**: Choose the smallest model that meets requirements (e.g., `gemini-2.5-flash` for simple tasks).
*   **Instruction Prompt Engineering**: Concise, clear instructions reduce tokens and improve accuracy.
*   **Tool Use Optimization**:
    *   Design efficient tools (fast API calls, optimize database queries).
    *   Cache tool results (e.g., using `before_tool_callback` or `tool_context.state`).
*   **State Management**: Store only necessary data in state to avoid large context windows.
*   **`include_contents='none'`**: For stateless utility agents, saves LLM context window.
*   **Parallelization**: Use `ParallelAgent` for independent tasks.
*   **Streaming**: Use `StreamingMode.SSE` or `BIDI` for perceived latency reduction.
*   **`max_llm_calls`**: Limit LLM calls to prevent runaway agents and control costs.

---

## 17. General Best Practices & Common Pitfalls

*   **Start Simple**: Begin with `LlmAgent`, mock tools, and `InMemorySessionService`. Gradually add complexity.
*   **Iterative Development**: Build small features, test, debug, refine.
*   **Modular Design**: Use agents and tools to encapsulate logic.
*   **Clear Naming**: Descriptive names for agents, tools, state keys.
*   **Error Handling**: Implement robust `try...except` blocks in tools and callbacks. Guide LLMs on how to handle tool errors.
*   **Testing**: Write unit tests for tools/callbacks, integration tests for agent flows (`pytest`, `adk eval`).
*   **Dependency Management**: Use virtual environments (`venv`) and `requirements.txt`.
*   **Secrets Management**: Never hardcode API keys. Use `.env` for local dev, environment variables or secret managers (Google Cloud Secret Manager) for production.
*   **Avoid Infinite Loops**: Especially with `LoopAgent` or complex LLM tool-calling chains. Use `max_iterations`, `max_llm_calls`, and strong instructions.
*   **Handle `None` & `Optional`**: Always check for `None` or `Optional` values when accessing nested properties (e.g., `event.content and event.content.parts and event.content.parts[0].text`).
*   **Immutability of Events**: Events are immutable records. If you need to change something *before* it's processed, do so in a `before_*` callback and return a *new* modified object.
*   **Understand `output_key` vs. direct `state` writes**: `output_key` is for the agent's *final conversational* output. Direct `tool_context.state['key'] = value` is for *any other* data you want to save.
*   **Example Agents**: Find practical examples and reference implementations in the [ADK Samples repository](https://github.com/google/adk-samples).


### Testing the output of an agent

The following script demonstrates how to programmatically test an agent's output. This approach is extremely useful when an LLM or coding agent needs to interact with a work-in-progress agent, as well as for automated testing, debugging, or when you need to integrate agent execution into other workflows:
```
import asyncio

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from app.agent import root_agent
from google.genai import types as genai_types


async def main():
    """Runs the agent with a sample query."""
    session_service = InMemorySessionService()
    await session_service.create_session(
        app_name="app", user_id="test_user", session_id="test_session"
    )
    runner = Runner(
        agent=root_agent, app_name="app", session_service=session_service
    )
    query = "I want a recipe for pancakes"
    async for event in runner.run_async(
        user_id="test_user",
        session_id="test_session",
        new_message=genai_types.Content(
            role="user", 
            parts=[genai_types.Part.from_text(text=query)]
        ),
    ):
        if event.is_final_response():
            print(event.content.parts[0].text)


if __name__ == "__main__":
    asyncio.run(main())
```

---

## 18. Official API & CLI References

For detailed specifications of all classes, methods, and commands, refer to the official reference documentation.

*   [Python API Reference](./api-reference/python/index.html)
*   [Java API Reference](./api-reference/java/index.html)
*   [CLI Reference](./api-reference/cli/index.html)
*   [REST API Reference](./api-reference/rest/index.md)
*   [Agent Config YAML Reference](./api-reference/agentconfig/index.html)

---
**llm.txt** documents the "Agent Starter Pack" repository, providing a source of truth on its purpose, features, and usage.
---

### Section 1: Project Overview

*   **Project Name:** Agent Starter Pack
*   **Purpose:** Accelerate development of production-ready GenAI Agents on Google Cloud.
*   **Tagline:** Production-Ready Agents on Google Cloud, faster.

**The "Production Gap":**
While prototyping GenAI agents is quick, production deployment often takes 3-9 months.

**Key Challenges Addressed:**
*   **Customization:** Business logic, data grounding, security/compliance.
*   **Evaluation:** Metrics, quality assessment, test datasets.
*   **Deployment:** Cloud infrastructure, CI/CD, UI integration.
*   **Observability:** Performance tracking, user feedback.

**Solution: Agent Starter Pack**
Provides MLOps and infrastructure templates so developers focus on agent logic.

*   **You Build:** Prompts, LLM interactions, business logic, agent orchestration.
*   **We Provide:**
    *   Deployment infrastructure, CI/CD, testing
    *   Logging, monitoring
    *   Evaluation tools
    *   Data connections, UI playground
    *   Security best practices

Establishes production patterns from day one, saving setup time.

---
### Section 2: Creating & Enhancing Agent Projects

Start by creating a new agent project from a predefined template, or enhance an existing project with agent capabilities. Both processes support interactive and fully automated setup.

**Prerequisites:**
Before you begin, ensure you have `uv`/`uvx`, `gcloud` CLI, `terraform`, `git`, and `gh` CLI (for automated CI/CD setup) installed and authenticated.

**Installing the `agent-starter-pack` CLI:**
Choose one method to get the `agent-starter-pack` command:

1.  **`uvx` (Recommended for Zero-Install/Automation):** Run directly without prior installation.
    ```bash
    uvx agent-starter-pack create ...
    ```
2.  **Virtual Environment (`pip` or `uv`):**
    ```bash
    pip install agent-starter-pack
    ```
3.  **Persistent CLI Install (`pipx` or `uv tool`):** Installs globally in an isolated environment.

---
### `agent-starter-pack create` Command

Generates a new agent project directory based on a chosen template and configuration.

**Usage:**
```bash
agent-starter-pack create PROJECT_NAME [OPTIONS]
```

**Arguments:**
*   `PROJECT_NAME`: Name for your new project directory and base for GCP resource naming (max 26 chars, converted to lowercase).

**Template Selection:**
*   `-a, --agent`: Agent template - built-in agents (e.g., `adk_base`, `agentic_rag`), remote templates (`adk@gemini-fullstack`, `github.com/user/repo@branch`), or local projects (`local@./path`).

**Deployment Options:**
*   `-d, --deployment-target`: Target environment (`cloud_run` or `agent_engine`).
*   `--cicd-runner`: CI/CD runner (`google_cloud_build` or `github_actions`).
*   `--region`: GCP region (default: `us-central1`).

**Data & Storage:**
*   `-i, --include-data-ingestion`: Include data ingestion pipeline.
*   `-ds, --datastore`: Datastore type (`vertex_ai_search`, `vertex_ai_vector_search`, `alloydb`).
*   `--session-type`: Session storage (`in_memory`, `alloydb`, `agent_engine`).

**Project Creation:**
*   `-o, --output-dir`: Output directory (default: current directory).
*   `--agent-directory, -dir`: Agent code directory name (default: `app`).
*   `--in-folder`: Create files in current directory instead of new subdirectory.

**Automation:**
*   `--auto-approve`: **Skip all interactive prompts (crucial for automation).**
*   `--skip-checks`: Skip GCP/Vertex AI verification checks.
*   `--debug`: Enable debug logging.

**Automated Creation Example:**
```bash
uvx agent-starter-pack create my-automated-agent \
  -a adk_base \
  -d cloud_run \
  --region us-central1 \
  --auto-approve
```

---

### `agent-starter-pack enhance` Command

Enhance your existing project with AI agent capabilities by adding agent-starter-pack features in-place. This command supports all the same options as `create` but templates directly into the current directory instead of creating a new project directory.

**Usage:**
```bash
agent-starter-pack enhance [TEMPLATE_PATH] [OPTIONS]
```

**Key Differences from `create`:**
*   Templates into current directory (equivalent to `create --in-folder`)
*   `TEMPLATE_PATH` defaults to current directory (`.`)
*   Project name defaults to current directory name
*   Additional `--base-template` option to override template inheritance

**Enhanced Project Example:**
```bash
# Enhance current directory with agent capabilities
uvx agent-starter-pack enhance . \
  --base-template adk_base \
  -d cloud_run \
  --region us-central1 \
  --auto-approve
```

**Project Structure:** Expects agent code in `app/` directory (configurable via `--agent-directory`).

---

### Available Agent Templates

Templates for the `create` command (via `-a` or `--agent`):

| Agent Name             | Description                                  |
| :--------------------- | :------------------------------------------- |
| `adk_base`             | Base ReAct agent (ADK)                       |
| `adk_gemini_fullstack` | Production-ready fullstack research agent    |
| `agentic_rag`          | RAG agent for document retrieval & Q&A       |
| `langgraph_base_react` | Base ReAct agent (LangGraph)                 |
| `crewai_coding_crew`   | Multi-agent collaborative coding assistance  |
| `live_api`             | Real-time multimodal RAG agent               |

---

### Including a Data Ingestion Pipeline (for RAG agents)

For RAG agents needing custom document search, enabling this option automates loading, chunking, embedding documents with Vertex AI, and storing them in a vector database.

**How to enable:**
```bash
uvx agent-starter-pack create my-rag-agent \
  -a agentic_rag \
  -d cloud_run \
  -i \
  -ds vertex_ai_search \
  --auto-approve
```
**Post-creation:** Follow your new project's `data_ingestion/README.md` to deploy the necessary infrastructure.

---
### Section 3: Development & Automated Deployment Workflow
---

This section describes the end-to-end lifecycle of an agent, with emphasis on automation.


### 1. Local Development & Iteration

Once your project is created, navigate into its directory to begin development.

**First, install dependencies (run once):**
```bash
make install
```

**Next, test your agent. The recommended method is to use a programmatic script.**

#### Programmatic Testing (Recommended Workflow)

This method allows for quick, automated validation of your agent's logic.

1.  **Create a script:** In the project's root directory, create a Python script named `run_agent.py`.
2.  **Invoke the agent:** In the script, write code to programmatically call your agent with sample input and `print()` the output for inspection.
    *   **Guidance:** If you're unsure or no guidance exists, you can look at files in the `tests/` directory for examples of how to import and call the agent's main function.
    *   **Important:** This script is for simple validation. **Assertions are not required**, and you should not create a formal `pytest` file.
3.  **Run the test:** Execute your script from the terminal using `uv`.
    ```bash
    uv run python run_agent.py
    ```
You can keep the test file for future testing.

#### Manual Testing with the UI Playground (Optional)

If the user needs to interact with your agent manually in a chat interface for debugging:

1.  Run the following command to start the local web UI:
    ```bash
    make playground
    ```
    This is useful for human-in-the-loop testing and features hot-reloading.

### 2. Deploying to a Cloud Development Environment
Before setting up full CI/CD, you can deploy to a personal cloud dev environment.

1.  **Set Project:** `gcloud config set project YOUR_DEV_PROJECT_ID`
2.  **Provision Resources:** `make setup-dev-env` (uses Terraform).
3.  **Deploy Backend:** `make backend` (builds and deploys the agent).

### 3. Automated Production-Ready Deployment with CI/CD
For reliable deployments, the `setup-cicd` command streamlines the entire process. It creates a GitHub repo, connects it to your chosen CI/CD runner (Google Cloud Build or GitHub Actions), provisions staging/prod infrastructure, and configures deployment triggers.

**Automated CI/CD Setup Example (Recommended):**
```bash
# Run from the project root. This command will guide you or can be automated with flags.
uvx agent-starter-pack setup-cicd
```

**CI/CD Workflow Logic:**
*   **On Pull Request:** CI pipeline runs tests.
*   **On Merge to `main`:** CD pipeline deploys to staging.
*   **Manual Approval:** A manual approval step triggers the production deployment.

---
### Section 4: Key Features & Customization
---

### Deploying with a User Interface (UI)
*   **Unified Deployment (for Dev/Test):** The backend and frontend can be packaged and served from a single Cloud Run service, secured with Identity-Aware Proxy (IAP).
*   **Deploying with UI:** `make backend IAP=true`
*   **Access Control:** After deploying with IAP, grant users the `IAP-secured Web App User` role in IAM to give them access.

### Session Management

For stateful agents, the starter pack supports persistent sessions.
*   **Cloud Run:** Choose between `in_memory` (for testing) and durable `alloydb` sessions using the `--session-type` flag.
*   **Agent Engine:** Provides session management automatically.

### Monitoring & Observability
*   **Technology:** Uses OpenTelemetry to emit events to Google Cloud Trace and Logging.
*   **Custom Tracer:** A custom tracer in `app/utils/tracing.py` (or a different agent directory instead of app) handles large payloads by linking to GCS, overcoming default service limits.
*   **Infrastructure:** A Log Router to sink data to BigQuery is provisioned by Terraform.

---
### Section 5: CLI Reference for CI/CD Setup
---

### `agent-starter-pack setup-cicd`
Automates the complete CI/CD infrastructure setup for GitHub-based deployments. Intelligently detects your CI/CD runner (Google Cloud Build or GitHub Actions) and configures everything automatically.

**Usage:**
```bash
uvx agent-starter-pack setup-cicd [OPTIONS]
```

**Prerequisites:** 
- Run from the project root (directory with `pyproject.toml`)
- Required tools: `gh` CLI (authenticated), `gcloud` CLI (authenticated), `terraform`
- `Owner` role on GCP projects
- GitHub token with `repo` and `workflow` scopes

**Key Options:**
*   `--staging-project`, `--prod-project`: GCP project IDs (will prompt if omitted).
*   `--repository-name`, `--repository-owner`: GitHub repo details (will prompt if omitted).
*   `--cicd-project`: CI/CD resources project (defaults to prod project).
*   `--dev-project`: Development project ID (optional).
*   `--region`: GCP region (default: `us-central1`).
*   `--auto-approve`: Skip all interactive prompts.
*   `--local-state`: Use local Terraform state instead of GCS backend.
*   `--debug`: Enable debug logging.

**What it does:**
1. Creates/connects GitHub repository
2. Sets up Terraform infrastructure with remote state
3. Configures CI/CD runner connection (Cloud Build or GitHub Actions with WIF)
4. Provisions staging/prod environments
5. Sets up local Git repository with origin remote

**Automated Example:**
```bash
uvx agent-starter-pack setup-cicd \
  --staging-project your-staging-project \
  --prod-project your-prod-project \
  --repository-name your-repo-name \
  --repository-owner your-username \
  --auto-approve
```

**After setup, push to trigger pipeline:**
```bash
git add . && git commit -m "Initial commit" && git push -u origin main
```

* Note: For coding agents - ask user for required project IDs and repo details before running with `--auto-approve`.
* Note: If user prefers different git provider, refer to `deployment/README.md` for manual deployment.
---
### Section 6: Operational Guidelines for Coding Agents

These guidelines are essential for interacting with the Agent Starter Pack project effectively.

---

### Principle 1: Code Preservation & Isolation

When executing code modifications using tools like `replace` or `write_file`, your paramount objective is surgical precision. You **must alter only the code segments directly targeted** by the user's request, while **strictly preserving all surrounding and unrelated code.**

**Mandatory Pre-Execution Verification:**

Before finalizing any `new_string` for a `replace` operation, meticulously verify the following:

1.  **Target Identification:** Clearly define the exact lines or expressions to be changed, based *solely* on the user's explicit instructions.
2.  **Preservation Check:** Compare your proposed `new_string` against the `old_string`. Ensure all code, configuration values (e.g., `model`, `version`, `api_key`), comments, and formatting *outside* the identified target remain identical and verbatim.

**Example: Adhering to Preservation**

*   **User Request:** "Change the agent's instruction to be a recipe suggester."
*   **Original Code Snippet:**
    ```python
    root_agent = Agent(
        name="root_agent",
        model="gemini-2.5-flash",
        instruction="You are a helpful AI assistant."
    )
    ```
*   **Incorrect Modification (VIOLATION):**
    ```python
    root_agent = Agent(
        name="recipe_suggester",
        model="gemini-1.5-flash", # UNINTENDED MUTATION - model was not requested to change
        instruction="You are a recipe suggester."
    )
    ```
*   **Correct Modification (COMPLIANT):**
    ```python
    root_agent = Agent(
        name="recipe_suggester", # OK, related to new purpose
        model="gemini-2.5-flash", # MUST be preserved
        instruction="You are a recipe suggester." # OK, the direct target
    )
    ```

**Critical Error:** Failure to adhere to this preservation principle is a critical error. Always prioritize the integrity of existing, unchanged code over the convenience of rewriting entire blocks.

---

### Principle 2: Workflow & Execution Best Practices

*   **Standard Workflow:**
    The validated end-to-end process is: `create` → `test` → `setup-cicd` → push to deploy. Trust this high-level workflow as the default for developing and shipping agents.

*   **Agent Testing:**
    *   **Avoid `make playground`** unless specifically instructed; it is designed for human interaction. Focus on programmatic testing.

*   **Model Selection:**
    *   **When using Gemini, prefer the 2.5 model family** for optimal performance and capabilities: "gemini-2.5-pro" and "gemini-2.5-flash"

*   **Running Python Commands:**
    *   Always use `uv` to execute Python commands within this repository (e.g., `uv run run_agent.py`).
    *   Ensure project dependencies are installed by running `make install` before executing scripts.
    *   Consult the project's `Makefile` and `README.md` for other useful development commands.

*   **Further Reading & Troubleshooting:**
    *   For questions about specific frameworks (e.g., LangGraph) or Google Cloud products (e.g., Cloud Run), their official documentation and online resources are the best source of truth.
    *   **When encountering persistent errors or if you're unsure how to proceed after initial troubleshooting, a targeted Google Search is strongly recommended.** It is often the fastest way to find relevant documentation, community discussions, or direct solutions to your problem.
