# Stage 1: Builder - Prepare APT repositories
FROM ghcr.io/astral-sh/uv:0.9.18-python3.11-bookworm-slim AS builder

# Install tools needed to add repositories
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    gnupg && \
    # GitHub CLI
    curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | gpg --dearmor -o /usr/share/keyrings/githubcli-archive-keyring.gpg && \
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" > /etc/apt/sources.list.d/github-cli.list && \
    # Google Cloud SDK
    curl -sS https://packages.cloud.google.com/apt/doc/apt-key.gpg | gpg --dearmor -o /usr/share/keyrings/cloud.google.gpg && \
    echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" > /etc/apt/sources.list.d/google-cloud-sdk.list && \
    # Terraform
    curl -fsSL https://apt.releases.hashicorp.com/gpg | gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg && \
    echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com bookworm main" > /etc/apt/sources.list.d/hashicorp.list && \
    # Clean up builder stage
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Stage 2: Final Image
FROM ghcr.io/astral-sh/uv:0.9.18-python3.11-bookworm-slim

# Copy repository configurations from the builder stage
COPY --from=builder /etc/apt/sources.list.d/ /etc/apt/sources.list.d/
COPY --from=builder /usr/share/keyrings/ /usr/share/keyrings/

# Install the final packages
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    curl \
    gh \
    google-cloud-cli \
    terraform \
    make \
    nodejs \
    npm && \
    # Clean up apt cache
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install Go
ARG GO_VERSION=1.24.3
RUN curl -fsSL https://go.dev/dl/go${GO_VERSION}.linux-amd64.tar.gz | tar -C /usr/local -xz
ENV PATH="/usr/local/go/bin:${PATH}"