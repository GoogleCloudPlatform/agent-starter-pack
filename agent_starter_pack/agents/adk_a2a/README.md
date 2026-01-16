# ADK with Agent2Agent (A2A) Protocol: Minimal Agent Example

<p align="center">
  <img src="https://github.com/GoogleCloudPlatform/agent-starter-pack/blob/main/docs/images/adk_logo.png?raw=true" width="200" alt="ADK Logo" style="margin-right: 40px; vertical-align: middle;">
  <img src="https://github.com/a2aproject/A2A/blob/main/docs/assets/a2a-logo-white.svg?raw=true" width="200" alt="A2A Logo" style="vertical-align: middle;">
</p>

A basic agent built using the **[Google Agent Development Kit (ADK)](https://google.github.io/adk-docs/)** with **[Agent2Agent (A2A) Protocol](https://a2a-protocol.org/)** support. This example demonstrates core ADK concepts like agent creation and tool integration, while enabling distributed agent communication through the A2A protocol for interoperability with agents across different frameworks and languages.

This agent uses the `gemini-2.5-flash` model and is equipped with two simple tools:
*   `get_weather`: Simulates fetching weather (hardcoded for SF).
*   `get_current_time`: Simulates fetching the time (hardcoded for SF).

## Validating Your A2A Implementation

This template includes the **[A2A Protocol Inspector](https://github.com/a2aproject/a2a-inspector)** for validating your agent's A2A implementation.

```bash
make inspector
```

The inspector now supports both JSON-RPC 2.0 (Cloud Run) and HTTP-JSON (Agent Engine) transport protocols:

- **Cloud Run**: Test locally at `http://localhost:8000` or connect to your deployed Cloud Run URL
- **Agent Engine**: Must deploy first, then connect to your deployed Agent Engine URL (local testing not available)

For detailed setup instructions including local and remote testing workflows, refer to the `README.md` in your generated project.

## Additional Resources

### ADK Resources
- **ADK Documentation**: Learn more about ADK concepts and capabilities in the [official documentation](https://google.github.io/adk-docs/)
- **ADK Samples**: Explore more examples and use cases in the [official ADK Samples Repository](https://github.com/google/adk-samples)

### A2A Resources
- **A2A Documentation**: Learn about the Agent2Agent protocol and distributed agent communication in the [official A2A documentation](https://a2a-protocol.org/latest/specification/)
- **A2A Samples**: Explore A2A agent implementations and integration examples in the [A2A Samples Repository](https://github.com/a2aproject/a2a-samples)
