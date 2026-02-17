# Copyright 2026 Google LLC
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

{% if cookiecutter.bq_analytics -%}
import logging
{% endif -%}
import os

import google
import vertexai
from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.models import Gemini
{%- if cookiecutter.bq_analytics %}
from google.adk.plugins.bigquery_agent_analytics_plugin import (
    BigQueryAgentAnalyticsPlugin,
    BigQueryLoggerConfig,
)
from google.cloud import bigquery
{%- endif %}
{%- if cookiecutter.datastore_type == "vertex_ai_search" %}
from google.adk.tools import VertexAiSearchTool
{%- endif %}
from google.genai import types
{%- if cookiecutter.datastore_type == "vertex_ai_vector_search" %}

from {{cookiecutter.agent_directory}}.retrievers import search_collection
{%- endif %}

LLM_LOCATION = "global"
LOCATION = "us-central1"
LLM = "gemini-3-flash-preview"

credentials, project_id = google.auth.default()
os.environ["GOOGLE_CLOUD_PROJECT"] = project_id
os.environ["GOOGLE_CLOUD_LOCATION"] = LLM_LOCATION
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"

vertexai.init(project=project_id, location=LOCATION)

{% if cookiecutter.datastore_type == "vertex_ai_search" %}
# For integration tests, use a mock tool instead of the real Vertex AI Search
if os.getenv("INTEGRATION_TEST") == "TRUE":

    def vertex_search_tool(query: str) -> str:
        """Mock Vertex AI Search tool for integration tests."""
        return "Mock search result for testing purposes."

else:
    data_store_region = os.getenv("DATA_STORE_REGION", "global")
    data_store_id = os.getenv(
        "DATA_STORE_ID", "{{cookiecutter.project_name}}-collection_documents"
    )
    data_store_path = (
        f"projects/{project_id}/locations/{data_store_region}"
        f"/collections/default_collection/dataStores/{data_store_id}"
    )

    vertex_search_tool = VertexAiSearchTool(data_store_id=data_store_path)
{% elif cookiecutter.datastore_type == "vertex_ai_vector_search" %}
# For integration tests, use a mock function instead of the real Vector Search
if os.getenv("INTEGRATION_TEST") == "TRUE":

    def retrieve_docs(query: str) -> str:
        """Mock Vector Search tool for integration tests."""
        return "Mock vector search result for testing purposes."

else:
    vector_search_collection = os.getenv(
        "VECTOR_SEARCH_COLLECTION",
        f"projects/{project_id}/locations/{LOCATION}/collections/{{cookiecutter.project_name}}-collection",
    )

    def retrieve_docs(query: str) -> str:
        """
        Useful for retrieving relevant documents based on a query.
        Use this when you need additional information to answer a question.

        Args:
            query (str): The user's question or search query.

        Returns:
            str: Formatted string containing relevant document content.
        """
        try:
            return search_collection(
                query=query,
                collection_path=vector_search_collection,
            )
        except Exception as e:
            return (
                f"Calling retrieval tool with query:\n\n{query}\n\n"
                f"raised the following error:\n\n{type(e)}: {e}"
            )
{% endif %}

instruction = """You are an AI assistant for question-answering tasks.
Answer to the best of your ability using the context provided.
Leverage the Tools you are provided to answer questions.
If you already know the answer to a question, you can respond directly without using the tools."""


root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model="gemini-3-flash-preview",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=instruction,
{%- if cookiecutter.datastore_type == "vertex_ai_search" %}
    tools=[vertex_search_tool],
{%- elif cookiecutter.datastore_type == "vertex_ai_vector_search" %}
    tools=[retrieve_docs],
{%- endif %}
)

{%- if cookiecutter.bq_analytics %}

# Initialize BigQuery Analytics
_plugins = []
_project_id = os.environ.get("GOOGLE_CLOUD_PROJECT")
_dataset_id = os.environ.get("BQ_ANALYTICS_DATASET_ID", "adk_agent_analytics")
_location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")

if _project_id:
    try:
        bq = bigquery.Client(project=_project_id)
        bq.create_dataset(f"{_project_id}.{_dataset_id}", exists_ok=True)

        _plugins.append(
            BigQueryAgentAnalyticsPlugin(
                project_id=_project_id,
                dataset_id=_dataset_id,
                location=_location,
                config=BigQueryLoggerConfig(
                    gcs_bucket_name=os.environ.get("BQ_ANALYTICS_GCS_BUCKET"),
                    connection_id=os.environ.get("BQ_ANALYTICS_CONNECTION_ID"),
                ),
            )
        )
    except Exception as e:
        logging.warning(f"Failed to initialize BigQuery Analytics: {e}")
{%- endif %}

app = App(
    root_agent=root_agent,
    name="{{cookiecutter.agent_directory}}",
{%- if cookiecutter.bq_analytics %}
    plugins=_plugins,
{%- endif %}
)
