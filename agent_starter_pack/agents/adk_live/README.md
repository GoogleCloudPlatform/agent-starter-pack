# ADK Live Agent

Real-time conversational agent built with Google ADK and Gemini's live audio model. Supports audio, video, and text interactions with native tool calling.

![live_api_diagram](https://storage.googleapis.com/github-repo/generative-ai/sample-apps/e2e-gen-ai-app-starter-pack/live_api_diagram.png)

**Key components:**

- **Python Backend** (in `app/` folder): ADK-powered agent using Gemini's live audio model with native tool calling and deployment support for Cloud Run and Agent Engine

- **React Frontend** (in `frontend/` folder): Web console for interacting with the live agent via audio, video, and text

![live api demo](https://storage.googleapis.com/github-repo/generative-ai/sample-apps/e2e-gen-ai-app-starter-pack/adk_live_pattern_demo.gif)

Once running, click the play button to connect and interact with the agent. Try asking "What's the weather like in San Francisco?" to see tool calling in action.

## Additional Resources for Multimodal Live API

Explore these resources to learn more about the Multimodal Live API and see examples of its usage:

- [Project Pastra](https://github.com/heiko-hotz/gemini-multimodal-live-dev-guide/tree/main): a comprehensive developer guide for the Gemini Multimodal Live API.
- [ADK Samples: Realtime Conversational Agent](https://github.com/google/adk-samples/tree/main/python/agents/realtime-conversational-agent): Full-stack, reusable template using Agent Development Kit (ADK) with the Gemini Live API.
- [Google Cloud Multimodal Live API demos and samples](https://github.com/GoogleCloudPlatform/generative-ai/tree/main/gemini/multimodal-live-api): Collection of code samples and demo applications leveraging multimodal live API in Vertex AI
- [Gemini 2 Cookbook](https://github.com/google-gemini/cookbook/tree/main/gemini-2): Practical examples and tutorials for working with Gemini 2
- [Multimodal Live API Web Console](https://github.com/google-gemini/multimodal-live-api-web-console): Interactive React-based web interface for testing and experimenting with Gemini Multimodal Live API.

## Current Status & Future Work

This pattern is under active development. Key areas planned for future enhancement include:

*   **Observability:** Implementing comprehensive monitoring and tracing features.
*   **Load Testing:** Integrating load testing capabilities.
