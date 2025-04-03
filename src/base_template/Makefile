install:
	@command -v uv >/dev/null 2>&1 || { echo "uv is not installed. Installing uv..."; curl -LsSf https://astral.sh/uv/0.6.12/install.sh | sh; source ~/.bashrc; }
	uv sync --dev {% if cookiecutter.agent_name != 'live_api' %}--extra streamlit{%- endif %} --extra jupyter --frozen{% if cookiecutter.agent_name == 'live_api' %} && npm --prefix frontend install{%- endif %}

test:
	uv run pytest tests/unit && uv run pytest tests/integration

playground:
{%- if cookiecutter.deployment_target == 'cloud_run' %}
	uv run uvicorn app.server:app --host 0.0.0.0 --port 8000 --reload &
{%- endif %}
{%- if cookiecutter.agent_name == 'live_api' %}
	npm --prefix frontend start
{%- else %}
	{% if cookiecutter.deployment_target == 'agent_engine' %}PYTHONPATH=. {% endif %}uv run streamlit run frontend/streamlit_app.py --browser.serverAddress=localhost --server.enableCORS=false --server.enableXsrfProtection=false
{%- endif %}

backend:
{%- if cookiecutter.deployment_target == 'cloud_run' %}
	uv run uvicorn app.server:app --host 0.0.0.0 --port 8000 --reload
{%- elif cookiecutter.deployment_target == 'agent_engine' %}
	# Export dependencies to requirements file using uv export (preferred method), otherwise fall back to uv pip freeze
	uv export --no-hashes --no-sources --no-header --no-dev --no-emit-project --no-annotate --frozen > .requirements.txt 2>/dev/null || \
	uv pip freeze --exclude-editable > .requirements.txt && uv run app/agent_engine_app.py
{%- endif %}

{% if cookiecutter.deployment_target == 'cloud_run' -%}
ui:
{%- if cookiecutter.agent_name == 'live_api' %}
	npm --prefix frontend start
{%- else %}
	uv run streamlit run streamlit/streamlit_app.py --browser.serverAddress=localhost --server.enableCORS=false --server.enableXsrfProtection=false
{%- endif %}
{%- endif %}

setup-dev-env:
	@if [ -z "$$PROJECT_ID" ]; then echo "Error: PROJECT_ID environment variable is not set"; exit 1; fi
	(cd deployment/terraform/dev && terraform init && terraform apply --var-file vars/env.tfvars --var dev_project_id=$$PROJECT_ID --auto-approve)
{% if cookiecutter.data_ingestion %}
data-ingestion:
	@if [ -z "$$PROJECT_ID" ]; then echo "Error: PROJECT_ID environment variable is not set"; exit 1; fi
	$(MAKE) install
	(cd data_ingestion && uv run data_ingestion_pipeline/submit_pipeline.py \
		--project-id=$$PROJECT_ID \
		--region="us-central1" \
{%- if cookiecutter.datastore_type == "vertex_ai_search" %}
		--data-store-id="{{cookiecutter.project_name}}-datastore" \
		--data-store-region="us" \
{%- elif cookiecutter.datastore_type == "vertex_ai_vector_search" %}
		--vector-search-index="{{cookiecutter.project_name}}-vector-search" \
		--vector-search-index-endpoint="{{cookiecutter.project_name}}-vector-search-endpoint" \
		--vector-search-data-bucket-name="$$PROJECT_ID-{{cookiecutter.project_name}}-vs" \
{%- endif %}
		--service-account="{{cookiecutter.project_name}}-rag@$$PROJECT_ID.iam.gserviceaccount.com" \
		--pipeline-root="gs://$$PROJECT_ID-{{cookiecutter.project_name}}-rag" \
		--pipeline-name="data-ingestion-pipeline")
{%- endif %}

lint:
	uv run codespell
	uv run ruff check . --diff
	uv run ruff format . --check --diff
	uv run mypy .
