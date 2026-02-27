# ADK Evaluation Guide

This guide covers the evaluation loop for ADK agents — metrics, evalsets, LLM-as-judge configuration, and critical gotchas.

---

## The Evaluation Loop (Main Iteration Phase)

This is where most iteration happens. Work with the user to:

1. **Start small**: Begin with 1-2 sample eval cases, not a full suite
2. Run evaluations: `make eval`
3. Discuss results with the user
4. Fix issues and iterate on the core cases first
5. Only after core cases pass, add edge cases and new scenarios
6. Adjust prompts, tools, or agent logic based on results
7. Repeat until quality thresholds are met

**Why start small?** Too many eval cases at the beginning creates noise. Get 1-2 core cases passing first to validate your agent works, then expand coverage.

```bash
make eval
```

Review the output:
- `tool_trajectory_avg_score`: Are the right tools called in order?
- `response_match_score`: Do responses match expected patterns?

**Expect 5-10+ iterations here** as you refine the agent with the user.

---

## LLM-as-a-Judge Evaluation (Recommended)

For high-quality evaluations, use LLM-based metrics that judge response quality semantically.

**Running with custom config:**
```bash
uv run adk eval ./app <path_to_evalset.json> --config_file_path=<path_to_config.json>
```

Or use the Makefile:
```bash
make eval EVALSET=tests/eval/evalsets/my_evalset.json
```

### Configuration Schema (`test_config.json`)

**CRITICAL:** The JSON configuration for rubrics **must use camelCase** (not snake_case).

```json
{
  "criteria": {
    "tool_trajectory_avg_score": 1.0,
    "final_response_match_v2": 0.8,
    "rubric_based_final_response_quality_v1": {
      "threshold": 0.8,
      "rubrics": [
        {
          "rubricId": "professionalism",
          "rubricContent": { "textProperty": "The response must be professional and helpful." }
        },
        {
          "rubricId": "safety",
          "rubricContent": { "textProperty": "The agent must NEVER book without asking for confirmation." }
        }
      ]
    }
  }
}
```

### EvalSet Schema (`evalset.json`)

```json
{
  "eval_set_id": "my_eval_set",
  "eval_cases": [
    {
      "eval_id": "search_test",
      "conversation": [
        {
          "user_content": { "parts": [{ "text": "Find a flight to NYC" }] },
          "final_response": {
            "role": "model",
            "parts": [{ "text": "I found a flight for $500. Want to book?" }]
          },
          "intermediate_data": {
            "tool_uses": [
              { "name": "search_flights", "args": { "destination": "NYC" } }
            ]
          }
        }
      ],
      "session_input": { "app_name": "<your-agent-directory>", "user_id": "user_1", "state": {} }
    }
  ]
}
```

---

## Key Metrics

| Metric | Purpose |
|--------|---------|
| `tool_trajectory_avg_score` | Ensures the right tools were called in the right order |
| `final_response_match_v2` | Uses LLM to check if agent's answer matches ground truth semantically |
| `rubric_based_final_response_quality_v1` | Judges agent against custom rules (tone, safety, confirmation) |
| `hallucinations_v1` | Ensures agent's response is grounded in tool output |

For complete metric definitions, see: `site-packages/google/adk/evaluation/eval_metrics.py`

---

## Rubrics vs Semantic Matches

For complex outputs like executive digests or multi-part responses, `final_response_match_v2` is often too sensitive. `rubric_based_final_response_quality_v1` is far superior because it judges specific qualities (tone, citations, strategic relevance) rather than comparing against a static string.

---

## The Proactivity Trajectory Gap

LLMs are often "too helpful" and will perform extra actions. For example, an agent might call `google_search` immediately after `save_preferences` even when not asked. This causes `tool_trajectory_avg_score` failures. Solutions:
- Include ALL tools the agent might call in your expected trajectory
- Use extremely strict instructions: "Stop after calling save_preferences. Do NOT search."
- Use rubric-based evaluation instead of trajectory matching

---

## Multi-Turn Conversations

The `tool_trajectory_avg_score` uses EXACT matching. If you don't specify expected tool calls for intermediate turns, the evaluation will fail even if the agent called the right tools.

**You must provide `tool_uses` for ALL turns:**

```json
{
  "conversation": [
    {
      "invocation_id": "inv_1",
      "user_content": { "parts": [{"text": "Find me a flight from NYC to London on 2026-06-01"}] },
      "intermediate_data": {
        "tool_uses": [
          { "name": "search_flights", "args": {"origin": "NYC", "destination": "LON", "departure_date": "2026-06-01"} }
        ]
      }
    },
    {
      "invocation_id": "inv_2",
      "user_content": { "parts": [{"text": "Book the first option for Elias (elias@example.com)"}] },
      "intermediate_data": {
        "tool_uses": [
          { "name": "get_flight_price", "args": {"flight_offer": {"id": "1", "price": {"total": "500.00"}}} }
        ]
      }
    },
    {
      "invocation_id": "inv_3",
      "user_content": { "parts": [{"text": "Yes, confirm the booking"}] },
      "final_response": { "role": "model", "parts": [{"text": "Booking confirmed! Reference: ABC123"}] },
      "intermediate_data": {
        "tool_uses": [
          { "name": "book_flight", "args": {"passenger_name": "Elias", "email": "elias@example.com"} }
        ]
      }
    }
  ]
}
```

---

## Common Eval Failure Causes

- Missing `tool_uses` in intermediate turns -> trajectory score fails
- Agent mentions data not in tool output -> `hallucinations_v1` fails
- Response not explicit enough -> `rubric_based` score drops

---

## The `before_agent_callback` Pattern (State Initialization)

Always use a callback to initialize session state variables used in your instruction template (like `{user_preferences}`). This prevents `KeyError` crashes on the first turn before the user has provided data:

```python
async def initialize_state(callback_context: CallbackContext) -> None:
    """Initialize session state with defaults if not present."""
    state = callback_context.state
    if "user_preferences" not in state:
        state["user_preferences"] = {}
    if "feedback_history" not in state:
        state["feedback_history"] = []

root_agent = Agent(
    name="my_agent",
    before_agent_callback=initialize_state,
    instruction="Based on preferences: {user_preferences}...",
    ...
)
```

---

## Eval-State Overrides (Type Mismatch Danger)

Be careful with `session_input.state` in your evalset.json. It overrides Python-level initialization and can introduce type errors:

```json
// WRONG - initializes feedback_history as a string, breaks .append()
"state": { "feedback_history": "" }

// CORRECT - matches the Python type (list)
"state": { "feedback_history": [] }
```

This can cause cryptic errors like `AttributeError: 'str' object has no attribute 'append'` in your tool logic.

---

## Evaluation Gotchas

### App name must match directory name

The `App` object's `name` parameter MUST match the directory containing your agent. If your agent is in the `app/` directory, use `name="app"`:

```python
# CORRECT - matches the "app" directory
app = App(root_agent=root_agent, name="app")

# WRONG - causes "Session not found" errors
app = App(root_agent=root_agent, name="flight_booking_assistant")
```

If names don't match, you'll get: `Session not found... The runner is configured with app name "X", but the root agent was loaded from ".../app"`

---

## Evaluating Agents with `google_search` (IMPORTANT)

`google_search` is NOT a regular tool - it's a **model-internal grounding feature**:

```python
# How google_search works internally:
llm_request.config.tools.append(
    types.Tool(google_search=types.GoogleSearch())  # Injected into model config
)
```

**Key behavior:**
- Custom tools (`save_preferences`, `save_feedback`) -> appear as `function_call` in trajectory
- `google_search` -> NEVER appears in trajectory (happens inside the model)
- Search results come back as `grounding_metadata`, not function call/response events

**BUT the evaluator STILL detects it** at the session level:
```json
{
  "error_code": "UNEXPECTED_TOOL_CALL",
  "error_message": "Unexpected tool call: google_search"
}
```

This causes `tool_trajectory_avg_score` to ALWAYS fail for agents using `google_search`.

### Metric compatibility for `google_search` agents

| Metric | Usable? | Why |
|--------|---------|-----|
| `tool_trajectory_avg_score` | NO | Always fails due to unexpected google_search |
| `response_match_score` | Maybe | Unreliable for dynamic news content |
| `rubric_based_final_response_quality_v1` | YES | Evaluates output quality semantically |
| `final_response_match_v2` | Maybe | Works for stable expected outputs |

### Evalset best practices for `google_search` agents

```json
{
  "eval_id": "news_digest_test",
  "conversation": [{
    "user_content": { "parts": [{"text": "Give me my news digest."}] }
    // NO intermediate_data.tool_uses for google_search - it won't match anyway
  }]
}
```

For custom tools alongside google_search, still include them (but NOT google_search):
```json
{
  "intermediate_data": {
    "tool_uses": [
      { "name": "save_feedback" }  // Custom tools work fine
      // Do NOT include google_search here
    ]
  }
}
```

### Config for `google_search` agents

```json
{
  "criteria": {
    // REMOVE this - incompatible with google_search:
    // "tool_trajectory_avg_score": 1.0,

    // Use rubric-based evaluation instead:
    "rubric_based_final_response_quality_v1": {
      "threshold": 0.6,
      "rubrics": [
        { "rubricId": "has_citations", "rubricContent": { "textProperty": "Response includes source citations or references" } },
        { "rubricId": "relevance", "rubricContent": { "textProperty": "Response directly addresses the user's query" } }
      ]
    }
  }
}
```

**Bottom line:** `google_search` is a model feature, not a function tool. You cannot test it with trajectory matching. Use rubric-based LLM-as-judge evaluation to verify the agent produces grounded, cited responses.

---

## ADK Built-in Tools: Trajectory Behavior Reference

This applies to ALL Gemini model-internal tools, not just `google_search`:

### Model-Internal Tools (DON'T appear in trajectory)

| Tool | Type | In Trajectory? | Eval Strategy |
|------|------|----------------|---------------|
| `google_search` | `types.GoogleSearch()` | No | Rubric-based |
| `google_search_retrieval` | `types.GoogleSearchRetrieval()` | No | Rubric-based |
| `BuiltInCodeExecutor` | `types.CodeExecution()` | No | Check output |
| `VertexAiSearchTool` | `types.Retrieval()` | No | Rubric-based |
| `url_context` | Model-internal | No | Rubric-based |

These inject into `llm_request.config.tools` as model capabilities:
```python
types.Tool(google_search=types.GoogleSearch())
types.Tool(code_execution=types.ToolCodeExecution())
types.Tool(retrieval=types.Retrieval(...))
```

### Function-Based Tools (DO appear in trajectory)

| Tool | Type | In Trajectory? | Eval Strategy |
|------|------|----------------|---------------|
| `load_web_page` | FunctionTool | Yes | `tool_trajectory_avg_score` works |
| Custom tools | FunctionTool | Yes | `tool_trajectory_avg_score` works |
| AgentTool | Wrapped agent | Yes | `tool_trajectory_avg_score` works |

These generate `function_call` and `function_response` events:
```python
types.Tool(function_declarations=[...])
```

### Quick Reference - Can I use `tool_trajectory_avg_score`?

- `google_search` -> NO (model-internal)
- `code_executor` -> NO (model-internal)
- `VertexAiSearchTool` -> NO (model-internal)
- `load_web_page` -> YES (FunctionTool)
- Custom functions -> YES (FunctionTool)

**Rule of Thumb:**
- If a tool provides grounding/retrieval/execution capabilities built into Gemini -> model-internal, won't appear in trajectory
- If it's a Python function you can call -> appears in trajectory, can test with `tool_trajectory_avg_score`

**When mixing both types** (e.g., `google_search` + `save_preferences`):
1. Remove `tool_trajectory_avg_score` entirely, OR
2. Only test function-based tools in `tool_uses` and accept the trajectory will be incomplete

---

## Additional Gotchas

**Model thinking mode may bypass tools:**
Models with "thinking" enabled may decide they have sufficient information and skip tool calls. Use `tool_config` with `mode="ANY"` to force tool usage, or switch to a non-thinking model like `gemini-2.0-flash` for predictable tool calling.

**Sub-agents need instances, not function references:**
When using multi-agent systems with `sub_agents`, you must pass **Agent instances**, not factory function references.

```python
# WRONG - This fails with ValidationError
sub_agents=[
    create_lead_qualifier,   # Function reference - FAILS!
    create_product_matcher,  # Function reference - FAILS!
]

# CORRECT - Call the factories to get instances
sub_agents=[
    create_lead_qualifier(),   # Instance - WORKS
    create_product_matcher(),  # Instance - WORKS
]
```

**Root cause**: ADK's pydantic validation expects `BaseAgent` instances, not callables. The error message is:
`ValidationError: Input should be a valid dictionary or instance of BaseAgent`

When using `SequentialAgent` with sub-agents that may be reused, create each sub-agent via a factory function (not module-level instances) to avoid "agent already has a parent" errors:

```python
def create_researcher():
    return Agent(name="researcher", ...)

root_agent = SequentialAgent(
    sub_agents=[create_researcher(), create_analyst()],  # Note: calling the functions!
    ...
)
```

**A2A handoffs pass data between agents:**
When using multi-agent systems (SequentialAgent), data flows between sub-agents through the conversation history and context. To ensure proper handoffs:

```python
# Lead Qualifier agent should include score in response
def create_lead_qualifier():
    return Agent(
        name="lead_qualifier",
        instruction="Score leads 1-100. ALWAYS include the score in your response: 'Lead score: XX/100'",
        ...
    )

# Product Matcher receives the score via conversation context
def create_product_matcher():
    return Agent(
        name="product_matcher",
        instruction="Recommend products based on the lead score from the previous agent.",
        ...
    )
```

Verify handoffs in eval by checking that sub-agents reference data from previous agents in their responses.

---

## Mock Mode for External APIs

When your agent calls external APIs, add mock mode so evals can run without real credentials:
```python
def call_external_api(query: str) -> dict:
    api_key = os.environ.get("EXTERNAL_API_KEY", "")
    if not api_key or api_key == "dummy_key":
        return {"status": "success", "data": "mock_response"}
    # Real API call here
```

---

## Session Persistence Testing (Cloud SQL)

When using Cloud SQL for sessions, add test cases that verify session resume functionality:

```json
{
  "test_case": "session_resume",
  "description": "Verify agent remembers context from previous conversation",
  "steps": [
    {
      "input": "Qualify lead #123",
      "expected_response_contains": ["score", "qualified"]
    },
    {
      "input": "What products did you recommend for this lead?",
      "new_session": false,
      "expected_response_contains": ["products", "lead #123"]
    }
  ]
}
```

Key testing principles:
- Test same session_id across multiple requests
- Verify agent recalls previous conversation details
- Test session isolation (different session_id = no shared context)
- Verify database persistence survives service restarts

---

## Adding Evaluation Cases

To improve evaluation coverage:

1. Add cases to `tests/eval/evalsets/basic.evalset.json`
2. Each case should test a core capability of your agent
3. Include expected tool calls in `intermediate_data.tool_uses`
4. Run `make eval` to verify

---

## Data Ingestion (RAG Agents)

**CRITICAL**: Before deploying a RAG agent, you MUST ingest data into the vector store.

### Data Ingestion Setup

1. **Prepare Sample Documents**: Create or obtain 3-5 sample documents relevant to your agent's domain (PDFs, text files, etc.)
2. **Upload to GCS**: Place documents in a GCS bucket
3. **Set Up Infrastructure**: Run `make setup-dev-env` to provision the vector store (Vertex AI Search or Vector Search)
4. **Run Data Ingestion**: Execute `make data-ingestion` to process and index documents

```bash
# Example workflow
make setup-dev-env  # Provisions vector store infrastructure
make data-ingestion # Processes documents and creates embeddings
```

### Data Ingestion Best Practices

- **Test with Real Data**: Use documents representative of production data
- **Verify Indexing**: After ingestion, test retrieval with sample queries via `make playground`
- **Citation Format**: Ensure your agent includes document sources in responses (e.g., "[Document Name, p.3]")
- **Chunking Strategy**: Default is 512 tokens with 50-token overlap; adjust in `data_ingestion/` if needed
- **Wait for Indexing**: Vector stores may take 2-5 minutes to fully index after ingestion

### RAG-Specific Evaluation Criteria

When evaluating RAG agents, add these additional test cases:

- **Citation Accuracy**: Responses include correct document references
- **Out-of-Scope Handling**: Agent refuses questions outside indexed knowledge
- **Multi-Document Synthesis**: Agent combines information from multiple sources
- **No Results Found**: Agent admits when no relevant documents exist

See `tests/eval/evalsets/basic.evalset.json` for examples.
