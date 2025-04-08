# Project name used for resource naming
project_name = "{{ cookiecutter.project_name | replace('_', '-') }}"

# Your Dev Google Cloud project id
dev_project_id = "your-dev-project-id"

# The Google Cloud region you will use to deploy the infrastructure
region = "us-central1"

{%- if cookiecutter.data_ingestion %}
{%- if cookiecutter.datastore_type == "vertex_ai_search" %}
# The value can only be one of "global", "us" and "eu".
data_store_region = "us"
{%- elif cookiecutter.datastore_type == "vertex_ai_vector_search" %}
vector_search_shard_size = "SHARD_SIZE_SMALL"
vector_search_machine_type = "e2-standard-2"
vector_search_min_replica_count = 1
vector_search_max_replica_count = 1
{%- endif %}
{%- endif %}
