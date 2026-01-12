Coding Agent guidance:
{%- if cookiecutter.language == "python" %}
{%- if cookiecutter.is_adk %}
{{ cookiecutter.adk_cheatsheet }}
{%- endif %}

For further reading on ADK, see: https://google.github.io/adk-docs/llms.txt
{%- elif cookiecutter.language == "go" %}

For ADK documentation, see: https://google.github.io/adk-docs/llms.txt
{%- endif %}
{{ cookiecutter.llm_txt }}
