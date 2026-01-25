# 🚀 Agent Starter Pack

![Version](https://img.shields.io/pypi/v/agent-starter-pack?color=blue) [![1-Minute Video Overview](https://img.shields.io/badge/1--Minute%20Overview-gray)](https://youtu.be/jHt-ZVD660g) [![Docs](https://img.shields.io/badge/Documentation-gray)](https://googlecloudplatform.github.io/agent-starter-pack/) <a href="https://studio.firebase.google.com/new?template=https%3A%2F%2Fgithub.com%2FGoogleCloudPlatform%2Fagent-starter-pack%2Ftree%2Fmain%2Fagent_starter_pack%2Fresources%2Fidx">
  <picture>
    <source
      media="(prefers-color-scheme: dark)"
      srcset="https://cdn.firebasestudio.dev/btn/try_light_20.svg">
    <source
      media="(prefers-color-scheme: light)"
      srcset="https://cdn.firebasestudio.dev/btn/try_dark_20.svg">
    <img
      height="20"
      alt="Try in Firebase Studio"
      src="https://cdn.firebasestudio.dev/btn/try_blue_20.svg">
  </picture>
</a> [![Launch in Cloud Shell](https://img.shields.io/badge/Launch-in_Cloud_Shell-white)](https://shell.cloud.google.com/cloudshell/editor?cloudshell_git_repo=https%3A%2F%2Fgithub.com%2Feliasecchig%2Fasp-open-in-cloud-shell&cloudshell_print=open-in-cs) ![Stars](https://img.shields.io/github/stars/GoogleCloudPlatform/agent-starter-pack?color=yellow)

A Python package that provides **production-ready templates** for GenAI agents on Google Cloud.

Focus on your agent logic—the starter pack provides everything else: infrastructure, CI/CD, observability, and security.

| ⚡️ Launch | 🧪 Experiment  | ✅ Deploy | 🛠️ Customize |
|---|---|---|---|
| [Pre-built agent templates](./agent_starter_pack/agents/) (ReAct, RAG, multi-agent, Live API). | [Vertex AI evaluation](https://cloud.google.com/vertex-ai/generative-ai/docs/models/evaluation-overview) and an interactive playground. | Production-ready infra with [monitoring, observability](https://googlecloudplatform.github.io/agent-starter-pack/guide/observability), and [CI/CD](https://googlecloudplatform.github.io/agent-starter-pack/guide/deployment) on [Cloud Run](https://cloud.google.com/run) or [Agent Engine](https://cloud.google.com/vertex-ai/generative-ai/docs/agent-engine/overview). | Extend and customize templates according to your needs. 🆕 Now integrating with [Gemini CLI](https://github.com/google-gemini/gemini-cli) |

---

## ⚡ Get Started in 1 Minute

**From zero to production-ready agent in 60 seconds using [`uv`](https://docs.astral.sh/uv/getting-started/installation/):**

```bash
uvx agent-starter-pack create
```

<details>
<summary> ✨ Alternative: Using pip</summary>

If you don't have [`uv`](https://github.com/astral-sh/uv) installed, you can use pip:
```bash
# Create and activate a Python virtual environment
python -m venv .venv && source .venv/bin/activate

# Install the agent starter pack
pip install --upgrade agent-starter-pack

# Create a new agent project
agent-starter-pack create
```
</details>

**That's it!** You now have a fully functional agent project—complete with backend, frontend, and deployment infrastructure—ready for you to explore and customize.

### 🔧 Enhance Existing Agents

Already have an agent? Add production-ready deployment and infrastructure by running this command in your project's root folder:

```bash
uvx agent-starter-pack enhance
```

See [Installation Guide](https://googlecloudplatform.github.io/agent-starter-pack/guide/installation) for more options, or try with zero setup in [Firebase Studio](https://studio.firebase.google.com/new?template=https%3A%2F%2Fgithub.com%2FGoogleCloudPlatform%2Fagent-starter-pack%2Ftree%2Fmain%2Fsrc%2Fresources%2Fidx) or [Cloud Shell](https://shell.cloud.google.com/cloudshell/editor?cloudshell_git_repo=https%3A%2F%2Fgithub.com%2Feliasecchig%2Fasp-open-in-cloud-shell&cloudshell_print=open-in-cs).

---

## 🤖 Agents

| Agent Name                  | Description                                                                                                                       |
|-----------------------------|-----------------------------------------------------------------------------------------------------------------------------------|
| `adk`      | A base ReAct agent implemented using Google's [Agent Development Kit](https://github.com/google/adk-python) |
| `adk_a2a`  | An ADK agent with [Agent2Agent (A2A) Protocol](https://a2a-protocol.org/) support for distributed agent communication and interoperability |
| `agentic_rag` | A RAG agent for document retrieval and Q&A. Supporting [Vertex AI Search](https://cloud.google.com/generative-ai-app-builder/docs/enterprise-search-introduction) and [Vector Search](https://cloud.google.com/vertex-ai/docs/vector-search/overview).       |
| `langgraph`      | A base ReAct agent implemented using LangChain's [LangGraph](https://github.com/langchain-ai/langgraph) |
| `adk_live`       | A real-time multimodal RAG agent powered by Gemini, supporting audio/video/text chat     |

**More agents are on the way!** We are continuously expanding our [agent library](https://googlecloudplatform.github.io/agent-starter-pack/agents/overview). Have a specific agent type in mind? [Raise an issue as a feature request!](https://github.com/GoogleCloudPlatform/agent-starter-pack/issues/new?labels=enhancement)

**🔍 ADK Samples**

Looking to explore more ADK examples? Check out the [ADK Samples Repository](https://github.com/google/adk-samples) for additional examples and use cases demonstrating ADK's capabilities.

---

## 🌟 Community Showcase

Explore amazing projects built with the Agent Starter Pack! 

**[View Community Showcase →](https://googlecloudplatform.github.io/agent-starter-pack/guide/community-showcase)**

## Key Features

The `agent-starter-pack` offers key features to accelerate and simplify the development of your agent:
- **🔄 [CI/CD Automation](https://googlecloudplatform.github.io/agent-starter-pack/cli/setup_cicd)** - A single command to set up a complete CI/CD pipeline for all environments, supporting both **Google Cloud Build** and **GitHub Actions**.
- **📥 [Data Pipeline for RAG with Terraform/CI-CD](https://googlecloudplatform.github.io/agent-starter-pack/guide/data-ingestion)** - Seamlessly integrate a data pipeline to process embeddings for RAG into your agent system. Supporting [Vertex AI Search](https://cloud.google.com/generative-ai-app-builder/docs/enterprise-search-introduction) and [Vector Search](https://cloud.google.com/vertex-ai/docs/vector-search/overview).
- **[Remote Templates](https://googlecloudplatform.github.io/agent-starter-pack/remote-templates/)**: Create and share your own agent starter packs templates from any Git repository.
- **🤖 Gemini CLI Integration** - Use the [Gemini CLI](https://github.com/google-gemini/gemini-cli) and the included `GEMINI.md` context file to ask questions about your template, agent architecture, and the path to production. Get instant guidance and code examples directly in your terminal.

## High-Level Architecture

This starter pack covers all aspects of Agent development, from prototyping and evaluation to deployment and monitoring.

![High Level Architecture](docs/images/asp_high_level_architecture.png "Architecture")

---

## 🔧 Requirements

- Python 3.10+
- [Google Cloud SDK](https://cloud.google.com/sdk/docs/install)
- [Terraform](https://developer.hashicorp.com/terraform/downloads) (for deployment)
- [Make](https://www.gnu.org/software/make/) (for development tasks)


## 📚 Documentation

Visit our [documentation site](https://googlecloudplatform.github.io/agent-starter-pack/) for comprehensive guides and references!

🔍 **New to the codebase?** Explore the [CodeWiki](https://codewiki.google/github.com/googlecloudplatform/agent-starter-pack) for AI-powered code understanding and navigation.

- [Getting Started Guide](https://googlecloudplatform.github.io/agent-starter-pack/guide/getting-started) - First steps with agent-starter-pack
- [Installation Guide](https://googlecloudplatform.github.io/agent-starter-pack/guide/installation) - Setting up your environment
- [Deployment Guide](https://googlecloudplatform.github.io/agent-starter-pack/guide/deployment) - Taking your agent to production
- [Agent Templates Overview](https://googlecloudplatform.github.io/agent-starter-pack/agents/overview) - Explore available agent patterns
- [CLI Reference](https://googlecloudplatform.github.io/agent-starter-pack/cli/) - Command-line tool documentation


### Video Walkthrough:

- **[From Demo to Production with Agent Starter Pack](https://www.youtube.com/watch?v=mtJMYgJkTt8)**: Learn how the Agent Starter Pack acts as an Automated Architect, building the professional infrastructure for your AI project in seconds. Covers why most AI projects fail at deployment and how ASP automates Terraform, CI/CD, and observability.

- **[6-minute introduction](https://www.youtube.com/live/eZ-8UQ_t4YM?feature=shared&t=2791)** (April 2024): Explaining the Agent Starter Pack and demonstrating its key features. Part of the Kaggle GenAI intensive course.

Looking for more examples and resources for Generative AI on Google Cloud? Check out the [GoogleCloudPlatform/generative-ai](https://github.com/GoogleCloudPlatform/generative-ai) repository for notebooks, code samples, and more!

## Contributing

Contributions are welcome! See the [Contributing Guide](CONTRIBUTING.md).

## Feedback

We value your input! Your feedback helps us improve this starter pack and make it more useful for the community.

### Getting Help

If you encounter any issues or have specific suggestions, please first consider [raising an issue](https://github.com/GoogleCloudPlatform/generative-ai/issues) on our GitHub repository.

### Share Your Experience

For other types of feedback, or if you'd like to share a positive experience or success story using this starter pack, we'd love to hear from you! You can reach out to us at <a href="mailto:agent-starter-pack@google.com">agent-starter-pack@google.com</a>.

Thank you for your contributions!

## Disclaimer

This repository is for demonstrative purposes only and is not an officially supported Google product.

## Terms of Service

The agent-starter-pack templating CLI and the templates in this starter pack leverage Google Cloud APIs. When you use this starter pack, you'll be deploying resources in your own Google Cloud project and will be responsible for those resources. Please review the [Google Cloud Service Terms](https://cloud.google.com/terms/service-terms) for details on the terms of service associated with these APIs.
