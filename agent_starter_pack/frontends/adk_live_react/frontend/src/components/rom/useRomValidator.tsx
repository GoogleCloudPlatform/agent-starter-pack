import React, { useCallback, useState } from "react";
import RomManifestValidator, {
  RomManifestValidatorProps,
  RomValidationResult,
} from "./RomManifestValidator";

export type UseRomValidatorResult = {
  romFiles: File[];
  manifestFile: File | null;
  setRomFiles: (files: File[]) => void;
  setManifestFile: (file: File | null) => void;
  validation: RomValidationResult | null;
  Validator: React.FC<Omit<RomManifestValidatorProps, "romFiles" | "manifestFile" | "onValidation">>;
};

export function useRomValidator(): UseRomValidatorResult {
  const [romFiles, setRomFiles] = useState<File[]>([]);
  const [manifestFile, setManifestFile] = useState<File | null>(null);
  const [validation, setValidation] = useState<RomValidationResult | null>(null);

  const handleValidation = useCallback((result: RomValidationResult) => {
    setValidation(result);
  }, []);

  const Validator = useCallback<
    React.FC<Omit<RomManifestValidatorProps, "romFiles" | "manifestFile" | "onValidation">>
  >(
    () => (
      <RomManifestValidator
        romFiles={romFiles}
        manifestFile={manifestFile}
        onValidation={handleValidation}
      />
    ),
    [romFiles, manifestFile, handleValidation],
  );

  return {
    romFiles,
    manifestFile,
    setRomFiles,
    setManifestFile,
    validation,
    Validator,
  };
}
