export type TelemetryEventV1 = {
  schemaVersion: "telemetry.event.v1";
  eventKey: string;
  sessionId: string;
  timestamp: string;
  sourceSystem: string;
  payloadType: "qube_forensic_report.v1";
  payload: any;
  canonicalHash: string;
  sealPhrase: string;
  lineage?: {
    caseId?: string;
    kernel?: string;
    computeNode?: string;
  };
};
