# Project name used for resource naming
project_name = "{{ cookiecutter.project_name | replace('_', '-') }}"

# Your Dev Google Cloud project id
dev_project_id = "your-dev-project-id"

# The Google Cloud region you will use to deploy the infrastructure
region = "us-central1"

{%- if cookiecutter.data_ingestion %}
{%- if cookiecutter.datastore_type == "vertex_ai_search" %}
# The value can only be one of "global", "us" and "eu".
data_store_region = "global"
{%- endif %}
{%- endif %}
