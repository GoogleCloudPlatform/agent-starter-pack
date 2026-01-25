import React, { useEffect, useMemo, useState } from "react";
import { MANIFEST_SCHEMA, ROM_FORMATS, detectRomFormat } from "./RomFormats";

export type RomManifestEntry = {
  name?: string;
  file?: string;
  sha1?: string;
  size?: number;
};

export type RomManifest = {
  title?: string;
  system?: string;
  roms?: RomManifestEntry[];
  region?: string;
  description?: string;
};

export type DetectedRom = {
  file: File;
  format: string | null;
};

export type RomValidationResult = {
  isValid: boolean;
  errors: string[];
  warnings: string[];
  roms: DetectedRom[];
  manifest: RomManifest | null;
};

export type RomManifestValidatorProps = {
  romFiles: File[];
  manifestFile: File | null;
  onValidation?: (result: RomValidationResult) => void;
};

const readFileAsArrayBuffer = (file: File) =>
  new Promise<ArrayBuffer>((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result as ArrayBuffer);
    reader.onerror = () => reject(reader.error);
    reader.readAsArrayBuffer(file);
  });

const readFileAsText = (file: File) =>
  new Promise<string>((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result as string);
    reader.onerror = () => reject(reader.error);
    reader.readAsText(file);
  });

const validateManifest = (
  manifest: RomManifest,
  romFiles: File[],
  errors: string[],
  warnings: string[],
) => {
  MANIFEST_SCHEMA.required.forEach((field) => {
    if (!(field in manifest)) {
      errors.push(`Manifest is missing required field: ${field}.`);
    }
  });

  if (manifest.system && !ROM_FORMATS[manifest.system]) {
    errors.push(
      `Manifest system "${manifest.system}" is not supported. Supported systems: ${Object.keys(
        ROM_FORMATS,
      ).join(", ")}.`,
    );
  }

  if (manifest.roms && Array.isArray(manifest.roms)) {
    const romNames = new Set(romFiles.map((file) => file.name));
    manifest.roms.forEach((romEntry, index) => {
      if (!romEntry.file) {
        errors.push(`Manifest ROM entry ${index + 1} is missing a file name.`);
        return;
      }
      if (!romNames.has(romEntry.file)) {
        warnings.push(
          `Manifest references ROM "${romEntry.file}" that is not selected.`,
        );
      }
    });
  }
};

export default function RomManifestValidator({
  romFiles,
  manifestFile,
  onValidation,
}: RomManifestValidatorProps) {
  const [result, setResult] = useState<RomValidationResult>({
    isValid: false,
    errors: [],
    warnings: [],
    roms: [],
    manifest: null,
  });
  const [isValidating, setIsValidating] = useState(false);

  useEffect(() => {
    let isMounted = true;

    const validate = async () => {
      setIsValidating(true);
      const errors: string[] = [];
      const warnings: string[] = [];

      if (romFiles.length === 0) {
        errors.push("No ROM files selected.");
      }

      const romResults = await Promise.all(
        romFiles.map(async (file) => {
          const buffer = await readFileAsArrayBuffer(file);
          const format = detectRomFormat(file.name, buffer);
          if (!format) {
            warnings.push(`Unable to detect ROM format for "${file.name}".`);
          }
          return { file, format: format ? format.label : null };
        }),
      );

      let manifest: RomManifest | null = null;
      if (manifestFile) {
        try {
          const rawManifest = await readFileAsText(manifestFile);
          manifest = JSON.parse(rawManifest) as RomManifest;
          if (!manifest || typeof manifest !== "object") {
            errors.push("Manifest file does not contain a valid JSON object.");
          } else {
            validateManifest(manifest, romFiles, errors, warnings);
          }
        } catch (error) {
          errors.push(
            `Failed to read manifest: ${
              error instanceof Error ? error.message : "Unknown error"
            }`,
          );
        }
      } else {
        warnings.push("No manifest file provided.");
      }

      const validationResult: RomValidationResult = {
        isValid: errors.length === 0,
        errors,
        warnings,
        roms: romResults,
        manifest,
      };

      if (isMounted) {
        setResult(validationResult);
        onValidation?.(validationResult);
        setIsValidating(false);
      }
    };

    validate();

    return () => {
      isMounted = false;
    };
  }, [romFiles, manifestFile, onValidation]);

  const formatCounts = useMemo(() => {
    return result.roms.reduce<Record<string, number>>((counts, rom) => {
      const key = rom.format ?? "Unknown";
      counts[key] = (counts[key] ?? 0) + 1;
      return counts;
    }, {});
  }, [result.roms]);

  return (
    <section style={{ border: "1px solid #e2e8f0", padding: 16, borderRadius: 8 }}>
      <h3 style={{ marginTop: 0 }}>ROM Validation</h3>
      <p style={{ margin: "4px 0", color: "#475569" }}>
        Validates NES, Game Boy, GBA, and SNES ROMs plus an optional manifest.
      </p>

      {isValidating ? (
        <p>Validating files…</p>
      ) : (
        <>
          <p style={{ fontWeight: 600, color: result.isValid ? "#16a34a" : "#dc2626" }}>
            {result.isValid ? "Validation passed." : "Validation failed."}
          </p>

          <div style={{ display: "flex", gap: 24, flexWrap: "wrap" }}>
            <div>
              <h4>Detected ROMs</h4>
              <ul>
                {result.roms.map((rom) => (
                  <li key={rom.file.name}>
                    {rom.file.name} — {rom.format ?? "Unknown"} ({rom.file.size.toLocaleString()} bytes)
                  </li>
                ))}
              </ul>
              {Object.keys(formatCounts).length > 0 && (
                <p style={{ marginTop: 8, color: "#475569" }}>
                  {Object.entries(formatCounts)
                    .map(([format, count]) => `${format}: ${count}`)
                    .join(" · ")}
                </p>
              )}
            </div>

            <div>
              <h4>Manifest</h4>
              {result.manifest ? (
                <ul>
                  <li>Title: {result.manifest.title ?? "Untitled"}</li>
                  <li>System: {result.manifest.system ?? "Unknown"}</li>
                  <li>Entries: {result.manifest.roms?.length ?? 0}</li>
                </ul>
              ) : (
                <p style={{ color: "#64748b" }}>No manifest loaded.</p>
              )}
            </div>
          </div>

          {result.errors.length > 0 && (
            <div style={{ marginTop: 16 }}>
              <h4 style={{ color: "#dc2626" }}>Errors</h4>
              <ul>
                {result.errors.map((error) => (
                  <li key={error}>{error}</li>
                ))}
              </ul>
            </div>
          )}

          {result.warnings.length > 0 && (
            <div style={{ marginTop: 16 }}>
              <h4 style={{ color: "#f97316" }}>Warnings</h4>
              <ul>
                {result.warnings.map((warning) => (
                  <li key={warning}>{warning}</li>
                ))}
              </ul>
            </div>
          )}
        </>
      )}
    </section>
  );
}
