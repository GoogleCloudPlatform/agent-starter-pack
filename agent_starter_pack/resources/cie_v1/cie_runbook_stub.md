# CIE-V1 Runbook Stub

## Purpose
This runbook defines the neutral-perturbation workflow for the **content.integrity.eval.v1** service, aligned with the ZERO-DRIFT mandate.

## Modules

### 1) synthetic.noise.injector.v1
- **Objective:** Apply deterministic, neutral noise to payloads for robustness testing.
- **Inputs:** `seed`, `payload_hash`.
- **Outputs:** `noise_profile_id`, `noise_tensor`.
- **Controls:** Seeded determinism, zero drift budget, audit logging enabled.

### 2) synthetic.contradiction.synth.v1
- **Objective:** Generate neutral contradictions to validate invariant preservation.
- **Inputs:** `seed`, `payload_hash`, `invariant_set`.
- **Outputs:** `contradiction_set_id`, `contradiction_vectors`.
- **Controls:** Seeded determinism, zero drift budget, audit logging enabled.

## Execution Steps
1. **Prepare inputs**: ensure payload hashes and invariant sets are finalized.
2. **Inject neutral noise** using `synthetic.noise.injector.v1` with a fixed seed.
3. **Synthesize contradictions** using `synthetic.contradiction.synth.v1` with the same seed lineage.
4. **Run the audit bundle validation** using the CIE-V1 harness:
   ```bash
   python scripts/validate_cie_v1_audit_bundle.py \
     --payloads inputs/cie_v1_audit/payloads.ndjson \
     --receipts ledger/cie_v1/neutrality_receipts.jsonl
   ```
5. **Record outcomes**: persist receipts and summarize the neutral-perturbation profile.

## Operational Notes
- Use only neutral perturbation models for all evaluations.
- Keep the drift budget at zero and document all seed lineages.
- Escalate any non-neutral outputs for review before release.

## Next Operational Step
Define the inputs for the first official **CIE-V1** audit run before executing the harness:

- **Payloads**: finalize `inputs/cie_v1_audit/payloads.ndjson` with canonical payload hashes.
- **Invariant set**: document the invariant expectations consumed by `synthetic.contradiction.synth.v1`.
- **Seed lineage**: record the fixed seed(s) used across both modules for reproducibility.
- **Receipts path**: confirm `ledger/cie_v1/neutrality_receipts.jsonl` is writable and versioned.

## Zap Intent (Audit Lifecycle)
The webhook payload should represent a CIE-V1 audit lifecycle event so downstream steps can:

- **Index/update Airtable** with audit state, module outputs, and timestamps.
- **Route Path A/B** based on status (e.g., `verified`, `failed`, `drift_detected`).
- **Open a remediation PR** when drift or packaging/provenance issues are detected.

## Zapier Runtime Payload (Draft)
Use the webhook to emit CIE-V1 audit events into your Zap. The payload should include:

```json
{
  "arc_id": "string",
  "audit_id": "string",
  "status": "queued|running|verified|failed",
  "module_ids": ["synthetic.noise.injector.v1", "synthetic.contradiction.synth.v1"],
  "payload_hash": "string",
  "seed_lineage": ["string"],
  "receipts_path": "ledger/cie_v1/neutrality_receipts.jsonl",
  "timestamp": "ISO-8601"
}
```

### GHCR Remediation Payload (Path B)
If Path B opens a GitHub PR to harden GHCR publishing, include remediation details in the payload:

```json
{
  "remediation": {
    "action_required": true,
    "class": "packaging_provenance",
    "github": {
      "repo": "OWNER/REPO",
      "base_branch": "main",
      "title": "chore(ci): publish CIE-V1 image to GHCR",
      "body": "Add a publish workflow, OCI labels, and GHCR login using GITHUB_TOKEN."
    }
  }
}
```

### Zap Configuration Checklist
Answer these before wiring the webhook:

1. **Webhook intent**: which event triggers the Zap (audit start, completion, or failure)?
2. **Airtable mapping**:
   - Base ID / name
   - Table name
   - Search field for Step 5
   - Fields to update in Step 6
3. **Path A condition (Step 4)**: the exact filter predicate (e.g., `status == verified`).
4. **Path B condition (Step 9)**: the exact filter predicate (e.g., `status == failed`).
5. **GitHub PR details (Step 10)**:
   - Repo (`owner/name`)
   - Title mapping
   - Body template
   - Target branch

### MCP Share Link Access Note
If you share a Zapier MCP link for review, ensure the link is accessible to reviewers:

- Confirm the MCP share is public or explicitly shared with the reviewer’s account.
- If the link is private, export the MCP configuration (or paste the step list) so it can be
  reviewed without session access.

### GHCR PR Content Guidance
If the PR should publish CIE-V1 to GHCR, include:

1. **Workflow**: a GitHub Actions workflow that builds and pushes the image to `ghcr.io`
   using `GITHUB_TOKEN`.
2. **Dockerfile labels**: add `org.opencontainers.image.source` and related metadata
   (`description`, `licenses`) once a service Dockerfile exists.
3. **Optional**: multi-arch build steps and README usage notes for `docker login`/`docker pull`.

### GHCR Authentication Notes
- Prefer `GITHUB_TOKEN` for publishing packages tied to the workflow repository.
- Use a **personal access token (classic)** only when installing or publishing packages that
  require cross-repo access; ensure it has the minimum scopes (`read:packages` or
  `write:packages`).
