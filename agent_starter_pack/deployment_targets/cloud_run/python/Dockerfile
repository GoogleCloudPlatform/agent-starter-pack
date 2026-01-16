# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

FROM python:3.11-slim

RUN pip install --no-cache-dir uv==0.8.13

{%- if cookiecutter.is_adk_live %}
# Install Node.js for frontend build
RUN apt-get update && apt-get install -y \
    curl \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*
{%- endif %}

WORKDIR /code

COPY ./pyproject.toml ./README.md ./uv.lock* ./

COPY ./{{cookiecutter.agent_directory}} ./{{cookiecutter.agent_directory}}

{%- if cookiecutter.is_adk_live %}
# Copy and build frontend
COPY ./frontend ./frontend
RUN cd frontend && npm ci && npm run build
{%- endif %}

RUN uv sync --frozen

ARG COMMIT_SHA=""
ENV COMMIT_SHA=${COMMIT_SHA}

ARG AGENT_VERSION=0.0.0
ENV AGENT_VERSION=${AGENT_VERSION}

EXPOSE 8080

CMD ["uv", "run", "uvicorn", "{{cookiecutter.agent_directory}}.fast_api_app:app", "--host", "0.0.0.0", "--port", "8080"]