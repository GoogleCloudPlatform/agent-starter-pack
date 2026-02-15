import React from "react";
import { TelemetryEventV1 } from "../types";

export default function EventList({
  events,
  selected,
  onSelect
}: {
  events: TelemetryEventV1[];
  selected: TelemetryEventV1 | null;
  onSelect: (e: TelemetryEventV1) => void;
}) {
  return (
    <div style={{ padding: 12 }}>
      <div style={{ fontWeight: 700, marginBottom: 8 }}>Forensic Telemetry</div>
      {events.map((e) => {
        const active = selected?.canonicalHash === e.canonicalHash;
        const caseId = e.lineage?.caseId ?? e.payload?.caseId ?? "unknown";
        return (
          <div
            key={e.canonicalHash}
            onClick={() => onSelect(e)}
            style={{
              padding: 10,
              border: "1px solid #ddd",
              marginBottom: 8,
              cursor: "pointer",
              background: active ? "#f5f5f5" : "#fff"
            }}
          >
            <div style={{ fontWeight: 600 }}>{caseId}</div>
            <div style={{ fontSize: 12, opacity: 0.8 }}>{e.timestamp}</div>
            <div style={{ fontSize: 12, opacity: 0.8 }}>{e.eventKey}</div>
          </div>
        );
      })}
    </div>
  );
}
