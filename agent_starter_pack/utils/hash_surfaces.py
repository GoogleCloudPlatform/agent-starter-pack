from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Any


def _normalize_preimage(preimage: Any) -> str:
    if isinstance(preimage, bytes):
        return preimage.decode("utf-8")
    if isinstance(preimage, str):
        return preimage
    return json.dumps(preimage, sort_keys=True, separators=(",", ":"))


@dataclass(frozen=True)
class HashSurfaces:
    preimage: str
    sha256: str

    @classmethod
    def from_payload(cls, preimage: Any) -> "HashSurfaces":
        canonical = _normalize_preimage(preimage)
        digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        return cls(preimage=canonical, sha256=digest)

    def as_dict(self) -> dict[str, str]:
        return {"preimage": self.preimage, "sha256": self.sha256}
