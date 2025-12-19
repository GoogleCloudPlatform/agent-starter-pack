# 🌟 Community Showcase

Welcome to the Agent Starter Pack Community Showcase! This page highlights amazing projects, implementations, and creative uses of the Agent Starter Pack by our community.

## 🔍 Explore Community Projects

**[Browse all community agents on GitHub →](https://github.com/search?q=Agent+generated+with+%5B%60googleCloudPlatform%2Fagent-starter-pack%60%5D&type=code)**

Discover how developers are using our templates in real-world applications.

## Featured Projects

### Sherlock by [Devoteam](https://devoteam.com/)
**Repository:** [jasonquekavalon/agentic-era-hack](https://github.com/jasonquekavalon/agentic-era-hack)
**Video:** [Building an AI Agent for error log detection and remediation at the Agentic Era Hackathon](https://www.youtube.com/watch?v=i_nb9EpTVF0)

An intelligent log analysis agent for enterprises with large application landscapes that generate massive volumes of log entries. Sherlock investigates log entries with varying warning levels and messages, automatically creates Jira tickets prioritized by severity, and can even detect issues during microservice version rollouts and trigger automatic rollbacks on Cloud Run.

### Smart Learning Platform by [tensr](https://tensr.be/)
**Repository:** [jossehuybrechts/smart-learning](https://github.com/jossehuybrechts/smart-learning)
**Blog Post:** [Building a Smart Learning Platform with Google's Agent Starter Pack](https://medium.com/@tensr/9f75876bc618)

An intelligent learning platform that adapts to individual learning styles and provides personalized educational content. This project demonstrates how to build a production-ready educational AI agent using the Agent Starter Pack's templates and deployment infrastructure.

### Production Monitoring Assistant by [norma](https://norma.dev/)
**Repository:** [adilmoumni/prod-monitoring-assistant](https://github.com/adilmoumni/prod-monitoring-assistant)
**Blog Post:** [Building an AI Agent for Production Monitoring at the Agentic Era Hackathon](https://medium.com/norma-dev/building-an-ai-agent-for-production-monitoring-at-the-agentic-era-hackathon-ffa283dd391d)

An AI-powered production monitoring assistant built for the Agentic Era Hackathon. This agent helps DevOps teams monitor system health, detect anomalies, and provide intelligent insights for maintaining production environments.

### Bob's Brain
**Repository:** [jeremylongshore/bobs-brain](https://github.com/jeremylongshore/bobs-brain)

A production-grade multi-agent system built entirely with Google's Agent Development Kit (ADK) and Vertex AI Agent Engine. Bob's Brain demonstrates advanced ADK patterns including agent-to-agent (A2A) protocol, comprehensive CI/CD with ARV gates, and Terraform-first infrastructure.

**Key Features:**
- **Multi-Agent Architecture:** Orchestrator (bob) + foreman (iam-senior-adk-devops-lead) + 8 specialist agents
- **A2A Protocol:** Full AgentCard implementation with foreman-worker pattern
- **Hard Mode Rules:** R1-R8 compliance enforcement (ADK-only, drift detection, WIF authentication)
- **CI/CD Excellence:** 8 GitHub Actions workflows with ARV validation gates and multi-stage approvals
- **Documentation:** 141 organized docs including 20+ canonical standards (6767-series) reusable across repos
- **Production Patterns:** Inline source deployment, smoke testing, comprehensive error handling

**Technologies:** ADK, Vertex AI Agent Engine, Cloud Run, Terraform, GitHub Actions (WIF), Firestore
**Deployment:** Agent Engine (inline source) + Cloud Run (A2A gateways + Slack webhook)

This project serves as a reference implementation for production-grade ADK agent departments with enterprise CI/CD practices.

### Google Chat ADK Agent Add-on by [Google Workspace](https://developers.google.com/workspace)
**Repository:** [googleworkspace/add-ons-samples](https://github.com/googleworkspace/add-ons-samples/tree/main/apps-script/chat/adk-ai-agent)
**Tutorial:** [Build a Google Chat app with an ADK AI agent](https://developers.google.com/workspace/add-ons/chat/quickstart-adk-agent)

A Google Workspace add-on that brings AI-powered fact-checking to Google Chat using an ADK agent hosted in Vertex AI Agent Engine. Users can send statements like "The Eiffel Tower was completed in 1900" and the LLM Auditor multi-agent will critique and revise facts using Gemini and Google Search grounding.

**Key Features:**

- **Quick Deployment:** Deploy the LLM Auditor ADK sample via Agent Starter Pack from GCP console with Cloud Shell
- **Fact-Checking Agent:** Multi-agent system that autonomously critiques statements and provides corrections with sources
- **Custom Chat Integration:** Reference implementation for building Google Chat apps that interface with Vertex AI agents

**Technologies:** ADK, Vertex AI Agent Engine, Apps Script, Google Chat API, Google Workspace Add-ons

---

*This section will be updated regularly as we review and feature outstanding community submissions.*

## 📝 Submit Your Project

Built something amazing with the Agent Starter Pack? **[Create a showcase issue](https://github.com/GoogleCloudPlatform/agent-starter-pack/issues/new?labels=showcase)** with your repository URL, project description, and unique features.
