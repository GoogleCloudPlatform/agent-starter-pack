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
FROM golang:1.24-alpine AS builder

WORKDIR /app

# Copy go mod files
COPY go.mod go.sum* ./

# Download dependencies
RUN go mod download

# Copy source code
COPY main.go ./
COPY agent/ ./agent/

# Build the binary
RUN CGO_ENABLED=0 GOOS=linux go build -o /agent .

# Runtime stage
FROM gcr.io/distroless/static-debian12

COPY --from=builder /agent /agent

ARG COMMIT_SHA=""
ENV COMMIT_SHA=${COMMIT_SHA}

EXPOSE 8080

# Cloud Run sets PORT env var which ADK launcher reads automatically
# Supports REST API, A2A protocol, and Web UI
# API endpoints: /api/run_sse, /api/apps/...
# A2A endpoint: /a2a/invoke (JSON-RPC)
# Agent card: /.well-known/agent-card.json
# Web UI: /ui/ (requires IAP for authenticated access)
ENTRYPOINT ["/agent", "web", "api", "a2a", "webui"]
