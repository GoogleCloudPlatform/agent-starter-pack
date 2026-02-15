import React from "react";

export default function HashBadge({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ display: "grid", gridTemplateColumns: "140px 1fr", gap: 8 }}>
      <div style={{ fontSize: 12, opacity: 0.8 }}>{label}</div>
      <div
        style={{
          fontFamily: "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
          fontSize: 12,
          wordBreak: "break-all"
        }}
      >
        {value}
      </div>
    </div>
  );
}
