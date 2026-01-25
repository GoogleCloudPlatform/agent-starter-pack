export type RomFormat = {
  id: string;
  label: string;
  extensions: string[];
  magicBytes?: number[];
  magicOffset?: number;
  magicText?: string;
};

export const ROM_FORMATS: Record<string, RomFormat> = {
  nes: {
    id: "nes",
    label: "NES",
    extensions: [".nes"],
    magicBytes: [0x4e, 0x45, 0x53, 0x1a],
    magicOffset: 0,
  },
  gb: {
    id: "gb",
    label: "Game Boy / Game Boy Color",
    extensions: [".gb", ".gbc"],
  },
  gba: {
    id: "gba",
    label: "Game Boy Advance",
    extensions: [".gba"],
    magicText: "AGB",
    magicOffset: 0xac,
  },
  snes: {
    id: "snes",
    label: "Super Nintendo",
    extensions: [".sfc", ".smc", ".fig"],
  },
};

export const MANIFEST_SCHEMA = {
  required: ["title", "system", "roms"],
  properties: {
    title: "string",
    system: "string",
    roms: "array",
    region: "string",
    description: "string",
  },
};

const matchesMagicBytes = (
  buffer: ArrayBuffer,
  magicBytes: number[],
  offset = 0,
) => {
  if (buffer.byteLength < offset + magicBytes.length) {
    return false;
  }
  const bytes = new Uint8Array(buffer, offset, magicBytes.length);
  return magicBytes.every((byte, index) => bytes[index] === byte);
};

const matchesMagicText = (
  buffer: ArrayBuffer,
  magicText: string,
  offset = 0,
) => {
  if (buffer.byteLength < offset + magicText.length) {
    return false;
  }
  const bytes = new Uint8Array(buffer, offset, magicText.length);
  const decoded = String.fromCharCode(...bytes);
  return decoded === magicText;
};

export const detectRomFormat = (
  filename: string,
  buffer?: ArrayBuffer | null,
): RomFormat | null => {
  const extension = filename.toLowerCase().slice(filename.lastIndexOf("."));
  const formats = Object.values(ROM_FORMATS);

  const extensionMatch = formats.find((format) =>
    format.extensions.includes(extension),
  );
  if (extensionMatch) {
    return extensionMatch;
  }

  if (!buffer) {
    return null;
  }

  for (const format of formats) {
    if (format.magicBytes && matchesMagicBytes(buffer, format.magicBytes, format.magicOffset)) {
      return format;
    }
    if (format.magicText && matchesMagicText(buffer, format.magicText, format.magicOffset)) {
      return format;
    }
  }

  return null;
};
