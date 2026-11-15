# Agent Starter Pack is now Agents CLI

Agent Starter Pack has been replaced by [Agents CLI](https://github.com/google/agents-cli).

Since version 1.0.0, the `agent-starter-pack` package installs `google-agents-cli`, and the `agent-starter-pack` command runs `agents-cli`:

```bash
uvx google-agents-cli create my-agent
```

Some commands and options were renamed. Run `agents-cli --help`, or see the [Agents CLI docs](https://github.com/google/agents-cli).

| Agent Starter Pack | Agents CLI |
|---|---|
| `create` | `create` (or `scaffold create`) |
| `-d agent_engine` | `-d agent_runtime` |
| `enhance` | `scaffold enhance` |
| `upgrade` | `scaffold upgrade` |
| `setup-cicd` | `infra cicd` |
| `register-gemini-enterprise` | `publish gemini-enterprise` |

The last Agent Starter Pack release is [v0.41.3](https://github.com/GoogleCloudPlatform/agent-starter-pack/tree/v0.41.3). It is no longer maintained.
