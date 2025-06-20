# Agent Templates

The Agent Starter Pack follows a "bring your own agent" approach. It provides several production-ready agent templates designed to accelerate your development while offering the flexibility to use your preferred agent framework or pattern.

## Available Templates


| Agent Name | Description | Use Case |
|------------|-------------|----------|
| `adk_base` | A base ReAct agent implemented using Google's [Agent Development Kit](https://github.com/google/adk-python) | General purpose conversational agent |
| `adk_gemini_fullstack` | A production-ready fullstack research agent with Gemini | Complex research and information synthesis |
| `agentic_rag` | A RAG agent for document retrieval and Q&A | Document search and question answering |
| `langgraph_base_react` | A base ReAct agent using LangGraph | Graph based conversational agent |
| `crewai_coding_crew` | A multi-agent system implemented with CrewAI | Collaborative coding assistance |
| `live_api` | A real-time multimodal RAG agent | Audio/video/text chat with knowledge base |

## Choosing the Right Template

When selecting a template, consider these factors:

1.  **Primary Goal**: Are you building a conversational bot, a Q&A system over documents, a task-automation crew, or something else?
2.  **Core Pattern/Framework**: Do you have a preference for Google's ADK, LangChain/LangGraph, CrewAI, or implementing a pattern like RAG directly? The Starter Pack supports various approaches.
3.  **Reasoning Complexity**: Does your agent need complex planning and tool use (like ReAct), or is it more focused on retrieval and synthesis (like basic RAG)?
4.  **Collaboration Needs**: Do you need multiple specialized agents working together?
5.  **Modality**: Does your agent need to process or respond with audio, video, or just text?

## Template Details

### ADK Base (`adk_base`)

This template provides a minimal example of a ReAct agent built using Google's [Agent Development Kit (ADK)](https://github.com/google/adk-python). It demonstrates core ADK concepts like agent creation and tool integration, enabling reasoning and tool selection. Ideal for:

*   Getting started with agent development on Google Cloud.
*   Building general-purpose conversational agents.
*   Learning the ADK framework and ReAct pattern.

### ADK Gemini Fullstack (`adk_gemini_fullstack`)

> 🔍 **Sample Agent**: This agent is part of the [ADK Samples](https://github.com/google/adk-samples/tree/main/python/agents/gemini-fullstack) collection, showcasing agent implementations using the Agent Development Kit.

This template provides a production-ready blueprint for building a sophisticated, fullstack research agent with Gemini. It demonstrates how the ADK helps structure complex agentic workflows, build modular agents, and incorporate critical Human-in-the-Loop (HITL) steps. Key features include:

*   A complete React frontend and ADK-powered FastAPI backend
*   Advanced agentic workflow where the agent strategizes a multi-step plan, reflects on findings to identify gaps, and synthesizes a final, comprehensive report.
*   Iterative and Human-in-the-Loop research that involves the user for plan approval, then autonomously loops through searching and refining results.

### Agentic RAG (`agentic_rag`)

Built on the ADK, this template implements [Retrieval-Augmented Generation (RAG)](https://cloud.google.com/use-cases/retrieval-augmented-generation?hl=en) with a production-ready data ingestion pipeline for document-based question answering. It allows you to ingest, process, and embed custom data to enhance response relevance. Features include:

*   Automated data ingestion pipeline for custom data.
*   Flexible datastore options: [Vertex AI Search](https://cloud.google.com/vertex-ai-search-and-conversation) and [Vertex AI Vector Search](https://cloud.google.com/vertex-ai/docs/vector-search/overview).
*   Generation of custom embeddings for enhanced semantic search.
*   Answer synthesis from retrieved context.
*   Infrastructure deployment via Terraform and Cloud Build.

### LangGraph Base ReAct (`langgraph_base_react`)

This template provides a minimal example of a ReAct agent built using [LangGraph](https://langchain-ai.github.io/langgraph/). It serves as an excellent starting point for developing agents with graph-based structures, offering:

*   Explicit state management for complex, multi-step reasoning flows.
*   Fine-grained control over reasoning cycles.
*   Robust tool integration and error handling capabilities.
*   Streaming response support using Vertex AI.
*   Includes a basic search tool to demonstrate tool usage.

### CrewAI Coding Crew (`crewai_coding_crew`)

This template combines [CrewAI](https://www.crewai.com/)'s multi-agent collaboration with LangGraph's conversational control to create an interactive coding assistant. It orchestrates specialized agents (e.g., Senior Engineer, QA Engineer) to understand requirements and generate code. Key features include:

*   Interactive requirements gathering through natural dialogue (LangGraph).
*   Collaborative code development by a crew of specialized AI agents (CrewAI).
*   Sequential processing for tasks from requirements to implementation and QA.
*   Ideal for complex tasks requiring delegation and simulating team collaboration.

### Live API (`live_api`)

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