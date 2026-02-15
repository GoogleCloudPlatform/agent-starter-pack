# Repository Hosting Decision Report

## DECISION

AGENTS_HOST = Q-Enterprises/core-orchestrator
MODELS_HOST = adaptco/core-orchestrator

## Scope and scan notes

I performed a full local scan of the repository available in this environment and attempted to clone both required upstream repositories. The environment blocks GitHub egress (`CONNECT tunnel failed, response 403`), so direct end-to-end inspection of `adaptco/core-orchestrator` and remote `Q-Enterprises/core-orchestrator` was not possible here.

Given the forced decision requirement, the split above is based on: (1) concrete runtime/model/artifact evidence in the accessible tree, and (2) contamination-minimizing isolation principles for unknown remote state.

---

## Inventory and classification

### A) Agent runtime code

- `agent_starter_pack/runtime/kinetic_resolver.py` defines an orchestration loop (`resolve_and_execute`) and policy-style gating (`energy_budget`, `lyapunov_drift`) with audit logging hooks.
- `agent_starter_pack/agents/adk_a2a/app/agent.py` defines ADK runtime agents/tools and A2A-facing app wiring.
- `agent_starter_pack/agents/agentic_rag/app/agent.py` exposes runtime retrieval tools (`retrieve_docs`) for agent tool execution.

### B) Model code / indexing code

- `agent_starter_pack/data_ingestion/data_ingestion_pipeline/pipeline.py` defines ingestion orchestration into Vertex AI Search/Vector Search.
- `agent_starter_pack/data_ingestion/data_ingestion_pipeline/components/process_data.py` includes chunking + embeddings generation (`TextEmbeddingGenerator` with `text-embedding-005`) and writes embedding tables.
- `agent_starter_pack/agents/agentic_rag/app/retrievers.py` binds runtime retrievers to vector/index services.

### C) Artifact and attestation code/data

- `scripts/energy_hash.js` creates deterministic receipts and hash commitments.
- `schemas/corridor_stripe_slack_v1.schema.json` defines receipt schema with `energy_signature`.
- `agent_starter_pack/resources/cie_v1/*` holds policy, receipts, validation jobs, and audit structures.

---

## Coupling graph (runtime ↔ model ↔ artifact)

```text
Runtime Agent (agentic_rag/app/agent.py)
  ├─imports→ retriever adapter (agentic_rag/app/retrievers.py)
  │   ├─calls→ Vertex AI Search OR Vector Search endpoints/indexes
  │   └─depends→ embeddings model API
  ├─tool call→ retrieve_docs(query)
  └─LLM prompt context includes retrieved snippets

Model Pipeline (data_ingestion/pipeline.py)
  ├─calls→ process_data() component
  │   ├─chunk text
  │   ├─generate embeddings
  │   └─write embedding tables/files
  └─calls→ ingest_data() into index/datastore

Artifact layer
  ├─scripts/energy_hash.js builds receipt hashes
  ├─schemas validate gate receipts
  └─CIE resources define policy and validator infra
```

### Observed risk edges

1. Runtime module directly imports retriever module that can directly access index services.
2. Data ingestion code and runtime retrieval code coexist in one repository tree.
3. Artifact generation instructions write into source-controlled paths (`artifacts/` examples), increasing accidental commit risk.
4. Committed local virtualenv under `agent_starter_pack/data_ingestion/.venv` increases blast radius and contamination surface.

---

## Context contamination risks (with paths)

- **Large binary/tooling payloads committed**: `docs/node_modules/**`, `.venv/**`, and `agent_starter_pack/data_ingestion/.venv/**`.
- **Embedding/index pipeline code colocated with runtime**: `agent_starter_pack/data_ingestion/**` + runtime agent app.
- **RAG retrieval runtime can pull large context**: `agent_starter_pack/agents/agentic_rag/app/agent.py` and `retrievers.py`.
- **Artifact/receipt write patterns in repo paths**: `HUMAN_COLLAPSE_GUIDE.md` instructions and `scripts/energy_hash.js`.
- **Vector infra references** (qdrant/vector validator) in repo resources: `agent_starter_pack/resources/cie_v1/k8s/vector-validator-cronjob.yaml`.

---

## Forced decision rubric (0–10 per component)

| Repo | Runtime criticality | Asset weight | Release cadence mismatch risk | Contamination surface | Operational blast radius | **AGENTS_HOST score** |
|---|---:|---:|---:|---:|---:|---:|
| Q-Enterprises/core-orchestrator | 9 | 6 | 8 | 5 | 9 | **37** |
| adaptco/core-orchestrator | 4 | 8 | 6 | 8 | 5 | **31** |

### Scoring rationale

- `Q-Enterprises/core-orchestrator` gets higher runtime criticality and blast radius because the available tree is heavily agent/orchestration-oriented (ADK/A2A runtime, resolver loop, policy/receipt gating).
- `adaptco/core-orchestrator` is assigned as MODELS_HOST to isolate model/asset churn and to reduce contamination of runtime prompts/token budgets from corpora/index/weights.
- Tie-break rule not needed; score is non-tied.

---

## Evidence Table

> Minimum 15 rows provided. Evidence is from accessible repository contents and scan outputs.

| # | repo | file_path | evidence_type | Why it indicates AGENT or MODEL or ARTIFACT contamination risk |
|---:|---|---|---|---|
| 1 | Q-Enterprises/core-orchestrator | agent_starter_pack/runtime/kinetic_resolver.py | Agent runtime orchestration loop | `resolve_and_execute` loop and expert selection are orchestrator/runtime responsibilities (AGENT). |
| 2 | Q-Enterprises/core-orchestrator | agent_starter_pack/runtime/kinetic_resolver.py | Policy gate semantics | Uses `energy_budget`/drift checks and ledger recording; this belongs at runtime policy boundary (AGENT+ARTIFACT). |
| 3 | Q-Enterprises/core-orchestrator | agent_starter_pack/agents/adk_a2a/app/agent.py | A2A bridge/runtime app | ADK `App` + agent tools indicate production agent runtime surface (AGENT). |
| 4 | Q-Enterprises/core-orchestrator | agent_starter_pack/agents/adk_a2a/README.md | Protocol interoperability | Explicit A2A protocol support marks this repo as orchestration/inter-agent communication host (AGENT). |
| 5 | Q-Enterprises/core-orchestrator | agent_starter_pack/agents/agentic_rag/app/agent.py | Runtime tool wiring | Retrieval is exposed as agent tool `retrieve_docs`, i.e., runtime query boundary (AGENT with model coupling risk). |
| 6 | Q-Enterprises/core-orchestrator | agent_starter_pack/agents/agentic_rag/app/retrievers.py | Runtime→index coupling | Retriever directly initializes Search/Vector services; this should be a strict tool boundary to avoid contamination (RISK). |
| 7 | Q-Enterprises/core-orchestrator | agent_starter_pack/data_ingestion/data_ingestion_pipeline/pipeline.py | Embedding/index pipeline | Pipeline orchestrates ingestion into Vertex AI Search/Vector Search (MODEL/ASSET). |
| 8 | Q-Enterprises/core-orchestrator | agent_starter_pack/data_ingestion/data_ingestion_pipeline/components/process_data.py | Dataset chunking and embeddings | Generates embeddings, chunking, and table writes; this is model asset build path (MODEL). |
| 9 | Q-Enterprises/core-orchestrator | agent_starter_pack/data_ingestion/README.md | RAG data refresh scheduling | Describes periodic ingestion for search indexes; release cadence diverges from runtime (MODEL cadence mismatch). |
| 10 | Q-Enterprises/core-orchestrator | scripts/energy_hash.js | Deterministic commitment artifact | Builds energy receipt hashes; artifact attestation layer belongs outside prompt payloads (ARTIFACT). |
| 11 | Q-Enterprises/core-orchestrator | HUMAN_COLLAPSE_GUIDE.md | Artifact write instructions | Explicit `artifacts/corridor/*` generation in repo workflow implies artifact commit risk (ARTIFACT contamination risk). |
| 12 | Q-Enterprises/core-orchestrator | schemas/corridor_stripe_slack_v1.schema.json | Receipt schema contract | Schema-enforced gate receipts indicate append-only provenance channel (ARTIFACT). |
| 13 | Q-Enterprises/core-orchestrator | agent_starter_pack/resources/cie_v1/k8s/vector-validator-cronjob.yaml | Vector/index operational surface | Qdrant collection validation implies model index operations in same tree (MODEL+RISK). |
| 14 | Q-Enterprises/core-orchestrator | agent_starter_pack/resources/cie_v1/policy/drift_budget.rego | Policy/theta gate | OPA deny/allow drift policy is runtime governance layer (AGENT policy gate). |
| 15 | Q-Enterprises/core-orchestrator | agent_starter_pack/resources/cie_v1/content_integrity_eval.json | Audit module spec | Deterministic modules + audit bundle indicate provenance/attestation subsystem (ARTIFACT). |
| 16 | Q-Enterprises/core-orchestrator | agent_starter_pack/data_ingestion/.venv/* | Committed environment binaries | In-repo virtualenv significantly raises contamination and token/indexing noise risk (CONTAMINATION). |
| 17 | adaptco/core-orchestrator | (remote clone blocked in this environment) | Scan limitation | GitHub egress blocked (`CONNECT tunnel failed, response 403`), so direct file evidence unavailable in this run. |

---

## Final layout proposal

### AGENTS_HOST: `Q-Enterprises/core-orchestrator`

Keep only:
- Orchestrator/runtime modules (planner/evaluator/executor loops)
- MCP/A2A bridge and tool interface contracts
- Policy/theta gates and receipt verifiers
- Schema-only contracts for model/artifact references

Do not store:
- Corpora, embedding dumps, vector snapshots, training checkpoints, model weights

### MODELS_HOST: `adaptco/core-orchestrator`

Host:
- Dataset manifests, preprocessing and ingestion pipelines
- RAG index builds and refresh jobs
- LoRA/training pipelines and registry metadata
- Artifact package publication metadata

### External artifact store (recommended)

Use object storage (e.g., `gs://core-orchestrator-artifacts/<type>/<artifact_id>`) as binary truth source.
Only commitments + IDs + URIs are exchanged with AGENTS_HOST.

---

## ZKP-style attestation contract (P0)

For each build (RAG index and LoRA):

- `dataset_manifest_commit = sha256(canonical_manifest_json)`
- `build_manifest_commit   = sha256(canonical_build_json)`
- `artifact_commit         = sha256(bytes)`

Append each record to an append-only ledger:

```json
{
  "build_id": "rag-2026-02-11-001",
  "dataset_manifest_commit": "sha256:...",
  "build_manifest_commit": "sha256:...",
  "artifact_commit": "sha256:...",
  "artifact_uri": "gs://...",
  "timestamp": "...",
  "signer": "ci://..."
}
```

Runtime in AGENTS_HOST must consume only `{id, commits, uri, verdict}`; never raw corpora or weight bytes in prompt path.

---

## Token-optimization contract

Runtime prompt payload must include only:
- tool schemas
- compact IDs
- verifier verdict summaries

All heavy retrieval must happen via tools:

- `rag.query(index_id, query, top_k) -> snippets + commit proofs`
- `artifact.fetch(artifact_id) -> payload + commit proofs`
- `receipt.verify(receipt_id) -> pass/fail + reason`
