# CrewAI Base Agent

A ReAct-style AI assistant built with CrewAI framework and Google Vertex AI Gemini.

## Overview

This agent template demonstrates autonomous agent development using CrewAI with Google Cloud's Vertex AI. It features multiple utility tools that work completely offline without requiring external API keys.

### Key Features

- **Framework**: CrewAI 1.7+
- **LLM**: Google Gemini 2.0 Flash (via Vertex AI)
- **Tools**: Calculator, text analyzer, time checker, idea generator
- **Deployment**: Cloud Run support
- **Architecture**: Single agent with sequential task processing
- **No External APIs**: All tools work offline without API keys

## Quick Start

### Prerequisites

No external API keys required! This template works completely offline with Google Vertex AI (which is configured automatically by Agent Starter Pack).

### Local Development

```bash
# Install dependencies
uv sync

# Run the agent with the default example
python -m {{cookiecutter.agent_directory}}.agent

# Run with custom queries
python -c "from {{cookiecutter.agent_directory}}.agent import run_agent; print(run_agent('What is 15 * 23 + 47?'))"
python -c "from {{cookiecutter.agent_directory}}.agent import run_agent; print(run_agent('Analyze this text: Hello world!'))"
python -c "from {{cookiecutter.agent_directory}}.agent import run_agent; print(run_agent('Generate 3 ideas for a mobile app'))"
```

### Testing

```bash
# Run all tests
pytest tests/

# Run integration tests only
pytest tests/integration/ -v

# Run specific tests
pytest tests/integration/test_agent.py::test_get_current_time -v
pytest tests/integration/test_agent.py::test_calculate_tool -v
pytest tests/integration/test_agent.py::test_analyze_text_tool -v
```

## Architecture

```
User Query → CrewAI Task → AI Assistant → [Calculate | Analyze Text | Get Time | Generate Ideas]
                                  ↓
                            Gemini 2.0 Flash (Vertex AI)
                                  ↓
                          Synthesized Response
```

### How It Works

1. **Query Input**: User submits a question or request
2. **Task Creation**: CrewAI creates a Task with the query
3. **Agent Processing**: AI Assistant analyzes the query
4. **Tool Selection**: Agent decides which tools to use based on the request
5. **LLM Reasoning**: Gemini processes tool results and generates response
6. **Response**: Final answer returned to user

### Available Tools

1. **Calculate**: Performs mathematical calculations (e.g., "What is 25 * 4 + 10?")
2. **Analyze Text**: Provides text statistics, word count, sentiment analysis
3. **Get Current Time**: Returns current time in UTC
4. **Generate Ideas**: Brainstorms creative ideas on any topic

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
assistant_agent = Agent(
    role="AI Assistant",
    tools=[calculate, analyze_text, get_current_time, generate_ideas, my_custom_tool],
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

- `GOOGLE_CLOUD_PROJECT`: Set automatically by Agent Starter Pack
- `GOOGLE_GENAI_USE_VERTEXAI`: Set automatically for Vertex AI

All tools work offline without requiring additional API keys or configuration.

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

See the main project documentation for detailed deployment instructions.

## Troubleshooting

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
