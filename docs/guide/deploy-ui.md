# Deploying with a User Interface

This guide covers strategies for deploying agent applications with UIs to Google Cloud, focusing on approaches for development, testing, and demos.

### 1. Deployment Strategies

When deploying an application with both a backend and a frontend UI, two primary strategies exist.

#### A. Unified Deployment
*   **Description**: The backend and frontend are packaged and served from a single, unified service.
*   **Best For**: This approach is simpler and well-suited for **development and testing purposes**.
*   **Technology**: Google Cloud Run supports this model and can secure it with a single [Identity-Aware Proxy (IAP)](https://cloud.google.com/run/docs/securing/identity-aware-proxy-cloud-run) endpoint.

#### B. Decoupled Deployment
*   **Description**: The backend and frontend run as separate, independent services.
*   **Best For**: This is a more robust, **production-oriented** architecture.
*   **When to Use**: It becomes necessary if your backend technology is not suited for serving web frontends (e.g., if you are using a dedicated `Agent Engine`). In this case, the frontend is deployed separately to another Cloud Run service or to Cloud Storage.

::: tip Note
This guide focuses on the **Unified Deployment** strategy using Google Cloud Run, which is ideal for rapid development and internal testing.
:::

### 2. Deploy to Cloud Run with IAP

The deployment method depends on whether you are using a framework's built-in UI or a custom one.

#### A. Scenario 1: Built-In Framework UI
Many agent frameworks (like ADK) include a built-in web UI or "playground" ([`adk-web`](https://github.com/google/adk-web)) that is served alongside the backend API by default. This is useful for quickly exposing the service to other developers or testers.

**i. Deploy the Service:**
Navigate to your project's root directory and run the pre-configured `make` command:
```bash
make deploy IAP=true
```
This single command typically handles building the container, pushing it to a registry, deploying it to Cloud Run, and configuring IAP.

#### B. Scenario 2: Custom Frontend
If you have a separate, custom frontend (e.g., a React app for a `gemini_fullstack` agent or `adk_live`) and want to deploy it with the backend for testing, the process requires a custom container configuration.

**Strategy**: For development, modify the `Dockerfile` to build and run both the frontend's development server and the backend's API server within a single container.

> **Important:** This approach, especially running a frontend dev server like `npm run dev`, is intended **for development and testing purposes only**. For production, you should build static frontend assets and serve them efficiently.

**i. Configure the Dockerfile:**
Create or modify your `Dockerfile` to install both Python and Node.js dependencies and to launch both services concurrently.

::: details Example Dockerfile for combined backend and frontend
```dockerfile
FROM python:3.11-slim

# Install Node.js and npm
RUN apt-get update && apt-get install -y \
    nodejs \
    npm \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv==0.8.13

WORKDIR /code

# Copy backend files
COPY ./pyproject.toml ./README.md ./uv.lock* ./
COPY ./app ./app

# Copy frontend files
COPY ./frontend ./frontend

# Install dependencies
RUN uv sync --frozen && npm --prefix frontend install

EXPOSE 8000 5173

# Start both backend and frontend in parallel
CMD ["sh", "-c", "ALLOW_ORIGINS='*' uv run uvicorn app.server:app --host 0.0.0.0 --port 8000 & npm --prefix frontend run dev -- --host 0.0.0.0 & wait"]
```
:::


**ii. 🚀 Deploy the Combined Service:**
When deploying, you must instruct Cloud Run to direct traffic to the **frontend's port**. Pass the `PORT` variable to your `make` command. If your frontend runs on port `5173`, as in the example:
```bash
make deploy IAP=true PORT=5173
```
This ensures the public, IAP-protected URL serves your user interface.

### 3. Manage User Access
Once deployed, your Cloud Run service is protected by IAP, but no users are authorized to access it yet. You must grant the "httpsResourceAccessor" role to the appropriate users or Google Groups.

➡️ Follow the official Google Cloud documentation to manage access for your service: [Manage user or group access](https://cloud.google.com/run/docs/securing/identity-aware-proxy-cloud-run#manage_user_or_group_access).
