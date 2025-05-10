# Data Ingestion Pipeline for RAG

The Agent Starter Pack simplifies incorporating data ingestion into your agent projects. This is especially useful for agents requiring document processing and retrieval, such as Retrieval Augmented Generation (RAG) applications.

## Overview

Data ingestion automates:

-   Loading data from various sources.
-   Processing and chunking documents.
-   Generating embeddings with Vertex AI.
-   Storing processed data and embeddings in **Vertex AI Search** or **Vertex AI Vector Search**.
-   Scheduling periodic data updates.

## When to Include Data Ingestion

Consider data ingestion if:

-   Your agent needs to search or reference extensive documentation.
-   You're developing a RAG-based application.
-   Your agent's knowledge base requires periodic updates.
-   You want to keep your agent's content fresh and searchable.

## Usage

### Project Creation

Include data ingestion during project creation in two ways:

1.  **Automatic Inclusion**: Some agents (e.g., those designed for RAG like `agentic_rag`) automatically include it due to their nature. You will be prompted to select a datastore (`vertex_ai_search` or `vertex_ai_vector_search`) if not specified.

2.  **Optional Inclusion**: For other agents, add it using the `--include-data-ingestion` flag and specify the desired datastore with `--datastore` (or `-ds`):

    ```bash
    # Using Vertex AI Search
    agent-starter-pack create my-agent-project --include-data-ingestion -ds vertex_ai_search

    # Using Vertex AI Vector Search
    agent-starter-pack create my-agent-project --include-data-ingestion -ds vertex_ai_vector_search
    ```
    If `--datastore` is omitted when `--include-data-ingestion` is used, you will be prompted to choose one.

### Infrastructure Setup

The Terraform IaC configures the necessary infrastructure based on your chosen datastore:

-   **Vertex AI Search**: Datastores.
-   **Vertex AI Vector Search**: Indexes, Index Endpoints, and Buckets for staging data.
-   Necessary service accounts and permissions.
-   Storage buckets for pipeline artifacts.
-   BigQuery datasets (if applicable).

## Getting Started

1.  Create your project with data ingestion, specifying your datastore:

    ```bash
    # Example with Vertex AI Search
    agent-starter-pack create my-project -ds vertex_ai_search

    # Example with Vertex AI Vector Search
    agent-starter-pack create my-project -ds vertex_ai_vector_search
    ```

2.  Follow the setup instructions in the generated `data_ingestion/README.md`. Deploy the Terraform infrastructure (at least in your development project) before running the data pipeline.

## Learn More

-   [Vertex AI Pipelines](https://cloud.google.com/vertex-ai/docs/pipelines/introduction) for pipeline management.
-   [Vertex AI Search documentation](https://cloud.google.com/generative-ai-app-builder/docs/enterprise-search-introduction) for search capabilities.
-   [Vertex AI Vector Search documentation](https://cloud.google.com/vertex-ai/docs/vector-search/overview) for vector database capabilities.
