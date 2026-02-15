# PR Plan (two PRs)

## PR1 — Enforce boundaries + tool surfaces

### Goal
Create hard AGENTS/MODELS interface boundaries before moving heavy assets.

### File list (planned)
**AGENTS_HOST (`Q-Enterprises/core-orchestrator`)**
- `schemas/tool/rag.query.schema.json` (new)
- `schemas/tool/artifact.fetch.schema.json` (new)
- `schemas/tool/receipt.verify.schema.json` (new)
- `schemas/build_manifest.schema.json` (new)
- `schemas/dataset_manifest.schema.json` (new)
- `scripts/ci/enforce_repo_boundaries.sh` (new)
- `.github/workflows/boundary-gates.yml` (new)
- `runtime/tool_clients/rag_client.py` (new)
- `runtime/tool_clients/artifact_client.py` (new)
- `runtime/tool_clients/receipt_client.py` (new)

### High-level diff summary
- Add strict schema contracts for all runtime-to-model interactions.
- Add CI gates for forbidden artifacts, directories, index snapshots, and file-size limits.
- Add static import scanner to prevent runtime importing training modules.
- Update runtime code to consume IDs/proofs rather than raw corpora/weights.

---

## PR2 — Move assets + wire commitments + CI attestation gates

### Goal
Relocate model/data pipelines and enforce proof-backed retrieval.

### File list (planned)
**MODELS_HOST (`adaptco/core-orchestrator`)**
- `pipelines/rag/build_index.py` (new or migrated)
- `pipelines/lora/train.py` (new or migrated)
- `pipelines/common/commitments.py` (new)
- `pipelines/common/canonicalize.py` (new)
- `ledger/append_only_writer.py` (new)
- `mcp_servers/rag_server.py` (new)
- `mcp_servers/artifact_server.py` (new)
- `.github/workflows/model-build-attest.yml` (new)

**AGENTS_HOST (`Q-Enterprises/core-orchestrator`)**
- `.github/workflows/runtime-proof-gate.yml` (new)
- `runtime/validators/proof_gate.py` (new)
- `runtime/tool_clients/*.py` (update)

### High-level diff summary
- Move/port RAG and LoRA build paths to MODELS_HOST.
- Emit `dataset_manifest_commit`, `build_manifest_commit`, `artifact_commit` for each build.
- Write commitments to append-only ledger and expose via MCP endpoints.
- Add runtime proof gate that fail-closes on missing or mismatched commitments.
