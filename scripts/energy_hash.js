// Deterministic energy hash generator: sha256(JCS(energy_context))
// Minimal canonicalization without external dependencies.

const fs = require("fs");
const crypto = require("crypto");

function isObject(value) {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function canonicalize(value) {
  if (Array.isArray(value)) {
    return `[${value.map(canonicalize).join(",")}]`;
  }
  if (isObject(value)) {
    const keys = Object.keys(value).sort();
    const props = keys.map((key) => `${JSON.stringify(key)}:${canonicalize(value[key])}`);
    return `{${props.join(",")}}`;
  }
  return JSON.stringify(value);
}

function sha256Hex(input) {
  return crypto.createHash("sha256").update(input, "utf8").digest("hex");
}

function main() {
  const inPath = process.argv[2];
  const outPath = process.argv[3];

  if (!inPath || !outPath) {
    console.error(
      "Usage: node scripts/energy_hash.js <energy_context.json> <energy_receipt.json>"
    );
    process.exit(2);
  }

  const context = JSON.parse(fs.readFileSync(inPath, "utf8"));
  const canonical = canonicalize(context);
  const hash = sha256Hex(canonical);

  const receipt = {
    schema: "corridor.energy_receipt.v1",
    energy_hash_alg: "sha256",
    energy_hash: `sha256:${hash}`,
    energy_context_sha256: `sha256:${sha256Hex(JSON.stringify(context))}`,
    energy_context_path: inPath,
  };

  fs.writeFileSync(outPath, JSON.stringify(receipt, null, 2) + "\n", "utf8");
  process.stdout.write(receipt.energy_hash + "\n");
}

main();
