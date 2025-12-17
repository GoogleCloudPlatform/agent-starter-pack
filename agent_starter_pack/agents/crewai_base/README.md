# CrewAI Base Agent

A ReAct-style research agent built with CrewAI framework and Google Vertex AI Gemini.

## Overview

This agent template demonstrates autonomous agent development using CrewAI with Google Cloud's Vertex AI. It features web search capabilities for answering questions with up-to-date information.

### Key Features

- **Framework**: CrewAI 1.7+
- **LLM**: Google Gemini 2.0 Flash (via Vertex AI)
- **Tools**: Web search (Google Custom Search), current time
- **Deployment**: Cloud Run and Agent Engine support
- **Architecture**: Single agent with sequential task processing

## Quick Start

### Prerequisites

For web search functionality, you'll need Google Custom Search API credentials:

```bash
# Get Google API Key from Google Cloud Console
# https://console.cloud.google.com/apis/credentials

# Create a Custom Search Engine
# https://programmablesearchengine.google.com/

# Set environment variables
export GOOGLE_API_KEY="your-api-key-here"
export GOOGLE_CSE_ID="your-custom-search-engine-id"
```

**Note**: The agent works without API keys using mock search responses for testing.

### Local Development

```bash
# Install dependencies
uv sync

# Run the agent
python -m {{cookiecutter.agent_directory}}.agent

# Run with custom query
python -c "from {{cookiecutter.agent_directory}}.agent import run_agent; print(run_agent('What are the latest AI trends?'))"
```

### Testing

```bash
# Run all tests
pytest tests/

# Run integration tests only
pytest tests/integration/ -v

# Run specific test
pytest tests/integration/test_agent.py::test_run_agent_time_query -v

# Run tests with real search (requires API keys)
pytest tests/integration/test_agent.py::test_run_agent_with_search -v
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
# In {{cookiecutter.agent_directory}}/agent.py

from crewai.tools import tool

@tool("Your Tool Name")
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
    tools=[web_search, get_current_time, my_custom_tool],
    # ...
)
```

### Changing the LLM Model

```python
# In {{cookiecutter.agent_directory}}/agent.py

llm = LLM(
    model="vertex_ai/gemini-1.5-pro",  # Change model
    temperature=0.5,                    # Adjust temperature
)
```

### Multi-Agent Extension

To extend to multiple agents:

```python
researcher = Agent(
    role="Researcher",
    goal="Find information",
    tools=[web_search],
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

- `GOOGLE_API_KEY`: Google Cloud API key for Custom Search (optional for testing)
- `GOOGLE_CSE_ID`: Custom Search Engine ID (optional for testing)
- `GOOGLE_CLOUD_PROJECT`: Set automatically by Agent Starter Pack
- `GOOGLE_GENAI_USE_VERTEXAI`: Set automatically for Vertex AI

### Available Gemini Models

- `vertex_ai/gemini-2.0-flash-exp` (default) - Fast, efficient
- `vertex_ai/gemini-1.5-pro` - Enhanced reasoning
- `vertex_ai/gemini-1.5-flash` - Balanced performance

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

**Problem**: "Mock search results" or search errors

**Solution**:
1. Get API key from [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
2. Create a Custom Search Engine at [Programmable Search Engine](https://programmablesearchengine.google.com/)
3. Set environment variables:
   ```bash
   export GOOGLE_API_KEY="your-key"
   export GOOGLE_CSE_ID="your-cse-id"
   ```
4. Add to `.env` file for persistence

**Note**: Google Custom Search has a free tier (100 queries/day) and paid tiers available.

### Vertex AI Authentication Errors

**Problem**: "Could not authenticate with Vertex AI"

**Solution**:
```bash
# Authenticate with Google Cloud
gcloud auth application-default login

# Set project
gcloud config set project YOUR_PROJECT_ID
```

### CrewAI Import Errors

**Problem**: "No module named 'crewai'"

**Solution**:
```bash
# Ensure dependencies are installed
uv sync

# Or manually install
uv add "crewai>=1.7.0"
```

## Learn More

- [CrewAI Documentation](https://docs.crewai.com)
- [Agent Starter Pack Documentation](https://googlecloudplatform.github.io/agent-starter-pack/)
- [Vertex AI Gemini Documentation](https://cloud.google.com/vertex-ai/docs/generative-ai/model-reference/gemini)
- [Google Custom Search JSON API](https://developers.google.com/custom-search/v1/overview)

## License

Apache License 2.0 - See LICENSE file for details
