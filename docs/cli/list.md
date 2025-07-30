# list

List available agents and templates.

## Usage

```bash
uvx agent-starter-pack list [OPTIONS]
```

## Options

- `--source URL` - List templates from a specific repository
- `--adk` - List official ADK samples

## Examples

```bash
# List built-in agents
uvx agent-starter-pack list

# List ADK samples  
uvx agent-starter-pack list --adk

# List templates from repository
uvx agent-starter-pack list --source https://github.com/user/templates
```

## Notes

Only templates with `[tool.agent-starter-pack]` configuration in `pyproject.toml` appear in listings. Templates without this configuration still work with `create` but aren't discoverable.

## Related

- [`create`](./create.md) - Create agents from templates
- [Remote Templates](../remote-templates/) - Template documentation