# Qube Forensic Console — end-to-end (Schema ➜ Ingest ➜ Telemetry ➜ Console UI)

Drop-in scaffold for a loader-consumable forensic console:

* **Schemas**: forensic report + telemetry envelope (Draft 2020-12)
* **Ingest**: validate + enforce invariants + canonical hash + append-only NDJSON SSOT
* **Console UI**: browse cases/events + locally recompute canonical hash to verify integrity

## Frozen invariants

* **Embedding dimension**: `d = 1536` (asserted)
* **Seal phrase** (exact bytes, immutable):
  * `Canonical truth, attested and replayable.`
* **Hash algorithm**: SHA-256 (canonical JSON over envelope minus `canonicalHash`)

## Repo layout

```
qube-forensic-console/
  README.md
  pyproject.toml
  schemas/
    forensics/
      qube_forensic_report.v1.schema.json
    telemetry/
      telemetry_event.v1.schema.json
  src/
    qube_forensics/
      __init__.py
      jcs.py
      hashing.py
      validate.py
      emit_ndjson.py
      ingest.py
  telemetry_store/
    ssot_telemetry_audit.ndjson
  console/
    package.json
    tsconfig.json
    vite.config.ts
    index.html
    public/
      ssot_telemetry_audit.ndjson
    src/
      main.tsx
      app.tsx
      types.ts
      api.ts
      jcs.ts
      hashing.ts
      views/
        EventList.tsx
        EventDetail.tsx
      components/
        KeyValueTable.tsx
        HashBadge.tsx
```

## Quickstart

### 1) Python ingest (append-only SSOT NDJSON)

```bash
cd qube-forensic-console
python -m venv .venv
source .venv/bin/activate
pip install -e .

# Example ingest (expects report.json you provide)
python -c "from pathlib import Path; \
from qube_forensics.ingest import load_report_json, ingest_forensic_report, IngestConfig; \
cfg=IngestConfig( \
  forensic_schema_path=Path('schemas/forensics/qube_forensic_report.v1.schema.json'), \
  telemetry_schema_path=Path('schemas/telemetry/telemetry_event.v1.schema.json'), \
  telemetry_store_path=Path('telemetry_store/ssot_telemetry_audit.ndjson') \
); \
r=load_report_json(Path('report.json')); \
ev=ingest_forensic_report(r, session_id='sess_001', cfg=cfg); \
print(ev['canonicalHash'])"
```

Copy the resulting NDJSON into:

* `telemetry_store/ssot_telemetry_audit.ndjson` (SSOT)
* `console/public/ssot_telemetry_audit.ndjson` (served by Vite)

### 2) Console UI

```bash
cd console
npm i
npm run dev
```

Open:
* http://localhost:5173

## Notes on determinism

* Canonical JSON is implemented in **both** Python and TS:
  * Sorted keys, stable recursion, no whitespace, UTF-8.
* The UI recomputes:
  * `sha256(canonical_json(event minus canonicalHash))`
  * Compares against stored `canonicalHash`.

## Next hardening (optional)

Add **Merkle evidence + signature**:

* `merkleRoot` over (`snapshot.*.sha256`, `decisionHash`, `dtvEnvelopeHash`)
* `Ed25519` signature on telemetry envelope
* Optional `tpmClockAttestation` field (secure clock)
