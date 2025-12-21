# CrewAI Base Agent

<p align="center">
  <img src="https://avatars.githubusercontent.com/u/170677839?s=200&v=4" width="200" alt="CrewAI Logo">
</p>

A ReAct-style AI assistant built with **[CrewAI](https://www.crewai.com/)** framework and Google Vertex AI Gemini. This example demonstrates autonomous agent development using CrewAI with self-contained utility tools that require no external API keys.

## Key Features

- **Framework**: CrewAI 1.7+
- **LLM**: Google Gemini 2.0 Flash (via Vertex AI)
- **Zero External APIs**: All tools work offline without API key configuration
- **Simple Architecture**: Single agent with sequential task processing
- **Web UI**: Includes simple_chat frontend for easy interaction

## Tools

This agent includes four utility tools:

- **Calculate**: Performs mathematical calculations (e.g., `2 + 2`, `10 * (5 + 3)`)
- **Analyze Text**: Provides text statistics, word count, and sentiment analysis
- **Get Current Time**: Returns current time in UTC
- **Generate Ideas**: Brainstorms creative ideas on any topic using the LLM

## Known Limitations

### Deployment Target: Cloud Run Only

CrewAI agents currently support **Cloud Run deployment only**. Agent Engine is not supported because:

- CrewAI is a generic agent framework (not ADK-based)
- Agent Engine requires ADK or A2A protocol integration
- CrewAI uses its own agent orchestration system

### Limited Telemetry Support

Advanced telemetry features (Traceloop SDK) are **not available** for CrewAI agents due to dependency conflicts:

- CrewAI includes `opentelemetry-sdk` v1.34.x
- Traceloop SDK requires `opentelemetry-sdk` v1.38+
- Version conflict prevents full telemetry integration

**Impact:** Basic logging is available, but advanced distributed tracing via Traceloop is disabled for this template.

**Workaround:** The base template gracefully degrades when OpenTelemetry dependencies are unavailable, allowing CrewAI agents to run without telemetry errors.

## Additional Resources

- **CrewAI Documentation**: Learn more about CrewAI concepts and capabilities in the [official documentation](https://docs.crewai.com/)
- **CrewAI Examples**: Explore more examples in the [CrewAI repository](https://github.com/crewAIInc/crewAI)
- **Agent Starter Pack Docs**: See the [main documentation](https://googlecloudplatform.github.io/agent-starter-pack/) for deployment guides
