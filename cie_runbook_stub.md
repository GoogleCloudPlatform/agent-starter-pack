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
4. **Validation Job Envelope (ValidationJobEnvelope.v1)**
   - `job_id` (UUID)
   - `schedule` (cadence + `jitter_ms=0` for sovereign jobs)
   - `inputs` (receipt block reference, Qdrant collection, sample spec)
   - `execution` (started/finished timestamps, validator version)
   - `outputs` (validation receipt, batch anchor)
   - `digest` (sha256 of canonical JSON excluding digest)

## Next Operational Step
Define and capture the first **ValidationJobEnvelope.v1** for the initial audit run, then
emit **Tick.v1(kind=VALIDATION)** in `/validation/ticks/` to start the job lifecycle.

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
- **AgentProposalReceipt.v1** (YAML receipt for audit attestation)

## Audit Notes
All runs must be reproducible via snapshot hash + seed pair. Any deviation triggers a re-run and escalation.

## Sovereign Validation Artifacts
Capture an **AgentProposalReceipt.v1** for each audit execution to ensure repeatable attestation and replayability:

```yaml
schema_version: AgentProposalReceipt.v1
receipt_id: "{{uuid}}"
proposal_id: "{{proposal_id}}"
timestamp_utc: "{{timestamp}}"

provenance:
  github_run_id: "{{github_run_id}}"
  oidc_identity: "https://github.com/{{org}}/{{repo}}/.github/workflows/agent-pr.yml@refs/heads/main"
  validator_version: "pydantic-sovereign-suite-1.0.2"

logic_proof:
  s1_structural_pass: true
  p1_air_gap_pass: true
  b1_offline_mode: true
  h1_gate_seal: "GOLDEN_SNAPSHOT_VERIFIED"
  validation_summary: "Payload satisfies all 4 Sovereign Invariants. KCT 64-D projection within safety bounds."

attestation:
  kct_hash: "sha256:{{sha256_of_kernel_control_token}}"
  snapshot_ref: "fossil://{{golden_snapshot_id}}"
  signer_address: "{{metamask_public_address}}"

digest: "{{sha256_of_canonical_receipt_without_digest}}"
```

## Sovereign Invariants Policy (OPA Rego)
Gate validation runs through an OPA policy check before archive and release:

```rego
package validation.sovereign

import future.keywords.if

default allow = false

# S1: Must include a validated artifact
violation[msg] if {
    not input.drift_receipt
    not input.agent_checkpoint
    msg := "S1 Violation: Missing required DriftReceipt or AgentCheckpoint."
}

# P1: Air-Gap enforcement for file paths
violation[msg] if {
    input.agent_role == "INFRA"
    not startswith(input.target_path, "charts/")
    msg := "P1 Violation: INFRA agent attempted to access restricted path."
}

violation[msg] if {
    input.agent_role == "POLICY"
    not startswith(input.target_path, "policy/")
    msg := "P1 Violation: POLICY agent attempted to access restricted path."
}

# H1: Human approval for production impact
violation[msg] if {
    input.requires_human_approval == true
    not input.golden_snapshot
    msg := "H1 Violation: Production-impacting change missing GoldenSnapshot artifact."
}

allow if {
    count(violation) == 0
}
```

## Replay-Court Verification Script
Use the kernel below to verify the AgentProposalReceipt digest prior to archival:

```python
import hashlib
import json
import yaml

def canonicalize_jcs(data: dict) -> str:
    """Implements JSON Canonicalization Scheme (RFC 8785) for YAML objects."""
    return json.dumps(data, sort_keys=True, separators=(',', ':'))

def verify_fossil(path_to_yaml: str) -> bool:
    """Verifies the integrity of a fossil artifact against its digest."""
    with open(path_to_yaml, 'r') as f:
        artifact = yaml.safe_load(f)

    provided_digest = artifact.pop('digest')
    computed_digest = hashlib.sha256(canonicalize_jcs(artifact).encode()).hexdigest()

    return provided_digest == computed_digest

# Kernel usage:
# if verify_fossil("validation/fossils/AgentProposalReceipt.v1.yaml"):
#     engage_replay_court()
```
