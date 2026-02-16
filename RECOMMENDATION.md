# Recommendation: branch-first enterprise delivery with a stable AI adapter

## Default operating model for client engagements

For initial discovery, proof-of-concept, and first production candidate work, keep implementation in the current repository on a dedicated feature branch:

- **Branch:** `feat/charlie-fox-enterprise`

Only move to a separate repository when one of these is true:

1. The client requires separate legal or security ownership boundaries.
2. The client needs independent billing/access governance.
3. The work has a distinct long-term product lifecycle.

## Stability principle: keep the model behind an adapter

Treat the LLM provider as replaceable infrastructure. Keep business logic and workflows model-agnostic by using a provider interface.

### Why this matters

- The client system remains stable if model vendors or versions change.
- Switching providers becomes a config and integration task, not a platform rewrite.
- Reliability controls (timeouts, retries, fallback) stay centralized.

## Client-safe architecture (recommended)

### 1) Application Layer (stable)

- Business workflows (onboarding steps, approvals, policies)
- RBAC, tenant isolation, and audit logging
- Prompt templates with explicit versioning

### 2) Orchestrator Layer

- Routes user intent to tools, RAG, or worker agents
- Enforces guardrails, policy checks, and escalation logic

### 3) Multimodal RAG Layer

- Ingestion pipelines for docs, images, video transcripts, and SOPs
- Embeddings with metadata filtering by role and tenant
- Retrieval + reranking + citation output

### 4) LLM Provider Layer

- ChatGPT (or other provider) behind a provider interface
- Timeouts, retries, circuit breakers, and fallback model policy

## Multi-user prompting without destabilizing core behavior

Do **not** let user prompts mutate global system behavior directly.

Version and govern these assets explicitly:

- System prompts
- Tool definitions
- Retrieval policies
- Worker-agent playbooks

Roll out with staging and canary releases before production.

## Evaluation and quality gates

Maintain an eval suite that runs before promotion:

- Task accuracy
- Hallucination rate
- Policy and compliance adherence
- Safety/regulatory checks where applicable

## Client-facing language (proposal-ready)

Use concise statements such as:

- “We will keep the intelligence layer modular and governed.”
- “Your business logic stays stable even as model capabilities evolve.”
- “Multi-user access is controlled through enterprise permissions and auditability.”

## Optional extension: autonomous Unity RL pipeline

If the engagement includes game AI or simulation training, add a dedicated MLOps track:

1. Generate Unity C# behavior scripts from scoped specs.
2. Build Unity environments headlessly.
3. Train RL agents continuously (offline + online fine-tuning).
4. Register and version models for deployment.
5. Schedule nightly or continuous retraining with monitoring.

This should still follow the same adapter and governance model used above.
