# LangGraph Base ReAct Agent with A2A Protocol

<p align="center">
  <img src="https://langchain-ai.github.io/langgraph/static/wordmark_dark.svg" width="50%" alt="LangGraph Logo" style="margin-right: 40px; vertical-align: middle;">
  <img src="https://github.com/a2aproject/A2A/blob/main/docs/assets/a2a-logo-white.svg?raw=true" width="40%" alt="A2A Logo" style="vertical-align: middle;">
</p>

A base ReAct agent built using **[LangGraph](https://docs.langchain.com/oss/python/langgraph/overview)** with **[Agent2Agent (A2A) Protocol](https://a2a-protocol.org/)** support. This example demonstrates how to build a LangGraph-based agent with distributed agent communication capabilities through the A2A protocol for interoperability with agents across different frameworks and languages.

## Key Features

- **Simple Architecture**: Shows the basic building blocks of a LangGraph agent
- **A2A Protocol Support**: Enables distributed agent communication and interoperability
- **Streaming Support**: Includes streaming response capability using Vertex AI
- **Sample Tool Integration**: Includes a basic search tool to demonstrate tool usage

## Validating Your A2A Implementation

This template includes the **[A2A Protocol Inspector](https://github.com/a2aproject/a2a-inspector)** for validating your agent's A2A implementation.

```bash
make inspector
```

The inspector now supports both JSON-RPC 2.0 (Cloud Run) and HTTP-JSON (Agent Engine) transport protocols:

- **Cloud Run**: Test locally at `http://localhost:8000` or connect to your deployed Cloud Run URL
- **Agent Engine**: Must deploy first, then connect to your deployed Agent Engine URL (local testing not available)

For detailed setup instructions including local and remote testing workflows, refer to the `README.md` in your generated project.
