import json
from pathlib import Path
from jsonschema import Draft202012Validator

def load_schema(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))

def validate_or_raise(payload: dict, schema: dict) -> None:
    v = Draft202012Validator(schema)
    errors = sorted(v.iter_errors(payload), key=lambda e: e.path)
    if errors:
        msgs = []
        for e in errors[:10]:
            loc = "/".join(str(x) for x in e.path)
            msgs.append(f"{loc or '<root>'}: {e.message}")
        raise ValueError("Schema validation failed: " + " | ".join(msgs))
