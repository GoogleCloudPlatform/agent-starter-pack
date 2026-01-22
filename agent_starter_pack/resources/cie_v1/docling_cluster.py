from dataclasses import dataclass
from typing import Any, Dict, List
import time
import uuid


@dataclass
class DriftReceipt:
    drift_id: str
    store: str
    collection: str
    drift_class: str
    sample_size: int
    counts: Dict[str, int]
    qdrant_ref: Dict[str, Any]


@dataclass
class DocBlock:
    block_id: str
    doc_ids: List[str]
    drift_class: str
    collection: str
    created_at_utc: float


@dataclass
class RagBatchSpec:
    batch_id: str
    collection: str
    drift_id: str
    blocks: List[DocBlock]
    objective: str  # e.g. "REDUCE_DRIFT", "IMPROVE_RECALL"
    created_at_utc: float


def build_doc_blocks_from_drift(receipt: DriftReceipt, block_size: int = 32) -> List[DocBlock]:
    sample_ids = receipt.qdrant_ref.get("sample_ids", [])
    blocks: List[DocBlock] = []

    for i in range(0, len(sample_ids), block_size):
        chunk = sample_ids[i : i + block_size]
        if not chunk:
            continue
        blocks.append(
            DocBlock(
                block_id=str(uuid.uuid4()),
                doc_ids=chunk,
                drift_class=receipt.drift_class,
                collection=receipt.collection,
                created_at_utc=time.time(),
            )
        )
    return blocks


def build_rag_batch_spec(receipt: DriftReceipt, objective: str = "REDUCE_DRIFT") -> RagBatchSpec:
    blocks = build_doc_blocks_from_drift(receipt)
    return RagBatchSpec(
        batch_id=f"rag-batch-{receipt.drift_id}",
        collection=receipt.collection,
        drift_id=receipt.drift_id,
        blocks=blocks,
        objective=objective,
        created_at_utc=time.time(),
    )


# Example wiring:
# 1. Ingest DriftReceipt.v1 (JSON) → DriftReceipt dataclass
# 2. Call build_rag_batch_spec(receipt)
# 3. Hand RagBatchSpec to your RAG/LoRA pipeline (GitHub Action, Qube job, etc.)
