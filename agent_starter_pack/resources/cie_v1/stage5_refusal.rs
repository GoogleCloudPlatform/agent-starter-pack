//! Stage 5 — Contamination Refusal Logic (2026.GOLD posture)
//! Enforces a pure-function refusal contract + deterministic taxonomy.
//!
//! Contract:
//! - If contamination is detected -> HALT (high impedance)
//! - No mutation-based “fixes” are allowed
//! - "before == after" for SceneCapsule must hold under refusal paths

use core::fmt;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ArmPhase {
    Orienting,
    Retrieving,
    Planning,
    Generating,
    Verifying,
    Correcting,
    Halted,
}

/// Stage-5 contamination taxonomy (your canonical five).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ContaminationClass {
    BiologicalIntrusion,
    ChemicalSpike,
    InstrumentDrift,
    LineageBreak,
    WorldlineImpossibility,
}

impl fmt::Display for ContaminationClass {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        use ContaminationClass::*;
        let s = match self {
            BiologicalIntrusion => "BIOLOGICAL_INTRUSION",
            ChemicalSpike => "CHEMICAL_SPIKE",
            InstrumentDrift => "INSTRUMENT_DRIFT",
            LineageBreak => "LINEAGE_BREAK",
            WorldlineImpossibility => "WORLDLINE_IMPOSSIBILITY",
        };
        write!(f, "{s}")
    }
}

/// A single refusal finding. Deterministic text, stable ordering.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct RefusalFinding {
    pub class: ContaminationClass,
    pub detail: &'static str, // keep static strings to avoid nondeterministic formatting
}

/// The Stage-5 verdict: either proceed, or HALT with reasons.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct RefusalVerdict {
    pub ok: bool,
    pub next_phase: ArmPhase,
    pub findings: Vec<RefusalFinding>,
}

/// Minimal “SceneCapsule” footprint for Stage-5 enforcement.
/// Keep it small: you can wrap/bridge to your full scene graph later.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SceneCapsule {
    pub scene_id: String,
    pub world_id: String,
    pub corridor_id: String,

    /// 2026.GOLD seal marker (or an enum if you prefer).
    pub finality_tag: String,

    /// Immutable anchors
    pub genesis_hash_sha256: [u8; 32],
    pub vaulted_blob_sha256: [u8; 32], // save-state blob hash

    /// Chain integrity (Windchill Ledger / corridor chain)
    pub merkle_root: [u8; 32],
    pub prev_root: [u8; 32],

    /// Worldline posture flags (Stage 3 abortion should propagate here)
    pub stage3_impossible_worldline: bool,
}

/// Minimal config footprint to prevent replay/config drift.
#[derive(Debug, Clone, PartialEq)]
pub struct EmulatorConfig {
    /// Deterministic emulator build id (e.g., git commit hash truncated)
    pub build_id: [u8; 20],
    /// Deterministic config hash of runtime parameters (JCS->sha256)
    pub config_hash_sha256: [u8; 32],
    /// Temporal budget (e.g., 1.49ms window)
    pub max_frame_delta_us: u32,
    /// Kaiser floor (your sentinel floor)
    pub kaiser_floor: f64,
}

/// Minimal telemetry that can trigger contamination refusal.
/// (You can enrich later; keep determinism now.)
#[derive(Debug, Clone, PartialEq)]
pub struct ContaminationTelemetry {
    /// Chemical spike detector output (ppm or normalized)
    pub acetaldehyde_ppm: f64,
    pub ethanol_ppm: f64,

    /// Instrument drift metric (absolute drift in mm)
    pub instrument_drift_mm: f64,

    /// Optional: “bio intrusion” boolean from classifier/sensor
    pub biological_intrusion_flag: bool,

    /// Deterministic “impossible worldline” signal from planner
    pub worldline_impossible_flag: bool,
}

/// Stage-5 thresholds are *policy*, not code.
/// Treat as immutable configuration under 2026.GOLD.
#[derive(Debug, Clone, PartialEq)]
pub struct RefusalPolicy {
    pub acetaldehyde_ppm_max: f64,
    pub ethanol_ppm_max: f64,
    pub instrument_drift_mm_max: f64,
    pub kaiser_floor_min: f64,
}

/// A pure-function “before/after” check token.
/// In your system, you’d compute this via canonicalization + sha256.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct CapsuleDigest(pub [u8; 32]);

/// Compute a digest of SceneCapsule (placeholder hook).
/// Replace with your canonicalization + sha256.
/// This function is intentionally explicit so you can wire to your existing hash stack.
pub fn digest_scene_capsule_placeholder(sc: &SceneCapsule) -> CapsuleDigest {
    // NOTE: Deterministic but intentionally simple placeholder.
    // Replace with: sha256(JCS(scene_capsule_without_derived_fields))
    // For now we "fold" a few bytes to produce a stable token.
    let mut out = [0u8; 32];
    // scene_id length
    out[0] = (sc.scene_id.len() & 0xFF) as u8;
    // world_id length
    out[1] = (sc.world_id.len() & 0xFF) as u8;
    // corridor_id length
    out[2] = (sc.corridor_id.len() & 0xFF) as u8;
    // finality tag length
    out[3] = (sc.finality_tag.len() & 0xFF) as u8;
    // copy some anchor bytes
    out[4..12].copy_from_slice(&sc.genesis_hash_sha256[0..8]);
    out[12..20].copy_from_slice(&sc.vaulted_blob_sha256[0..8]);
    out[20..28].copy_from_slice(&sc.merkle_root[0..8]);
    out[28] = if sc.stage3_impossible_worldline { 1 } else { 0 };
    CapsuleDigest(out)
}

/// Stage-5: evaluate contamination refusal.
/// Key property: does NOT mutate SceneCapsule.
pub fn stage5_refusal_contract(
    scene_before: &SceneCapsule,
    scene_after: &SceneCapsule,
    cfg: &EmulatorConfig,
    tel: &ContaminationTelemetry,
    policy: &RefusalPolicy,
) -> RefusalVerdict {
    // --- Pure-function invariant: before == after on digest ---
    // (You should also enforce deep equality if you want, but digest is the corridor primitive.)
    let before_digest = digest_scene_capsule_placeholder(scene_before);
    let after_digest = digest_scene_capsule_placeholder(scene_after);

    let mut findings: Vec<RefusalFinding> = Vec::new();

    // 0) Mutation detection itself is a constitutional violation.
    if before_digest != after_digest {
        findings.push(RefusalFinding {
            class: ContaminationClass::WorldlineImpossibility,
            detail: "SceneCapsule mutated under refusal path (before != after)",
        });
    }

    // 1) Worldline impossibility must halt (Stage 3 abortion propagates).
    if scene_before.stage3_impossible_worldline || tel.worldline_impossible_flag {
        findings.push(RefusalFinding {
            class: ContaminationClass::WorldlineImpossibility,
            detail: "Impossible worldline flagged (Stage 3 abortion)",
        });
    }

    // 2) Lineage break (Merkle continuity).
    // For Stage 5, we only check local continuity primitive:
    // - if prev_root == merkle_root (degenerate) or both zeroed, treat as break unless genesis.
    // You can replace this with full chain verification via your vault verifier.
    if scene_before.prev_root == [0u8; 32] && scene_before.merkle_root == [0u8; 32] {
        findings.push(RefusalFinding {
            class: ContaminationClass::LineageBreak,
            detail: "Merkle anchors are zeroed (lineage undefined)",
        });
    }
    if scene_before.prev_root == scene_before.merkle_root {
        findings.push(RefusalFinding {
            class: ContaminationClass::LineageBreak,
            detail: "prev_root equals merkle_root (degenerate linkage)",
        });
    }

    // 3) Biological intrusion
    if tel.biological_intrusion_flag {
        findings.push(RefusalFinding {
            class: ContaminationClass::BiologicalIntrusion,
            detail: "Biological intrusion flag asserted",
        });
    }

    // 4) Chemical spike
    if tel.acetaldehyde_ppm > policy.acetaldehyde_ppm_max || tel.ethanol_ppm > policy.ethanol_ppm_max {
        findings.push(RefusalFinding {
            class: ContaminationClass::ChemicalSpike,
            detail: "Chemical spike exceeds policy thresholds",
        });
    }

    // 5) Instrument drift
    if tel.instrument_drift_mm > policy.instrument_drift_mm_max {
        findings.push(RefusalFinding {
            class: ContaminationClass::InstrumentDrift,
            detail: "Instrument drift exceeds policy threshold",
        });
    }

    // 6) Kaiser floor breach (config drift / unsafe posture)
    if cfg.kaiser_floor < policy.kaiser_floor_min {
        findings.push(RefusalFinding {
            class: ContaminationClass::InstrumentDrift,
            detail: "Kaiser floor below minimum (spectral firewall weakened)",
        });
    }

    // Deterministic ordering: sort by enum discriminant then by detail pointer address is stable enough,
    // but we avoid relying on pointer ordering. Instead: stable manual ordering by class priority.
    // (Rust enum order is stable within a compilation unit; we keep it explicit anyway.)
    findings.sort_by_key(|f| match f.class {
        ContaminationClass::BiologicalIntrusion => 10,
        ContaminationClass::ChemicalSpike => 20,
        ContaminationClass::InstrumentDrift => 30,
        ContaminationClass::LineageBreak => 40,
        ContaminationClass::WorldlineImpossibility => 50,
    });

    if findings.is_empty() {
        return RefusalVerdict {
            ok: true,
            next_phase: ArmPhase::Verifying, // proceed to verification gates
            findings,
        };
    }

    // High-impedance refusal: HALTED.
    RefusalVerdict {
        ok: false,
        next_phase: ArmPhase::Halted,
        findings,
    }
}

/// Optional helper: enforce forbidden actions under HALTED.
/// Use this at runtime to guard tool calls, generation, planning, etc.
pub fn enforce_halted_forbids(phase: ArmPhase) -> bool {
    matches!(phase, ArmPhase::Halted)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn mk_scene() -> SceneCapsule {
        SceneCapsule {
            scene_id: "batavia.1924.fermentation.v1".to_string(),
            world_id: "world:batavia-lab".to_string(),
            corridor_id: "corridor:fermentation-dynamics".to_string(),
            finality_tag: "2026.GOLD".to_string(),
            genesis_hash_sha256: [1u8; 32],
            vaulted_blob_sha256: [2u8; 32],
            merkle_root: [3u8; 32],
            prev_root: [4u8; 32],
            stage3_impossible_worldline: false,
        }
    }

    fn mk_cfg() -> EmulatorConfig {
        EmulatorConfig {
            build_id: [9u8; 20],
            config_hash_sha256: [8u8; 32],
            max_frame_delta_us: 1490,
            kaiser_floor: 0.985,
        }
    }

    fn mk_policy() -> RefusalPolicy {
        RefusalPolicy {
            acetaldehyde_ppm_max: 50.0,
            ethanol_ppm_max: 500.0,
            instrument_drift_mm_max: 0.000001, // 1e-6 mm threshold
            kaiser_floor_min: 0.985,
        }
    }

    #[test]
    fn passes_when_clean_and_pure() {
        let scene = mk_scene();
        let cfg = mk_cfg();
        let policy = mk_policy();
        let tel = ContaminationTelemetry {
            acetaldehyde_ppm: 10.0,
            ethanol_ppm: 200.0,
            instrument_drift_mm: 0.0,
            biological_intrusion_flag: false,
            worldline_impossible_flag: false,
        };

        let verdict = stage5_refusal_contract(&scene, &scene, &cfg, &tel, &policy);
        assert!(verdict.ok);
        assert_eq!(verdict.next_phase, ArmPhase::Verifying);
        assert!(verdict.findings.is_empty());
        assert!(!enforce_halted_forbids(verdict.next_phase));
    }

    #[test]
    fn halts_on_chemical_spike() {
        let scene = mk_scene();
        let cfg = mk_cfg();
        let policy = mk_policy();
        let tel = ContaminationTelemetry {
            acetaldehyde_ppm: 999.0,
            ethanol_ppm: 200.0,
            instrument_drift_mm: 0.0,
            biological_intrusion_flag: false,
            worldline_impossible_flag: false,
        };

        let verdict = stage5_refusal_contract(&scene, &scene, &cfg, &tel, &policy);
        assert!(!verdict.ok);
        assert_eq!(verdict.next_phase, ArmPhase::Halted);
        assert!(enforce_halted_forbids(verdict.next_phase));
        assert!(verdict
            .findings
            .iter()
            .any(|f| f.class == ContaminationClass::ChemicalSpike));
    }

    #[test]
    fn halts_if_scene_mutates_under_refusal_path() {
        let before = mk_scene();
        let mut after = mk_scene();
        // simulate mutation
        after.scene_id = "batavia.1924.fermentation.v1.MUTATED".to_string();

        let cfg = mk_cfg();
        let policy = mk_policy();
        let tel = ContaminationTelemetry {
            acetaldehyde_ppm: 10.0,
            ethanol_ppm: 200.0,
            instrument_drift_mm: 0.0,
            biological_intrusion_flag: false,
            worldline_impossible_flag: false,
        };

        // Even with clean telemetry, mutation forces HALT.
        let verdict = stage5_refusal_contract(&before, &after, &cfg, &tel, &policy);
        assert!(!verdict.ok);
        assert_eq!(verdict.next_phase, ArmPhase::Halted);
        assert!(verdict
            .findings
            .iter()
            .any(|f| f.detail.contains("before != after")));
    }

    #[test]
    fn halts_on_stage3_impossible_worldline() {
        let mut scene = mk_scene();
        scene.stage3_impossible_worldline = true;

        let cfg = mk_cfg();
        let policy = mk_policy();
        let tel = ContaminationTelemetry {
            acetaldehyde_ppm: 10.0,
            ethanol_ppm: 200.0,
            instrument_drift_mm: 0.0,
            biological_intrusion_flag: false,
            worldline_impossible_flag: false,
        };

        let verdict = stage5_refusal_contract(&scene, &scene, &cfg, &tel, &policy);
        assert!(!verdict.ok);
        assert_eq!(verdict.next_phase, ArmPhase::Halted);
        assert!(verdict
            .findings
            .iter()
            .any(|f| f.class == ContaminationClass::WorldlineImpossibility));
    }
}
