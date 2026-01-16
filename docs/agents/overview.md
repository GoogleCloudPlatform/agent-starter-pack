# Agent Templates

The Agent Starter Pack follows a "bring your own agent" approach. It provides several production-ready agent templates designed to accelerate your development while offering the flexibility to use your preferred agent framework or pattern.

## Available Templates


| Agent Name | Description | Use Case |
|------------|-------------|----------|
| `adk` | A base ReAct agent implemented using Google's [Agent Development Kit](https://github.com/google/adk-python) | General purpose conversational agent |
| `adk_go` | A base ReAct agent implemented using Google's [Agent Development Kit for Go](https://github.com/google/adk-go) | Go-based conversational agent |
| `adk_a2a` | An ADK agent with [Agent2Agent (A2A) Protocol](https://a2a-protocol.org/) support | Distributed agent communication and interoperability across frameworks |
| `agentic_rag` | A RAG agent for document retrieval and Q&A | Document search and question answering |
| `langgraph` | A base ReAct agent implemented using LangChain's [LangGraph](https://github.com/langchain-ai/langgraph) | Graph based conversational agent |
| `adk_live` | A real-time multimodal RAG agent | Audio/video/text chat with knowledge base |

## Choosing the Right Template

When selecting a template, consider these factors:

1.  **Primary Goal**: Are you building a conversational bot, a Q&A system over documents, a task-automation network, or something else?
2.  **Programming Language**: Do you prefer Python or Go? Most templates are Python-based, but `adk_go` provides a Go alternative.
3.  **Core Pattern/Framework**: Do you have a preference for Google's ADK, LangChain/LangGraph, or implementing a pattern like RAG directly? The Starter Pack supports various approaches.
4.  **Reasoning Complexity**: Does your agent need complex planning and tool use (like ReAct), or is it more focused on retrieval and synthesis (like basic RAG)?
5.  **Collaboration Needs**: Do you need multiple specialized agents working together?
6.  **Modality**: Does your agent need to process or respond with audio, video, or just text?

## Template Details

### ADK Base (`adk`)

This template provides a minimal example of a ReAct agent built using Google's [Agent Development Kit (ADK)](https://github.com/google/adk-python). It demonstrates core ADK concepts like agent creation and tool integration, enabling reasoning and tool selection. Ideal for:

*   Getting started with agent development on Google Cloud.
*   Building general-purpose conversational agents.
*   Learning the ADK framework and ReAct pattern.

### ADK Base Go (`adk_go`)

This template provides a minimal example of a ReAct agent built using Google's [Agent Development Kit for Go](https://github.com/google/adk-go). It offers the same core ADK concepts as the Python version but for Go developers. Ideal for:

*   Go developers building agents on Google Cloud.
*   Teams with existing Go codebases wanting to add AI agent capabilities.
*   High-performance agent deployments leveraging Go's concurrency model.

**Note:** Currently supports Cloud Run deployment only.

### ADK A2A Base (`adk_a2a`)

This template integrates Google's [Agent Development Kit (ADK)](https://github.com/google/adk-python) with the [Agent2Agent (A2A) Protocol](https://a2a-protocol.org/), enabling distributed agent communication and interoperability across different frameworks and languages. It demonstrates core ADK concepts while providing standardized interfaces for building distributed agent systems. Ideal for:

*   Exploring the A2A protocol and agent interoperability patterns.
*   Building distributed, multi-agent systems that communicate across frameworks.
*   Implementing microservices-based agent architectures.

### Agentic RAG (`agentic_rag`)

Built on the ADK, this template implements [Retrieval-Augmented Generation (RAG)](https://cloud.google.com/use-cases/retrieval-augmented-generation?hl=en) with a production-ready data ingestion pipeline for document-based question answering. It allows you to ingest, process, and embed custom data to enhance response relevance. Features include:

*   Automated data ingestion pipeline for custom data.
*   Flexible datastore options: [Vertex AI Search](https://cloud.google.com/vertex-ai-search-and-conversation) and [Vertex AI Vector Search](https://cloud.google.com/vertex-ai/docs/vector-search/overview).
*   Generation of custom embeddings for enhanced semantic search.
*   Answer synthesis from retrieved context.
*   Infrastructure deployment via Terraform and a choice of CI/CD runners (Google Cloud Build or GitHub Actions).

### LangGraph Base (`langgraph`)

This template provides a minimal example of a ReAct agent built using [LangGraph](https://langchain-ai.github.io/langgraph/). It supports [Agent2Agent (A2A) Protocol](https://a2a-protocol.org/) integration, enabling distributed agent communication and interoperability across frameworks. It serves as an excellent starting point for developing agents with graph-based structures, offering:

*   Building agents with explicit state management and complex reasoning flows.
*   Fine-grained control over agent behavior and tool orchestration.
*   Distributed, multi-agent systems with A2A protocol support.

### Live API (`adk_live`)

Powered by Google Gemini, this template showcases a real-time, multimodal conversational RAG agent using the [Vertex AI Live API](https://cloud.google.com/vertex-ai/generative-ai/docs/live-api). Features include:

*   Handles audio, video, and text interactions.
*   Leverages tool calling.
*   Real-time bidirectional communication via WebSockets for low-latency chat.
*   Production-ready Python backend (FastAPI) and React frontend.
*   Includes feedback collection capabilities.

## Customizing Templates

All templates are provided as starting points and are designed for customization:

1.  Choose a template that most closely matches your needs.
2.  Create a new agent instance based on the selected template.
3.  Familiarize yourself with the code structure, focusing on the agent logic, tool definitions, and any UI components.
4.  Modify and extend the code: adjust prompts, add or remove tools, integrate different data sources, change the reasoning logic, or update the framework versions as needed.

Have fun building your agent!