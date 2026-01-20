# Human Collapse Guide

This guide defines the corridor-grade “Human Collapse” loop: a tamper-evident energy hash
produced by CI, a Slack approval gate, a deterministic Zapier decision object, and a
ledger-backed commit status update.

## Contract Overview

1. CI computes `energy_hash = sha256(JCS(energy_context))`.
2. Slack buttons include `trace_id` and `energy_hash`.
3. Zapier rejects any payload that fails integrity or identity checks.
4. GitHub branch protection requires a human-gated status check.

### Core Objects

- `trace_id`: idempotency key (recommended: `${repo}#${pr_number}#${head_sha}`)
- `energy_context`: immutable CI context snapshot
- `energy_hash`: hash of `energy_context` (tamper-evident binding)
- `decision`: `OPERATIONAL_FINALITY` or `ENTROPY_VIOLATION`

## 1) CI: Energy Hash Generation

### 1.1 Energy context schema

Create `artifacts/corridor/energy_context.json`:

```json
{
  "schema": "corridor.energy_context.v1",
  "repo": "Q-Enterprises/core-orchestrator",
  "pr_number": 188,
  "run_id": "GITHUB_RUN_ID",
  "head_sha": "GITHUB_SHA",
  "workflow": "ci.yml",
  "job": "lattice-integration",
  "profile": "cie_v1_audit",
  "artifact_hashes": {
    "events_ndjson_sha256": "…",
    "hash_manifest_sha256": "…",
    "merkle_root_sha256": "…",
    "signature_sha256": "…"
  },
  "attestation": {
    "runtime_profile": "parkersandboxv01",
    "origin_point_hash": "…"
  },
  "timestamp_rfc3339": "2026-01-20T16:05:00Z"
}
```

### 1.2 Deterministic hash script

Use `scripts/energy_hash.js` to create `energy_receipt.json`:

```bash
node scripts/energy_hash.js artifacts/corridor/energy_context.json artifacts/corridor/energy_receipt.json
```

### 1.3 Workflow snippet

```yaml
- name: Create corridor energy context
  run: |
    mkdir -p artifacts/corridor
    sha_events=$(sha256sum artifacts/ciev1/events.ndjson | awk '{print $1}')
    sha_manifest=$(sha256sum artifacts/ciev1/hash_manifest.json | awk '{print $1}')
    sha_merkle=$(sha256sum artifacts/ciev1/merkle_root.json | awk '{print $1}')
    sha_sig=$(sha256sum artifacts/ciev1/signature.json | awk '{print $1}')

    cat > artifacts/corridor/energy_context.json << EOF
    {
      "schema": "corridor.energy_context.v1",
      "repo": "${GITHUB_REPOSITORY}",
      "pr_number": ${PR_NUMBER},
      "run_id": "${GITHUB_RUN_ID}",
      "head_sha": "${GITHUB_SHA}",
      "workflow": "${GITHUB_WORKFLOW}",
      "job": "lattice-integration",
      "profile": "cie_v1_audit",
      "artifact_hashes": {
        "events_ndjson_sha256": "sha256:${sha_events}",
        "hash_manifest_sha256": "sha256:${sha_manifest}",
        "merkle_root_sha256": "sha256:${sha_merkle}",
        "signature_sha256": "sha256:${sha_sig}"
      },
      "attestation": {
        "runtime_profile": "${RUNTIMEPROFILE}",
        "origin_point_hash": "${ORIGIN_POINT_HASH}"
      },
      "timestamp_rfc3339": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
    }
    EOF

- name: Compute energy hash receipt
  run: |
    node scripts/energy_hash.js artifacts/corridor/energy_context.json artifacts/corridor/energy_receipt.json | tee artifacts/corridor/energy_hash.txt

- name: Upload corridor energy artifacts
  uses: actions/upload-artifact@v4
  with:
    name: corridor_energy
    path: |
      artifacts/corridor/energy_context.json
      artifacts/corridor/energy_receipt.json
      artifacts/corridor/energy_hash.txt
```

## 2) Slack: Human Collapse Gate

### 2.1 Trace ID convention

```
trace_id = "${repo}#${pr_number}#${head_sha}"
```

### 2.2 Button payload format

Use a delimiter that will not collide with the hash:

- `approve|{trace_id}|{energy_hash}`
- `reject|{trace_id}|{energy_hash}`

### 2.3 Slack Block Kit template

```json
{
  "text": "Human Collapse Required",
  "blocks": [
    {
      "type": "section",
      "text": {
        "type": "mrkdwn",
        "text": "*Human Collapse Gate*\nRepo: `Q-Enterprises/core-orchestrator`\nPR: `#188`\nHead: `{{head_sha}}`\nEnergy: `{{energy_hash}}`"
      }
    },
    {
      "type": "actions",
      "elements": [
        {
          "type": "button",
          "text": { "type": "plain_text", "text": "Approve (Operational Finality)" },
          "style": "primary",
          "value": "approve|{{trace_id}}|{{energy_hash}}"
        },
        {
          "type": "button",
          "text": { "type": "plain_text", "text": "Reject (Entropy Violation)" },
          "style": "danger",
          "value": "reject|{{trace_id}}|{{energy_hash}}"
        }
      ]
    }
  ]
}
```

## 3) Zapier: Parse Slack Verdict (Hardened)

```javascript
const rawValue = bundle.inputData.action_value || "";
const parts = rawValue.split("|");

if (parts.length !== 3) {
  throw new Error(`Invalid action_value format. Expected 3 parts with '|', got: ${parts.length}`);
}

const [verdictType, traceId, energyHash] = parts;

const intentMap = {
  approve: "OPERATIONAL_FINALITY",
  reject: "ENTROPY_VIOLATION"
};

const decision = intentMap[verdictType];
if (!decision) throw new Error(`Invalid verdict type: ${verdictType}`);

if (!traceId || traceId.length < 10) throw new Error("Missing/invalid trace_id");
if (!energyHash.startsWith("sha256:")) throw new Error("Missing/invalid energy_hash prefix");

return {
  trace_id: traceId,
  decision,
  operator: bundle.inputData.user_name,
  operator_id: bundle.inputData.user_id,
  timestamp: new Date().toISOString(),
  integrity_check: energyHash
};
```

## 4) Ledger Receipt Schema

Store the schema at `schemas/corridor_stripe_slack_v1.schema.json` and validate receipts
before appending JSONL entries.

### JSONL receipt template

```json
{
  "schema": "corridor-stripe-slack/v1",
  "event": "REVIEW_DECIDED",
  "trace_id": "{{trace_id}}",
  "repo": "Q-Enterprises/core-orchestrator",
  "pr_id": "188",
  "verdict": {
    "outcome": "{{decision}}",
    "operator": "{{operator}}",
    "operator_id": "{{operator_id}}",
    "timestamp": "{{timestamp}}"
  },
  "physics_context": {
    "run_id": "{{run_id}}",
    "head_sha": "{{head_sha}}",
    "energy_signature": "{{integrity_check}}"
  }
}
```

## 5) GitHub gating: Required status check

- Context: `corridor/human-collapse`
- State: `success` when `OPERATIONAL_FINALITY`, `failure` when `ENTROPY_VIOLATION`
- Branch protection must require `corridor/human-collapse`

## 6) Tamper-proof integrity verification

**Pattern A (recommended): Lookup-by-trace_id**

1. CI stores expected `energy_hash` by `trace_id` (Airtable, KV, or ledger pre-image table).
2. Slack includes `energy_hash` in button payload.
3. Zapier compares incoming `integrity_check` to the stored value and fail-closes on mismatch.

## 7) Deployment Checklist

### Slack
- [ ] App created, interactivity enabled
- [ ] Request URL points to Zapier hook
- [ ] App installed to target workspace/channel

### GitHub
- [ ] Branch protection requires `corridor/human-collapse`
- [ ] CI generates `energy_context.json` and `energy_receipt.json`
- [ ] CI publishes `energy_hash` by `trace_id`

### Zapier
- [ ] Trigger: Slack interactive event
- [ ] Code step: parse verdict (delimiter hardened)
- [ ] Lookup: fetch expected `energy_hash` for `trace_id`
- [ ] Filter: fail if hash mismatch
- [ ] GitHub status update
- [ ] Airtable update
- [ ] Ledger append

### Ledger
- [ ] JSON Schema validation enforced for receipts
- [ ] Idempotency policy for `trace_id`

## 8) Optional hardening

1. **Single-use hash**: include run_id or nonce in the energy context and require it to be
   the latest run for that PR head_sha.
2. **Dual attestation**: require two distinct operator approvals for finality.
3. **Operator allowlist**: enforce operator ID membership.
