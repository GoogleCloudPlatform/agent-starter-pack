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

# Build stage
FROM node:20-slim AS builder

WORKDIR /workspace

# Copy package files
COPY package.json package-lock.json ./
RUN npm ci

# Copy source and build config
COPY {{cookiecutter.agent_directory}}/ ./{{cookiecutter.agent_directory}}/
COPY tsconfig.json ./
RUN npm run build

# Runtime stage
FROM node:20-slim AS runtime

WORKDIR /workspace

# Copy package files and install production deps only
COPY package.json package-lock.json ./
RUN npm ci --omit=dev

# Copy built application
COPY --from=builder /workspace/dist ./dist

ARG COMMIT_SHA=""
ENV COMMIT_SHA=${COMMIT_SHA}

ARG AGENT_VERSION=0.0.0
ENV AGENT_VERSION=${AGENT_VERSION}

EXPOSE 8080

# Use ADK devtools api_server with compiled JavaScript
CMD ["npx", "@google/adk-devtools", "api_server", "dist/agent.js", "--port", "8080"]
