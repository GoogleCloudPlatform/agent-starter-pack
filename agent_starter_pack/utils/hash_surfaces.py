from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Any


def _normalize_preimage(preimage: Any) -> str:
    """Normalize payloads into a deterministic UTF-8 string preimage."""
    if isinstance(preimage, (bytes, bytearray, memoryview)):
        try:
            return bytes(preimage).decode("utf-8")
        except UnicodeDecodeError as exc:
            msg = "preimage bytes must be valid UTF-8"
            raise ValueError(msg) from exc
    if isinstance(preimage, str):
        return preimage
    try:
        return json.dumps(preimage, sort_keys=True, separators=(",", ":"))
    except (TypeError, ValueError) as exc:
        msg = "preimage must be JSON-serializable, bytes, or str"
        raise ValueError(msg) from exc


@dataclass(frozen=True)
class HashSurfaces:
    """Deterministic payload preimage surfaces for hashing."""

    preimage: str
    sha256: str

    @classmethod
    def from_payload(cls, preimage: Any) -> "HashSurfaces":
        """Create a HashSurfaces instance from a payload preimage."""
        canonical = _normalize_preimage(preimage)
        digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        return cls(preimage=canonical, sha256=digest)

    def as_dict(self) -> dict[str, str]:
        """Serialize the hash surfaces to a plain dictionary."""
        return {"preimage": self.preimage, "sha256": self.sha256}
