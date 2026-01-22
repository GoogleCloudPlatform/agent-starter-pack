package drift_budget.v1_windowed

default allow := false

max_missing_1h := 0
max_schema_drift_1h := 2
max_mismatch_payload_1h := 0

deny[msg] {
  input.window_counts_1h.MISSING_POINT > max_missing_1h
  msg := sprintf(
    "MISSING_POINT 1h over budget: %v > %v",
    [input.window_counts_1h.MISSING_POINT, max_missing_1h]
  )
}

deny[msg] {
  input.window_counts_1h.SCHEMA_DRIFT > max_schema_drift_1h
  msg := sprintf(
    "SCHEMA_DRIFT 1h over budget: %v > %v",
    [input.window_counts_1h.SCHEMA_DRIFT, max_schema_drift_1h]
  )
}

deny[msg] {
  input.window_counts_1h.MISMATCH_PAYLOAD > max_mismatch_payload_1h
  msg := sprintf(
    "MISMATCH_PAYLOAD 1h over budget: %v > %v",
    [input.window_counts_1h.MISMATCH_PAYLOAD, max_mismatch_payload_1h]
  )
}

allow {
  count(deny) == 0
}
