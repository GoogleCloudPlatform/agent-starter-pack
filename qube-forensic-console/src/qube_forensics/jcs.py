import json
from typing import Any

def canonical_json(obj: Any) -> str:
    # RFC8785-ish: deterministic keys + separators + unicode stable
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
