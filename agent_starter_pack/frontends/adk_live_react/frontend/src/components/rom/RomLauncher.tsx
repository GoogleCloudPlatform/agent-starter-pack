import React from "react";
import { useRomValidator } from "./useRomValidator";

export function RomLauncher() {
  const {
    romFiles,
    manifestFile,
    setRomFiles,
    setManifestFile,
    validation,
    Validator,
  } = useRomValidator();

  return (
    <div style={{ maxWidth: 720, margin: "0 auto", padding: "24px 16px" }}>
      <h2 style={{ marginTop: 0 }}>ROM Launcher</h2>
      <p style={{ color: "#475569" }}>
        Upload ROMs and an optional manifest to validate against supported systems.
      </p>

      <div style={{ display: "grid", gap: 12, marginBottom: 16 }}>
        <label style={{ display: "flex", flexDirection: "column", gap: 4 }}>
          ROM files
          <input
            type="file"
            multiple
            onChange={(event) => {
              const files = event.target.files
                ? Array.from(event.target.files)
                : [];
              setRomFiles(files);
            }}
          />
        </label>

        <label style={{ display: "flex", flexDirection: "column", gap: 4 }}>
          Manifest (JSON)
          <input
            type="file"
            accept="application/json"
            onChange={(event) => {
              const file = event.target.files?.[0] ?? null;
              setManifestFile(file);
            }}
          />
        </label>
      </div>

      <Validator />

      {validation && (
        <div style={{ marginTop: 16, color: "#475569" }}>
          <p style={{ margin: 0 }}>
            Selected ROMs: {romFiles.length} · Manifest:{" "}
            {manifestFile ? manifestFile.name : "None"}
          </p>
        </div>
      )}
    </div>
  );
}
