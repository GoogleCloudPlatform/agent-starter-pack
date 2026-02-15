import React from "react";

export default function KeyValueTable({ rows }: { rows: Array<[string, any]> }) {
  return (
    <div style={{ border: "1px solid #ddd" }}>
      {rows.map(([k, v]) => (
        <div key={k} style={{ display: "grid", gridTemplateColumns: "260px 1fr", borderTop: "1px solid #eee" }}>
          <div style={{ padding: 8, fontSize: 12, opacity: 0.8 }}>{k}</div>
          <div style={{ padding: 8, fontSize: 12 }}>
            {v === undefined || v === null ? (
              <span style={{ opacity: 0.5 }}>—</span>
            ) : (
              <span style={{ wordBreak: "break-word" }}>{String(v)}</span>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
