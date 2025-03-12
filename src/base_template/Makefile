install:
	@command -v uv >/dev/null 2>&1 || { echo "uv is not installed. Installing uv..."; curl -LsSf https://astral.sh/uv/install.sh | sh; source ~/.bashrc; }
	uv sync --dev {% if cookiecutter.agent_name != 'multimodal_live_api' %}--extra streamlit{%- endif %} --extra jupyter --frozen{% if cookiecutter.agent_name == 'multimodal_live_api' %} && npm --prefix frontend install{%- endif %}

test:
	uv run pytest tests/unit && uv run pytest tests/integration

playground:
{%- if cookiecutter.deployment_target == 'cloud_run' %}
	uv run uvicorn app.server:app --host 0.0.0.0 --port 8000 --reload &
{%- endif %}
{%- if cookiecutter.agent_name == 'multimodal_live_api' %}
	npm --prefix frontend start
{%- else %}
	{% if cookiecutter.deployment_target == 'agent_engine' %}PYTHONPATH=. {% endif %}uv run streamlit run frontend/streamlit_app.py --browser.serverAddress=localhost --server.enableCORS=false --server.enableXsrfProtection=false
{%- endif %}

backend:
{%- if cookiecutter.deployment_target == 'cloud_run' %}
	uv run uvicorn app.server:app --host 0.0.0.0 --port 8000 --reload
{%- elif cookiecutter.deployment_target == 'agent_engine' %}
	uv export --no-hashes --no-sources --no-header --no-emit-project --frozen > .requirements.txt && uv run app/agent_engine_app.py
{%- endif %}

{% if cookiecutter.deployment_target == 'cloud_run' -%}
ui:
{%- if cookiecutter.agent_name == 'multimodal_live_api' %}
	npm --prefix frontend start
{%- else %}
	uv run streamlit run streamlit/streamlit_app.py --browser.serverAddress=localhost --server.enableCORS=false --server.enableXsrfProtection=false
{%- endif %}
{%- endif %}

setup-dev-env:
	@if [ -z "$$PROJECT_ID" ]; then echo "Error: PROJECT_ID environment variable is not set"; exit 1; fi
	(cd deployment/terraform/dev && terraform init && terraform apply --var-file vars/env.tfvars --var dev_project_id=$$PROJECT_ID --auto-approve)

{%- if cookiecutter.data_ingestion%}
data-ingestion:
	@if [ -z "$$PROJECT_ID" ]; then echo "Error: PROJECT_ID environment variable is not set"; exit 1; fi
	$(MAKE) install
	(cd data_ingestion && uv run data_ingestion_pipeline/submit_pipeline.py \
		--project-id=$$PROJECT_ID \
		--data-store-id="sample-datastore" \
		--region="us-central1" \
		--data-store-region="us" \
		--service-account="vertexai-pipelines-sa@$$PROJECT_ID.iam.gserviceaccount.com" \
		--pipeline-root="gs://$$PROJECT_ID-pipeline-artifacts" \
		--pipeline-name="data-ingestion-pipeline")
{%- endif %}

lint:
	uv run codespell
	uv run ruff check . --diff
	uv run ruff format . --check --diff
	uv run mypy .
