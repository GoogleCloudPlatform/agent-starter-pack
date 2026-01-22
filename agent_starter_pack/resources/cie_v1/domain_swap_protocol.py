import hashlib
import json
from typing import Any, Dict, Mapping


def sha256_hex(data: str) -> str:
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def execute_fossilization(input_data: Mapping[str, Any]) -> Dict[str, str]:
    """Canonicalize and fossilize a customer inquiry (CIE-V1 Domain Swap Protocol)."""
    customer_id = input_data.get("customer_id")
    inquiry_type = input_data.get("inquiry_type")
    message = input_data.get("message")
    channel = input_data.get("channel")
    timestamp = input_data.get("timestamp")

    header_event_id = input_data.get("hdr_event_id")

    preimage = {
        "channel": channel,
        "customer_id": customer_id,
        "inquiry_type": inquiry_type,
        "message": message,
        "timestamp": timestamp,
    }

    canonical_json = json.dumps(preimage, sort_keys=True, separators=(",", ":"))
    leaf_digest = sha256_hex(canonical_json)

    if header_event_id:
        final_event_id = str(header_event_id)
        adjudication_type = "HEADER_OVERRIDE"
    else:
        final_event_id = sha256_hex(f"event:{leaf_digest}")
        adjudication_type = "DETERMINISTIC_FALLBACK"

    return {
        "event_id": final_event_id,
        "leaf_digest": f"sha256:{leaf_digest}",
        "raw_payload": canonical_json,
        "merkle_root": leaf_digest,
        "adjudication_verdict": "PASS",
        "adjudication_type": adjudication_type,
        "corridor_state": "State-3: Active Lineage",
    }


# Zapier Entry Point:
# output = execute_fossilization(input_data)
