# CIE-V1 Operational Runbook (Stub)

## Purpose
Define the operational flow for the Content Integrity Evaluation Service (CIE-V1) using neutral perturbation models aligned with the ZERO-DRIFT mandate.

## Modules
- **synthetic.noise.injector.v1**: injects bounded, neutral noise for robustness checks.
- **synthetic.contradiction.synth.v1**: produces neutral counterfactuals for contradiction testing.

## Inputs (Define for each audit run)
1. **Content Set**
   - Source identifier(s)
   - Immutable content snapshot hash
2. **Perturbation Seed**
   - Seed type (numeric/UUID)
   - Seed rotation policy
3. **Evaluation Policy**
   - Acceptable drift thresholds
   - Pass/fail criteria

## Next Operational Step (First Audit Run Definition)
Complete and record the following input manifest before executing the first audit:

```
run_id:
operator:
content_sources:
snapshot_hash:
seed:
seed_rotation_policy:
drift_thresholds:
pass_fail_criteria:
approval_required_by:
```

Store the manifest alongside the run artifacts to preserve auditability.

## Execution Steps
1. **Ingest** the immutable content snapshot and record its hash.
2. **Run** `synthetic.noise.injector.v1` with the selected seed to produce `noised_content`.
3. **Run** `synthetic.contradiction.synth.v1` with the same seed to produce `contradiction_set`.
4. **Evaluate** outputs against the policy thresholds and record pass/fail results.
5. **Archive** inputs, outputs, and verdicts for auditability.

## Bootstrap (Runtime Muscle)
Use `init_runtime.py` to initialize the vector store, register experts, and run the first
`resolve_and_execute` loop with audit-grade ledger output.

## Resolver Posture (Muscle Runtime)
The CIE-V1 resolver runs in **muscle** posture to enforce invariants at runtime:

- **Muscle (runtime)**: implement the invariant as a deterministic function.
  - Enforce fail-closed behavior during routing in the corridor runtime.
  - Best for real-time, replay-safe enforcement.
- **Fossil (schema-only)** remains available as a validation contract surface but is not the default runtime posture.

Record the posture and rationale for each audit run.

## Outputs
- `noised_content`
- `contradiction_set`
- Evaluation verdict with timestamps and operator identity

## Audit Notes
All runs must be reproducible via snapshot hash + seed pair. Any deviation triggers a re-run and escalation.
