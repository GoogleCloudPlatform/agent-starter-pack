# Recommendation: hard split to minimize contamination and token waste

## Chosen split

- **AGENTS_HOST:** `Q-Enterprises/core-orchestrator`
- **MODELS_HOST:** `adaptco/core-orchestrator`

## Why this minimizes context contamination

1. Runtime orchestration and policy gates remain in one lean control-plane repo.
2. Model-heavy churn (indexes, datasets, checkpoints, embedding exports) is isolated to a data-plane repo.
3. Agent prompts no longer risk accidental inclusion of corpora/index internals from co-located files.
4. CI/CD cadence can diverge safely: runtime hotfixes are not blocked by model pipeline rebuild cycles.

## Explicit AGENTS_HOST boundaries (forbidden content)

The following are forbidden in AGENTS_HOST:

- Model weights/checkpoints: `*.safetensors`, `*.pt`, `*.bin`, `*.ckpt`, `*.onnx` (above threshold)
- Corpora/data dumps: `datasets/`, `corpus/`, `prompts_dump/`, `embeddings_dump/`
- Vector snapshots: FAISS indexes, Qdrant snapshots, Milvus dumps
- Raw training/eval prompt dumps containing proprietary context
- Large binary artifacts not in explicit allowlist storage

## AGENTS_HOST allowed content

- Orchestrator logic, tool routers, MCP/A2A bridges
- Policy/theta gates and receipt verification logic
- Interface contracts: schemas, tool definitions, model/reference IDs
- Commit proofs + URIs + verdict summaries only

## MODELS_HOST responsibility boundary

- Dataset and build manifests
- Embedding pipelines and RAG index build jobs
- LoRA/training jobs and model registration metadata
- Publishing artifact commitments to append-only ledger
