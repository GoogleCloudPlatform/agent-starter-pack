# Remote Templates

Remote templates turn your agent prototype into a production-ready starter pack. A remote template is a Git repository containing your custom agent logic, dependencies, and infrastructure definitions (Terraform). The `agent-starter-pack` CLI uses it to generate a complete, deployable application by automatically adding production-grade boilerplate for testing and multi-target deployment (e.g., Cloud Run, Agent Engine).

## Choose Your Path

### 🚀 Using Remote Templates
**For developers who want to use existing templates**

Use any Git repository as a template to create production-ready agents instantly. Perfect for getting started quickly or using community-created templates.

**[👉 Go to Using Remote Templates Guide](./using-remote-templates.md)**

Quick example:
```bash
uvx agent-starter-pack create my-agent -a adk@gemini-fullstack
```

---

### 🛠️ Creating Remote Templates  
**For developers who want to share their own templates**

Package your custom agent logic, dependencies, and infrastructure into reusable templates that others can use. Perfect for sharing best practices and creating standardized agent patterns.

**[👉 Go to Creating Remote Templates Guide](./creating-remote-templates.md)**

Quick example:
```bash
# After creating your template repository
uvx agent-starter-pack create test-agent -a https://github.com/you/your-template
```

---

## Overview

Remote templates work by:
1. **Fetching** template repositories from Git
2. **Version locking** - automatically uses the exact starter pack version specified by the template for guaranteed compatibility
3. **Applying** intelligent defaults based on repository structure  
4. **Merging** template files with base agent infrastructure
5. **Generating** complete, production-ready agent projects

Any Git repository can become a template - the system handles the complexity automatically.

## Related Documentation

- **[Using Remote Templates](./using-remote-templates.md)** - Complete guide for template users
- **[Creating Remote Templates](./creating-remote-templates.md)** - Complete guide for template authors  
- **[Template Config Reference](../guide/template-config-reference.md)** - All available configuration options
- **[create CLI](../cli/create.md)** - Command line reference for creating agents
- **[enhance CLI](../cli/enhance.md)** - Command line reference for enhancing projects