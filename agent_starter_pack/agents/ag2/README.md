# AG2 Multi-Agent Template

A multi-agent system template powered by [AG2](https://ag2.ai) (formerly AutoGen), an open-source framework with 500K+ monthly PyPI downloads.

## Overview

This template demonstrates a ReAct-style agent built with AG2, featuring:
- **Tool Use**: Decorator-based function registration for LLM tool calling
- **Multi-Agent Ready**: Easy to extend with GroupChat for multi-agent orchestration
- **Dual LLM Support**: Vertex AI (Gemini) by default, with Google API key fallback

## Architecture

```
User Message
    |
    v
+--------------+     +---------------+
|  UserProxy   |---->|  Assistant    |
|  (executor)  |<----|  (LLM agent)  |
+--------------+     +---------------+
    |                       |
    v                       v
+----------+         +----------+
|  Tools   |         |  Gemini  |
|  (Python |         |  / GPT   |
|  funcs)  |         |          |
+----------+         +----------+
```

## Quick Start

```bash
agent-starter-pack create my-agent --agent ag2
cd my-agent
make install
make playground
```

## Customization

- Add tools: Define functions with `@user_proxy.register_for_execution()` + `@assistant.register_for_llm()`
- Change model: Update `llm_config` in `app/agent.py`
- Multi-agent: Add GroupChat (see `notebooks/getting_started.ipynb`)

## Resources

- [AG2 Documentation](https://docs.ag2.ai)
- [AG2 GitHub](https://github.com/ag2ai/ag2)
- [Agent Starter Pack Docs](https://googlecloudplatform.github.io/agent-starter-pack/)
