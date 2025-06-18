test:
	uv run pytest tests

test-templated-agents:
	uv run pytest tests/integration/test_templated_patterns.py

test-e2e:
	set -a && . tests/cicd/.env && set +a && uv run pytest tests/cicd/test_e2e_deployment.py

generate-lock:
	uv run src/utils/generate_locks.py

lint:
	uv run ruff check . --config pyproject.toml --diff
	uv run ruff format . --check  --config pyproject.toml --diff
	uv run mypy --config-file pyproject.toml ./agents ./src/cli ./tests ./src/frontends/streamlit

lint-templated-agents:
	uv run tests/integration/test_template_linting.py

clean:
	rm -rf target/*

install:
	uv sync --dev --extra lint --frozen

docs-dev:
	cd docs && npm install && NODE_OPTIONS="--no-warnings" npm run docs:dev


