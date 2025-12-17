# CrewAI Agent Template Implementation Plan

**Project**: Add CrewAI-based agent template to Agent Starter Pack
**Target Agent Name**: `crewai_base`
**Date**: 2025-12-17
**Status**: ✅ IMPLEMENTATION COMPLETE - Ready for Testing

## ✅ Implementation Summary

All core files have been successfully created:
- `.template/templateconfig.yaml` - Agent configuration with CrewAI 1.7+ dependencies
- `app/__init__.py` - Package initialization exporting `root_agent`
- `app/agent.py` - Main CrewAI agent with Google Custom Search integration
- `tests/integration/test_agent.py` - Comprehensive integration tests
- `README.md` - Complete documentation
- `notebooks/crewai_local_example.ipynb` - Simple local testing notebook
- `notebooks/evaluating_crewai_agent.ipynb` - Agent evaluation notebook

**Key Implementation Choices:**
- Using Google Custom Search API (with mock fallback for testing)
- Simplified design (no A2A protocol, no complex dependencies)
- Frontend type: "None" (no UI)
- Vertex AI Gemini 2.0 Flash via LiteLLM
- Compatible with both cloud_run and agent_engine deployments

---

## 🎯 Implementation Goals

Create a new agent template that:
- Uses CrewAI framework with single agent architecture
- Integrates with Google Vertex AI Gemini models
- Includes web search tool capability
- Follows existing Agent Starter Pack patterns
- Requires zero modifications to existing CLI code
- Supports both `cloud_run` and `agent_engine` deployment targets

---

## 📋 User Requirements

Based on user input:
1. ✅ **Simple agent** - Single agent, minimal complexity
2. ✅ **Web search tool** - Primary tool for the agent
3. ✅ **Integration depth** - Follow patterns from adk_base/langgraph_base
4. ✅ **Example query** - Showcase web search capability
5. ✅ **Single agent design** - No multi-agent crews

---

## 📁 Directory Structure to Create

```
agent_starter_pack/agents/crewai_base/
├── .template/
│   └── templateconfig.yaml          # Agent configuration for CLI
├── app/
│   ├── __init__.py                  # Package initialization
│   └── agent.py                     # Main CrewAI agent implementation
├── notebooks/
│   ├── evaluating_crewai_agent.ipynb   # Vertex AI evaluation notebook
│   └── crewai_local_example.ipynb      # Simple local testing notebook
├── tests/
│   └── integration/
│       └── test_agent.py            # Integration tests
└── README.md                        # Agent documentation
```

**Total New Files**: 7 files
**Modified Files**: 0 files

---

## 📝 Detailed Implementation Tasks

### TASK 1: Create Base Directory Structure

**Command**:
```bash
mkdir -p agent_starter_pack/agents/crewai_base/.template
mkdir -p agent_starter_pack/agents/crewai_base/app
mkdir -p agent_starter_pack/agents/crewai_base/notebooks
mkdir -p agent_starter_pack/agents/crewai_base/tests/integration
```

**Expected Result**: Empty directory structure created

**Verification**:
```bash
ls -la agent_starter_pack/agents/crewai_base/
# Should show: .template/, app/, notebooks/, tests/
```

---

### TASK 2: Create `.template/templateconfig.yaml`

**File**: `agent_starter_pack/agents/crewai_base/.template/templateconfig.yaml`

**Content**:
```yaml
description: "A ReAct agent built with CrewAI framework and web search capabilities"
example_question: "What are the latest developments in generative AI agents?"
settings:
  requires_data_ingestion: false
  requires_session: false
  deployment_targets: ["agent_engine", "cloud_run"]
  extra_dependencies:
    - "crewai>=0.80.0,<1.0.0"
    - "crewai-tools>=0.12.0,<1.0.0"
    - "langchain-google-vertexai>=2.0.0,<3.0.0"
    - "google-cloud-aiplatform>=1.120.0"
  tags: ["crewai"]
  frontend_type: "None"
```

**Key Configuration Decisions**:
- `requires_data_ingestion: false` - No RAG needed for web search
- `requires_session: false` - Stateless like langgraph_base
- `crewai-tools` - Provides built-in web search tool (SerperDevTool, etc.)
- `deployment_targets`: Both cloud_run and agent_engine
- `tags: ["crewai"]` - For filtering and identification

**Verification**:
```bash
cat agent_starter_pack/agents/crewai_base/.template/templateconfig.yaml
# Should display valid YAML
```

---

### TASK 3: Create `app/__init__.py`

**File**: `agent_starter_pack/agents/crewai_base/app/__init__.py`

**Content**:
```python
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

"""CrewAI agent implementation."""
```

**Purpose**: Standard Python package initialization with Apache license

**Verification**: File exists and has proper copyright header

---

### TASK 4: Create `app/agent.py` (Core Implementation)

**File**: `agent_starter_pack/agents/crewai_base/app/agent.py`

**Content Sections**:

#### Section 1: Imports and Environment Setup
```python
# Copyright 2025 Google LLC
# [Full license header...]

"""CrewAI agent with web search capabilities."""

import os
from datetime import datetime
from typing import Any

import google.auth
from crewai import Agent, Crew, Process, Task
from crewai.llm import LLM
from crewai_tools import SerperDevTool

# Set up Google Cloud environment for Vertex AI
try:
    credentials, project_id = google.auth.default()
    if project_id:
        os.environ["GOOGLE_CLOUD_PROJECT"] = project_id
        os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"
except Exception as e:
    print(f"Warning: Could not set up Google Cloud auth: {e}")
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "")
```

#### Section 2: Tool Definitions
```python
# Initialize web search tool
# Note: SerperDevTool requires SERPER_API_KEY environment variable
search_tool = SerperDevTool()


def get_current_time(timezone: str = "UTC") -> str:
    """Get the current time.

    Args:
        timezone: The timezone (currently returns UTC).

    Returns:
        The current time as a formatted string.
    """
    current_time = datetime.now()
    return f"The current time is {current_time.strftime('%Y-%m-%d %I:%M %p')} {timezone}."
```

**Alternative** (if SerperDevTool requires paid API):
```python
# Fallback: Simple mock web search tool for development
def web_search(query: str) -> str:
    """Search the web for information (mock implementation).

    Args:
        query: The search query.

    Returns:
        Mock search results.
    """
    return f"Mock search results for: {query}\n\nThis is a placeholder. Configure SERPER_API_KEY for real web search."
```

#### Section 3: LLM Configuration
```python
# Configure LLM to use Vertex AI Gemini
llm = LLM(
    model="gemini/gemini-2.0-flash-exp",
    temperature=0.7,
)
```

#### Section 4: Agent Definition
```python
# Create CrewAI agent with web search capabilities
research_agent = Agent(
    role="Research Assistant",
    goal="Help users find information and answer questions using web search",
    backstory=(
        "You are a knowledgeable AI research assistant with access to web search. "
        "You provide accurate, up-to-date information by searching the web and "
        "synthesizing results into clear, concise answers."
    ),
    tools=[search_tool, get_current_time],  # or [web_search, get_current_time]
    llm=llm,
    verbose=True,
    allow_delegation=False,
)
```

#### Section 5: Crew Creation and Execution
```python
def create_crew(user_query: str) -> Crew:
    """Create a crew to handle a user query.

    Args:
        user_query: The user's question or request.

    Returns:
        A configured Crew instance.
    """
    task = Task(
        description=user_query,
        expected_output="A comprehensive answer based on web search results",
        agent=research_agent,
    )

    crew = Crew(
        agents=[research_agent],
        tasks=[task],
        process=Process.sequential,
        verbose=True,
    )

    return crew


def run_agent(query: str) -> str:
    """Run the CrewAI agent with a user query.

    Args:
        query: The user's question or request.

    Returns:
        The agent's response.
    """
    crew = create_crew(query)
    result = crew.kickoff()

    # CrewAI returns a CrewOutput object; extract the text
    if hasattr(result, 'raw'):
        return result.raw
    return str(result)
```

#### Section 6: Deployment Wrapper
```python
# For compatibility with Agent Starter Pack deployment patterns
class CrewAIApp:
    """Wrapper class for CrewAI agent to match ASP deployment patterns."""

    def __init__(self):
        self.name = "{{cookiecutter.agent_directory}}"

    def run(self, query: str) -> str:
        """Run the agent with a query."""
        return run_agent(query)


# Create app instance
app = CrewAIApp()
```

#### Section 7: Main Entry Point
```python
# For testing
if __name__ == "__main__":
    test_query = "{{cookiecutter.example_question}}"
    print(f"Query: {test_query}")
    response = run_agent(test_query)
    print(f"Response: {response}")
```

**Key Implementation Details**:
- Uses `{{cookiecutter.agent_directory}}` for templating
- Follows Vertex AI authentication pattern from other agents
- Includes `CrewAIApp` wrapper for deployment compatibility
- Uses `SerperDevTool` for real web search (or mock for development)
- Single agent design with sequential process

**Verification**:
```bash
# Check syntax
python -m py_compile agent_starter_pack/agents/crewai_base/app/agent.py

# Test locally (after creating project)
cd target/test-project
python -m app.agent
```

---

### TASK 5: Create Integration Tests

**File**: `agent_starter_pack/agents/crewai_base/tests/integration/test_agent.py`

**Content**:
```python
# Copyright 2025 Google LLC
# [Full license header...]

"""Integration tests for CrewAI agent."""

import pytest

from {{cookiecutter.agent_directory}}.agent import (
    create_crew,
    get_current_time,
    run_agent,
)


def test_get_current_time():
    """Test time tool."""
    result = get_current_time()
    assert "current time" in result.lower()
    assert "UTC" in result


def test_create_crew():
    """Test crew creation."""
    crew = create_crew("What time is it?")
    assert crew is not None
    assert len(crew.agents) == 1
    assert len(crew.tasks) == 1
    assert crew.agents[0].role == "Research Assistant"


@pytest.mark.integration
@pytest.mark.skipif(
    not os.getenv("SERPER_API_KEY"),
    reason="SERPER_API_KEY not set"
)
def test_run_agent_with_search():
    """Integration test: Run agent with web search query."""
    query = "What is the capital of France?"
    response = run_agent(query)
    assert response is not None
    assert len(response) > 0
    # Should mention Paris in the response
    assert "Paris" in response or "paris" in response.lower()


@pytest.mark.integration
def test_run_agent_time_query():
    """Integration test: Run agent with time query."""
    query = "What time is it?"
    response = run_agent(query)
    assert response is not None
    assert len(response) > 0
```

**Test Structure**:
- Unit tests for individual functions (time tool, crew creation)
- Integration tests marked with `@pytest.mark.integration`
- Skip web search tests if API key not configured
- Follow pattern from other agents' test files

**Verification**:
```bash
# Run tests after project creation
cd target/test-project
pytest tests/integration/test_agent.py -v
```

---

### TASK 6: Create README.md

**File**: `agent_starter_pack/agents/crewai_base/README.md`

**Content Structure**:

```markdown
# CrewAI Base Agent

A ReAct-style research agent built with CrewAI framework and Google Vertex AI Gemini.

## Overview

This agent template demonstrates autonomous agent development using CrewAI with Google Cloud's Vertex AI. It features web search capabilities for answering questions with up-to-date information.

### Key Features

- **Framework**: CrewAI 0.80+
- **LLM**: Google Gemini 2.0 Flash (via Vertex AI)
- **Tools**: Web search (SerperDevTool), current time
- **Deployment**: Cloud Run and Agent Engine support
- **Architecture**: Single agent with sequential task processing

## Quick Start

### Prerequisites

```bash
# Set up Serper API key for web search (get free key at serper.dev)
export SERPER_API_KEY="your-api-key-here"
```

### Local Development

```bash
# Install dependencies
uv sync

# Run the agent
python -m {{cookiecutter.agent_directory}}.agent

# Run with custom query
python -c "from app.agent import run_agent; print(run_agent('What are the latest AI trends?'))"
```

### Testing

```bash
# Run all tests
pytest tests/

# Run integration tests only
pytest tests/integration/ -v

# Run specific test
pytest tests/integration/test_agent.py::test_run_agent_time_query -v
```

## Architecture

```
User Query → CrewAI Task → Research Agent → [Web Search Tool | Time Tool]
                                    ↓
                              Gemini 2.0 Flash (Vertex AI)
                                    ↓
                            Synthesized Response
```

### How It Works

1. **Query Input**: User submits a question
2. **Task Creation**: CrewAI creates a Task with the query
3. **Agent Processing**: Research Agent analyzes the query
4. **Tool Selection**: Agent decides which tools to use (search, time)
5. **LLM Reasoning**: Gemini processes tool results
6. **Response**: Final synthesized answer returned

## Customization

### Adding Custom Tools

```python
# In app/agent.py

def my_custom_tool(parameter: str) -> str:
    """Tool description for the LLM to understand when to use it.

    Args:
        parameter: Description of the parameter.

    Returns:
        Description of what the tool returns.
    """
    # Your implementation
    return result

# Add to agent
research_agent = Agent(
    role="Research Assistant",
    tools=[search_tool, get_current_time, my_custom_tool],
    # ...
)
```

### Changing the LLM Model

```python
# In app/agent.py

llm = LLM(
    model="gemini/gemini-1.5-pro",  # Change model
    temperature=0.5,                 # Adjust temperature
    top_p=0.9,                      # Add other parameters
)
```

### Multi-Agent Extension

To extend to multiple agents:

```python
researcher = Agent(
    role="Researcher",
    goal="Find information",
    tools=[search_tool],
    llm=llm
)

analyst = Agent(
    role="Analyst",
    goal="Analyze findings",
    tools=[],
    llm=llm
)

crew = Crew(
    agents=[researcher, analyst],
    tasks=[research_task, analysis_task],
    process=Process.sequential
)
```

## Configuration

### Environment Variables

- `SERPER_API_KEY`: Required for web search (get from [serper.dev](https://serper.dev))
- `GOOGLE_CLOUD_PROJECT`: Set automatically by Agent Starter Pack
- `GOOGLE_GENAI_USE_VERTEXAI`: Set to "True" for Vertex AI

### Model Options

Available Gemini models:
- `gemini-2.0-flash-exp` (default) - Fast, efficient
- `gemini-1.5-pro` - Enhanced reasoning
- `gemini-1.5-flash` - Balanced performance

## Deployment

### Cloud Run

```bash
# Deploy to Cloud Run
make deploy-staging
```

### Agent Engine

```bash
# Deploy to Agent Engine
make deploy-agent-engine
```

See the main project documentation for detailed deployment instructions.

## Troubleshooting

### Web Search Not Working

**Problem**: "SERPER_API_KEY not found" or search errors

**Solution**:
1. Get API key from [serper.dev](https://serper.dev) (free tier available)
2. Set environment variable: `export SERPER_API_KEY="your-key"`
3. Add to `.env` file for persistence

### Vertex AI Authentication Errors

**Problem**: "Could not authenticate with Vertex AI"

**Solution**:
```bash
# Authenticate with Google Cloud
gcloud auth application-default login

# Set project
gcloud config set project YOUR_PROJECT_ID
```

## Learn More

- [CrewAI Documentation](https://docs.crewai.com)
- [Agent Starter Pack Documentation](https://googlecloudplatform.github.io/agent-starter-pack/)
- [Vertex AI Gemini Documentation](https://cloud.google.com/vertex-ai/docs/generative-ai/model-reference/gemini)
- [Serper API Documentation](https://serper.dev/docs)

## License

Apache License 2.0 - See LICENSE file for details
```

**Verification**: Markdown renders correctly and all links are valid

---

### TASK 7: Create Evaluation Notebook

**File**: `agent_starter_pack/agents/crewai_base/notebooks/evaluating_crewai_agent.ipynb`

**Notebook Structure** (8-10 cells):

#### Cell 1: Introduction
```markdown
# Evaluating CrewAI Agent

This notebook demonstrates how to evaluate the CrewAI agent using Vertex AI's evaluation framework.

## Prerequisites
- Google Cloud project with Vertex AI enabled
- Authenticated with `gcloud auth application-default login`
- SERPER_API_KEY environment variable set
```

#### Cell 2: Install Dependencies
```python
# Install required packages
!pip install -q crewai crewai-tools langchain-google-vertexai google-cloud-aiplatform
```

#### Cell 3: Setup and Authentication
```python
import os
import google.auth

# Authenticate
credentials, project_id = google.auth.default()
print(f"Project ID: {project_id}")

# Set environment variables
os.environ["GOOGLE_CLOUD_PROJECT"] = project_id
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"

# Check for Serper API key
if not os.getenv("SERPER_API_KEY"):
    print("⚠️  Warning: SERPER_API_KEY not set. Web search will not work.")
    print("Get a free API key at: https://serper.dev")
```

#### Cell 4: Import Agent
```python
# Import the agent
import sys
sys.path.append('../')

from app.agent import run_agent, create_crew, research_agent
```

#### Cell 5: Test Queries
```python
# Define test queries
test_queries = [
    "What time is it?",
    "What are the latest developments in generative AI?",
    "Who won the most recent Nobel Prize in Physics?",
    "What is the capital of Australia?",
]

# Run queries
results = []
for query in test_queries:
    print(f"\n{'='*60}")
    print(f"Query: {query}")
    print(f"{'='*60}")

    response = run_agent(query)
    print(f"Response: {response}\n")

    results.append({
        "query": query,
        "response": response
    })
```

#### Cell 6: Vertex AI Evaluation Setup
```python
# Set up Vertex AI evaluation
from google.cloud import aiplatform

aiplatform.init(project=project_id, location="us-central1")

# Define evaluation dataset
eval_dataset = [
    {
        "query": q["query"],
        "response": q["response"]
    }
    for q in results
]
```

#### Cell 7: Run Evaluation Metrics
```python
# Example: Evaluate response quality
# This is a placeholder - follow pattern from other agent notebooks

from vertexai.preview.evaluation import EvalTask

eval_task = EvalTask(
    dataset=eval_dataset,
    metrics=["bleu", "rouge"],
)

eval_result = eval_task.evaluate()
print(eval_result.summary_metrics)
```

#### Cell 8: Visualize Results
```python
import pandas as pd

# Create results dataframe
df = pd.DataFrame(results)
df["response_length"] = df["response"].apply(len)

print(df)
```

#### Cell 9: Analysis and Insights
```markdown
## Analysis

- Response times
- Answer quality
- Tool usage patterns
- Areas for improvement
```

**Verification**: Notebook runs without errors (with proper credentials)

---

### TASK 8: Create Local Example Notebook

**File**: `agent_starter_pack/agents/crewai_base/notebooks/crewai_local_example.ipynb`

**Simpler Notebook** (5 cells):

#### Cell 1: Setup
```python
# Quick local testing notebook for CrewAI agent

import sys
sys.path.append('../')

from app.agent import run_agent, get_current_time, research_agent
```

#### Cell 2: Test Individual Tools
```python
# Test time tool
print("Time Tool:")
print(get_current_time())
print()

# Test agent info
print("Agent Info:")
print(f"Role: {research_agent.role}")
print(f"Goal: {research_agent.goal}")
print(f"Tools: {len(research_agent.tools)}")
```

#### Cell 3: Simple Query
```python
# Test with simple time query
query = "What time is it?"
response = run_agent(query)
print(f"Query: {query}")
print(f"Response: {response}")
```

#### Cell 4: Search Query (if API key available)
```python
import os

if os.getenv("SERPER_API_KEY"):
    query = "What is CrewAI framework?"
    response = run_agent(query)
    print(f"Query: {query}")
    print(f"Response: {response}")
else:
    print("⚠️  SERPER_API_KEY not set - skipping web search test")
    print("Get a free key at: https://serper.dev")
```

#### Cell 5: Custom Query
```python
# Try your own query
custom_query = input("Enter your query: ")
response = run_agent(custom_query)
print(f"\nResponse: {response}")
```

**Verification**: Runs in Jupyter/VS Code without errors

---

## 🧪 Testing & Verification Steps

### Step 1: Verify Agent Discovery

**Command**:
```bash
# List available agents (should include crewai_base)
uv run agent-starter-pack list
```

**Expected Output**:
```
Available agents:
  - adk_base
  - adk_a2a_base
  - adk_live
  - agentic_rag
  - crewai_base  ← Should appear here
  - langgraph_base
```

---

### Step 2: Create Test Project

**Command**:
```bash
# Create a test project with crewai_base agent
uv run agent-starter-pack create crewai-test-$(date +%s) \
  --agent crewai_base \
  -d cloud_run \
  --session-type in_memory \
  -p -s -y \
  --output-dir target
```

**Expected Result**: Project created successfully in `target/` directory

**Verification**:
```bash
cd target/crewai-test-*
ls -la
# Should show: app/, tests/, notebooks/, Makefile, pyproject.toml, etc.
```

---

### Step 3: Test Local Execution

**Commands**:
```bash
cd target/crewai-test-*

# Install dependencies
uv sync

# Set API key (get from serper.dev)
export SERPER_API_KEY="your-api-key"

# Run agent
python -m app.agent
```

**Expected Output**:
```
Query: What are the latest developments in generative AI agents?
Response: [Agent's response with search results]
```

---

### Step 4: Run Integration Tests

**Commands**:
```bash
cd target/crewai-test-*

# Run all tests
pytest tests/integration/ -v

# Run specific test
pytest tests/integration/test_agent.py::test_get_current_time -v
```

**Expected Result**: Tests pass (some may skip if SERPER_API_KEY not set)

---

### Step 5: Template Linting

**Commands**:
```bash
# From repo root
SKIP_MYPY=1 _TEST_AGENT_COMBINATION="crewai_base,cloud_run,--session-type,in_memory" make lint-templated-agents

SKIP_MYPY=1 _TEST_AGENT_COMBINATION="crewai_base,agent_engine" make lint-templated-agents
```

**Expected Result**: No linting errors (Ruff passes)

**Common Issues to Check**:
- Import ordering (third-party vs. local imports)
- Line length (max 88 characters)
- Trailing whitespace
- File ending with exactly one newline

---

### Step 6: Template Testing

**Commands**:
```bash
# Test both deployment targets
_TEST_AGENT_COMBINATION="crewai_base,cloud_run,--session-type,in_memory" make test-templated-agents

_TEST_AGENT_COMBINATION="crewai_base,agent_engine" make test-templated-agents
```

**Expected Result**: Template generation and basic tests pass

---

### Step 7: Test Notebooks

**Commands**:
```bash
cd target/crewai-test-*/notebooks

# Start Jupyter
jupyter notebook

# Or use VS Code with Jupyter extension
code crewai_local_example.ipynb
```

**Expected Result**:
- Notebooks load without errors
- Can execute cells sequentially
- Agent responds to queries

---

## 🔍 Common Issues & Solutions

### Issue 1: Agent Not Appearing in CLI Menu

**Problem**: `crewai_base` doesn't show in `agent-starter-pack list`

**Diagnosis**:
```bash
# Check directory exists
ls -la agent_starter_pack/agents/crewai_base/

# Check templateconfig.yaml exists
cat agent_starter_pack/agents/crewai_base/.template/templateconfig.yaml
```

**Solution**: Ensure `.template/templateconfig.yaml` exists and is valid YAML

---

### Issue 2: Dependency Installation Fails

**Problem**: `uv add` fails when adding crewai dependencies

**Diagnosis**:
```bash
# Try installing manually
cd target/test-project
uv add "crewai>=0.80.0,<1.0.0"
```

**Solution**:
- Check Python version (must be 3.10-3.13 for CrewAI)
- Update dependency versions in templateconfig.yaml
- Check for conflicting dependencies

---

### Issue 3: Linting Errors

**Problem**: Ruff reports formatting or import issues

**Common Errors**:
1. **Import ordering**: Third-party imports before local imports
2. **Line too long**: Split long lines (max 88 chars)
3. **Trailing whitespace**: Remove extra spaces
4. **Missing final newline**: Add exactly one newline at file end

**Solution**:
```bash
# Auto-fix formatting
cd target/test-project
uv run ruff format .

# Check remaining issues
uv run ruff check .
```

---

### Issue 4: Jinja2 Template Rendering Errors

**Problem**: Cookiecutter fails to render templates

**Common Causes**:
- Unbalanced `{% if %}` / `{% endif %}`
- Missing `{{cookiecutter.variable_name}}`
- Extra/missing whitespace control (`{%-` / `-%}`)

**Solution**:
- Verify all Jinja blocks are closed
- Test rendering with: `cookiecutter agent_starter_pack/agents/crewai_base/`

---

### Issue 5: Web Search Not Working

**Problem**: Agent can't perform web searches

**Diagnosis**:
```bash
# Check API key
echo $SERPER_API_KEY

# Test SerperDevTool directly
python -c "from crewai_tools import SerperDevTool; tool = SerperDevTool(); print(tool.run('test'))"
```

**Solution**:
- Get API key from https://serper.dev (free tier: 2,500 queries/month)
- Set environment variable: `export SERPER_API_KEY="your-key"`
- Add to `.env` file for persistence

---

### Issue 6: Vertex AI Authentication Errors

**Problem**: "Could not authenticate with Vertex AI"

**Solution**:
```bash
# Authenticate with Google Cloud
gcloud auth application-default login

# Set project
gcloud config set project YOUR_PROJECT_ID

# Verify authentication
gcloud auth list
```

---

## 📊 Implementation Checklist

### Core Files
- [ ] `.template/templateconfig.yaml` created with correct dependencies
- [ ] `app/__init__.py` created with license header
- [ ] `app/agent.py` created with CrewAI implementation
- [ ] `tests/integration/test_agent.py` created with tests
- [ ] `README.md` created with documentation
- [ ] `notebooks/evaluating_crewai_agent.ipynb` created
- [ ] `notebooks/crewai_local_example.ipynb` created

### Testing
- [ ] Agent appears in `agent-starter-pack list`
- [ ] Can create project with `agent-starter-pack create`
- [ ] Project dependencies install successfully
- [ ] Agent runs locally with `python -m app.agent`
- [ ] Integration tests pass
- [ ] Notebooks execute without errors

### Code Quality
- [ ] Passes Ruff linting (both deployment targets)
- [ ] Passes template generation tests
- [ ] Follows Agent Starter Pack patterns
- [ ] No modifications to existing CLI code
- [ ] Proper copyright headers on all files

### Documentation
- [ ] README.md is comprehensive
- [ ] Example queries are clear
- [ ] Configuration steps are documented
- [ ] Troubleshooting guide is complete

---

## 🚀 Next Steps After Implementation

1. **Test with Real Deployments**:
   ```bash
   # Deploy to Cloud Run (staging)
   cd target/crewai-test-*
   make deploy-staging
   ```

2. **Generate Lock Files**:
   ```bash
   # From repo root
   make generate-lock
   ```

3. **Create Pull Request**:
   - Branch: `feat/add-crewai-agent-template`
   - Title: "Add CrewAI agent template with web search"
   - Include: Testing results, example outputs, documentation

4. **Update Documentation**:
   - Add CrewAI to main README agent list
   - Update docs site with CrewAI example
   - Add CrewAI to agent comparison table

---

## 📚 Reference Materials

### CrewAI Documentation
- Main docs: https://docs.crewai.com
- GitHub: https://github.com/crewAIInc/crewAI
- Tools: https://docs.crewai.com/tools

### Agent Starter Pack Patterns
- Template reference: `agent_starter_pack/agents/adk_base/`
- LangGraph example: `agent_starter_pack/agents/langgraph_base/`
- CLI utils: `agent_starter_pack/cli/utils/template.py`

### Key Files to Reference
1. **`agent_starter_pack/agents/adk_base/app/agent.py`** - Simple agent pattern
2. **`agent_starter_pack/agents/langgraph_base/app/agent.py`** - Non-ADK framework example
3. **`agent_starter_pack/agents/adk_base/.template/templateconfig.yaml`** - Config example
4. **`GEMINI.md`** - Comprehensive templating guide

---

## 🎯 Success Metrics

Implementation is complete when:

1. ✅ Agent discoverable: Appears in CLI menu
2. ✅ Project creation: Can generate projects successfully
3. ✅ Local execution: Agent responds to queries
4. ✅ Tests passing: All integration tests pass
5. ✅ Linting clean: No Ruff or mypy errors
6. ✅ Both targets: Works with cloud_run and agent_engine
7. ✅ Documentation: README and notebooks are complete
8. ✅ Zero modifications: No changes to existing CLI code

---

## ⏱️ Estimated Timeline

- **TASK 1-3**: 15 minutes (directory structure, config, init)
- **TASK 4**: 45 minutes (main agent implementation)
- **TASK 5**: 30 minutes (integration tests)
- **TASK 6**: 30 minutes (README documentation)
- **TASK 7-8**: 45 minutes (notebooks)
- **Testing**: 30 minutes (verification and debugging)

**Total**: ~3 hours for full implementation and testing

---

## 📝 Notes and Considerations

### Web Search API Options

1. **SerperDevTool** (Recommended):
   - Free tier: 2,500 queries/month
   - Easy CrewAI integration
   - Requires API key from serper.dev

2. **Alternative: Custom Search Tool**:
   - Use Google Custom Search API
   - Use Brave Search API
   - Implement mock search for development

### Deployment Considerations

- **Cloud Run**: Requires API key in environment variables
- **Agent Engine**: Same authentication as other agents
- **Cost**: Web search API calls may incur costs (check quotas)

### Future Enhancements

- Add more tools (calculator, file operations)
- Multi-agent crew examples
- RAG integration with web search
- Custom search tool implementation
- Streaming responses support

---

**End of Planning Document**
