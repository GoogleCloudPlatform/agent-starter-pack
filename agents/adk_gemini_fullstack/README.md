# Gemini Fullstack Agent Development Kit (ADK) Quickstart

> 🔍 **Sample Agent**: This agent is part of the [ADK Samples](https://github.com/google/adk-samples/tree/main/python/agents/gemini-fullstack) collection, showcasing agent implementations using the Agent Development Kit.

The **Gemini Fullstack Agent Development Kit (ADK) Quickstart** is a production-ready blueprint for building a sophisticated, fullstack research agent with Gemini. It's built to demonstrate how the ADK helps structure complex agentic workflows, build modular agents, and incorporate critical Human-in-the-Loop (HITL) steps.

<table>
  <thead>
    <tr>
      <th colspan="2">Key Features</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>🏗️</td>
      <td><strong>Fullstack & Production-Ready:</strong> A complete React frontend and ADK-powered FastAPI backend, with deployment options for <a href="https://cloud.google.com/run">Google Cloud Run</a> and <a href="https://cloud.google.com/vertex-ai/generative-ai/docs/agent-engine/overview">Vertex AI Agent Engine</a>.</td>
    </tr>
    <tr>
      <td>🧠</td>
      <td><strong>Advanced Agentic Workflow:</strong> The agent uses Gemini to <strong>strategize</strong> a multi-step plan, <strong>reflect</strong> on findings to identify gaps, and <strong>synthesize</strong> a final, comprehensive report.</td>
    </tr>
    <tr>
      <td>🔄</td>
      <td><strong>Iterative & Human-in-the-Loop Research:</strong> Involves the user for plan approval, then autonomously loops through searching (via Gemini function calling) and refining its results until it has gathered sufficient information.</td>
    </tr>
  </tbody>
</table>
