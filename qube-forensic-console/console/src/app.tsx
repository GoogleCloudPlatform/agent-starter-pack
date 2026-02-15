import React, { useEffect, useMemo, useState } from "react";
import { loadTelemetryNDJSON } from "./api";
import { TelemetryEventV1 } from "./types";
import EventList from "./views/EventList";
import EventDetail from "./views/EventDetail";

export default function App() {
  const [events, setEvents] = useState<TelemetryEventV1[]>([]);
  const [selected, setSelected] = useState<TelemetryEventV1 | null>(null);

  useEffect(() => {
    loadTelemetryNDJSON("/ssot_telemetry_audit.ndjson").then((e) => {
      const filtered = e.filter((x) => x.payloadType === "qube_forensic_report.v1");
      setEvents(filtered);
      setSelected(filtered[0] ?? null);
    });
  }, []);

  const byCase = useMemo(() => {
    const m = new Map<string, TelemetryEventV1[]>();
    for (const ev of events) {
      const cid = ev.lineage?.caseId ?? ev.payload?.caseId ?? "unknown";
      m.set(cid, [...(m.get(cid) ?? []), ev]);
    }
    return m;
  }, [events]);

  return (
    <div style={{ display: "grid", gridTemplateColumns: "360px 1fr", height: "100vh" }}>
      <div style={{ borderRight: "1px solid #ddd", overflow: "auto" }}>
        <EventList events={events} selected={selected} onSelect={setSelected} />
      </div>
      <div style={{ overflow: "auto" }}>
        {selected ? <EventDetail event={selected} /> : <div style={{ padding: 16 }}>No event selected</div>}
        {/* byCase available for future grouping view */}
        <div style={{ display: "none" }}>{byCase.size}</div>
      </div>
    </div>
  );
}
