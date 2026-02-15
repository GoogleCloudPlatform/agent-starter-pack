import React from "react";
import { TelemetryEventV1 } from "../types";
import { canonicalJson } from "../jcs";
import { sha256Hex } from "../hashing";
import HashBadge from "../components/HashBadge";
import KeyValueTable from "../components/KeyValueTable";

export default function EventDetail({ event }: { event: TelemetryEventV1 }) {
  const caseId = event.lineage?.caseId ?? event.payload?.caseId ?? "unknown";
  const [computed, setComputed] = React.useState<string>("");

  React.useEffect(() => {
    (async () => {
      const tmp: any = { ...event };
      delete tmp.canonicalHash;
      const canon = canonicalJson(tmp);
      const h = await sha256Hex(canon);
      setComputed(h);
    })();
  }, [event]);

  const ok = computed && computed === event.canonicalHash;

  const snap = event.payload?.snapshot ?? {};
  const decision = event.payload?.intentSummary?.decision ?? {};
  const dtv = event.payload?.actuatorVerification ?? {};

  return (
    <div style={{ padding: 16 }}>
      <div style={{ fontWeight: 800, fontSize: 18 }}>Case: {caseId}</div>

      <div style={{ marginTop: 10, padding: 10, border: "1px solid #ddd" }}>
        <div><b>Seal Phrase</b>: {event.sealPhrase}</div>
        <div style={{ marginTop: 6 }}><HashBadge label="Canonical Hash" value={event.canonicalHash} /></div>
        <div style={{ marginTop: 6 }}><HashBadge label="Computed Hash" value={computed || "…"} /></div>
        <div style={{ marginTop: 6 }}><b>Verification</b>: {computed ? (ok ? "PASS" : "FAIL") : "PENDING"}</div>
      </div>

      <h3>Snapshot</h3>
      <KeyValueTable rows={[
        ["sensorBuffer.sha256", snap.sensorBuffer?.sha256],
        ["environmentContext.sha256", snap.environmentContext?.sha256],
        ["macroTexture.sha256", snap.macroTexture?.sha256]
      ]} />

      <h3>Intent Summary</h3>
      <KeyValueTable rows={[
        ["label", event.payload?.intentSummary?.label],
        ["lateralAdjustmentMeters", String(decision.lateralAdjustmentMeters ?? "")],
        ["velocityMph", String(decision.velocityMph ?? "")],
        ["status", String(decision.status ?? "")]
      ]} />

      <h3>DTV / Actuator Verification</h3>
      <KeyValueTable rows={[
        ["dtvStatus", String(dtv.dtvStatus ?? "")],
        ["trajectoryVarianceMm", String(dtv.trajectoryVarianceMm ?? "")],
        ["toleranceThresholdMm", String(dtv.toleranceThresholdMm ?? "")]
      ]} />
    </div>
  );
}
