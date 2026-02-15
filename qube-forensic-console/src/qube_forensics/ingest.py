from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import json
from typing import Dict, Any
from .hashing import sha256_hex_from_obj
from .validate import load_schema, validate_or_raise
from .emit_ndjson import append_ndjson

SEAL_PHRASE = "Canonical truth, attested and replayable."
EMBED_DIM_CANON = 1536

@dataclass(frozen=True)
class IngestConfig:
    forensic_schema_path: Path
    telemetry_schema_path: Path
    telemetry_store_path: Path
    source_system: str = "QUBE_FORensics"
    payload_type: str = "qube_forensic_report.v1"

def ingest_forensic_report(report: Dict[str, Any], *, session_id: str, cfg: IngestConfig) -> Dict[str, Any]:
    forensic_schema = load_schema(cfg.forensic_schema_path)
    telemetry_schema = load_schema(cfg.telemetry_schema_path)

    # 1) Validate report
    validate_or_raise(report, forensic_schema)

    # 2) Enforce frozen contract invariants
    if report.get("embeddingDimension") != EMBED_DIM_CANON:
        raise ValueError(f"embeddingDimension must be {EMBED_DIM_CANON}")

    gov = report.get("governance", {})
    if gov.get("sealPhrase") != SEAL_PHRASE:
        raise ValueError("sealPhrase mismatch")

    # 3) Build telemetry event (SSOT append-only)
    case_id = report["caseId"]
    event: Dict[str, Any] = {
        "schemaVersion": "telemetry.event.v1",
        "eventKey": f"forensic.report.ingested::{case_id}",
        "sessionId": session_id,
        "timestamp": report["timestamp"],
        "sourceSystem": cfg.source_system,
        "payloadType": cfg.payload_type,
        "payload": report,
        "sealPhrase": SEAL_PHRASE,
        "lineage": {
            "caseId": case_id,
            "kernel": report.get("kernel"),
            "computeNode": report.get("computeNode", {}).get("model")
        }
    }

    # 4) Canonical hash (exclude canonicalHash field itself)
    tmp = dict(event)
    tmp.pop("canonicalHash", None)
    event["canonicalHash"] = sha256_hex_from_obj(tmp)

    # 5) Validate telemetry envelope
    validate_or_raise(event, telemetry_schema)

    # 6) Append to NDJSON SSOT
    append_ndjson(cfg.telemetry_store_path, event)
    return event

def load_report_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))
