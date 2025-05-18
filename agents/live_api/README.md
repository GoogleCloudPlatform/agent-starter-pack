# Multimodal Live Agent

This pattern showcases a real-time conversational agent powered by Google Gemini. The agent handles audio, video, and text interactions while leveraging tool calling capabilities for enhanced responses.

![live_api_diagram](https://storage.googleapis.com/github-repo/generative-ai/sample-apps/e2e-gen-ai-app-starter-pack/live_api_diagram.png)

**Key components:**

- **Python Backend** (in `app/` folder): A production-ready server built with [FastAPI](https://fastapi.tiangolo.com/) and [google-genai](https://googleapis.github.io/python-genai/) that features:

  - **Real-time bidirectional communication** via WebSockets between the frontend and Gemini model
  - **Integrated tool calling** with a weather information tool for demonstrating external data retrieval
  - **Production-grade reliability** with retry logic and automatic reconnection capabilities
  - **Deployment flexibility** supporting both AI Studio and Vertex AI endpoints
  - **Feedback logging endpoint** for collecting user interactions

- **React Frontend** (in `frontend/` folder): Extends the [Multimodal live API Web Console](https://github.com/google-gemini/multimodal-live-api-web-console), with added features like **custom URLs** and **feedback collection**.

![live api demo](https://storage.googleapis.com/github-repo/generative-ai/sample-apps/e2e-gen-ai-app-starter-pack/live_api_pattern_demo.gif)

Once both the backend and frontend are running, click the play button in the frontend UI to establish a connection with the backend. You can now interact with the Multimodal Live Agent! You can try asking questions such as "What's the weather like in San Francisco?" to see the agent use its weather information tool.

## Additional Resources for Multimodal Live API

Explore these resources to learn more about the Multimodal Live API and see examples of its usage:

- [Project Pastra](https://github.com/heiko-hotz/gemini-multimodal-live-dev-guide/tree/main): a comprehensive developer guide for the Gemini Multimodal Live API.
- [Google Cloud Multimodal Live API demos and samples](https://github.com/GoogleCloudPlatform/generative-ai/tree/main/gemini/multimodal-live-api): Collection of code samples and demo applications leveraging multimodal live API in Vertex AI
- [Gemini 2 Cookbook](https://github.com/google-gemini/cookbook/tree/main/gemini-2): Practical examples and tutorials for working with Gemini 2
- [Multimodal Live API Web Console](https://github.com/google-gemini/multimodal-live-api-web-console): Interactive React-based web interface for testing and experimenting with Gemini Multimodal Live API.

## Current Status & Future Work

This pattern is under active development. Key areas planned for future enhancement include:

*   **Observability:** Implementing comprehensive monitoring and tracing features.
*   **Load Testing:** Integrating load testing capabilities.
