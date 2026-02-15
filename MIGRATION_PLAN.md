# Migration Plan (minimal disruption, ordered commits)

## Phase 0 — Preconditions

- Freeze direct model artifact commits in both repos (temporary branch protection rule).
- Create shared artifact ledger endpoint/store (append-only table + object storage bucket).

## Phase 1 — Interfaces first (no payload moves yet)

### Commit 1: Introduce shared contracts
- Add `schemas/build_manifest.schema.json`, `schemas/dataset_manifest.schema.json`, `schemas/artifact_receipt.schema.json`.
- Add `schemas/tool/rag.query.schema.json`, `schemas/tool/artifact.fetch.schema.json`, `schemas/tool/receipt.verify.schema.json`.
- Add versioned contract docs in both repos.

### Commit 2: Runtime consumes IDs + proofs only
- Update AGENTS_HOST tool invocations to accept `{index_id, artifact_id, commit}` instead of payloads.
- Add strict request/response validation against schemas.

## Phase 2 — Move pipelines/assets

### Commit 3: Relocate model pipelines to MODELS_HOST
- Move/port embedding ingestion, index build, and LoRA build code to MODELS_HOST.
- Keep compatibility shims in AGENTS_HOST that call remote MCP tools.

### Commit 4: Externalize binary assets
- Publish corpora/index snapshots/checkpoints to artifact store (`gs://...` or equivalent).
- Replace in-repo references with immutable `{artifact_id, uri, artifact_commit}` metadata.

## Phase 3 — Add enforcement gates

### Commit 5: CI boundary enforcement in AGENTS_HOST
- Add CI checks that fail on:
  - forbidden weight extensions (`*.safetensors`, `*.pt`, `*.bin`, `*.ckpt`, large `*.onnx`)
  - forbidden directories (`datasets/`, `corpus/`, `prompts_dump/`, `embeddings_dump/`)
  - vector snapshot signatures (faiss/qdrant/milvus artifacts)
  - files over size limit except explicit allowlist (`data/`, `artifacts/` if ignored)
  - static imports from model-training modules into runtime modules

### Commit 6: Add commitment generation and verification
- In MODELS_HOST pipelines, emit:
  - `dataset_manifest_commit = sha256(canonical_manifest_json)`
  - `build_manifest_commit   = sha256(canonical_build_json)`
  - `artifact_commit         = sha256(bytes)`
- Append to ledger and sign with CI identity.
- In AGENTS_HOST, enforce verification via `receipt.verify` before any retrieval/use.

## Phase 4 — Cutover and cleanup

### Commit 7: Remove deprecated local model paths from AGENTS_HOST
- Delete stale model pipeline code copies.
- Keep only contracts + client adapters.

### Commit 8: Enable mandatory policy gates
- Mark CI boundary jobs as required status checks.
- Enforce fail-closed behavior on missing proof/commit mismatch.

## Rollback strategy

- Keep interface compatibility layer for one release cycle.
- Rollback path = disable mandatory gate, continue using previous tool endpoint while preserving ledger writes.
