import { TelemetryEventV1 } from "./types";

export async function loadTelemetryNDJSON(url: string): Promise<TelemetryEventV1[]> {
  const res = await fetch(url);
  const text = await res.text();
  const lines = text.split("\n").map((l) => l.trim()).filter(Boolean);
  return lines.map((l) => JSON.parse(l));
}
