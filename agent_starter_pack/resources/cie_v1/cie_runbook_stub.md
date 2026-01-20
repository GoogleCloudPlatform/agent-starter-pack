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
