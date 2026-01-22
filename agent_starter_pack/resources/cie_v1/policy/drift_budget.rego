package drift_budget.v1

default allow := false

valid_classes := {"MISSING_POINT", "SCHEMA_DRIFT", "MISMATCH_PAYLOAD"}

max_missing_per_run := 0
max_schema_drift_per_run := 0
max_mismatch_payload_per_run := 0

max_last_success_age_seconds := 900
max_run_duration_seconds := 30

deny[msg] {
  some k
  input.drift_counts[k]
  not valid_classes[k]
  msg := sprintf("Unknown drift class: %v", [k])
}

deny[msg] {
  input.drift_counts["MISSING_POINT"] > max_missing_per_run
  msg := sprintf(
    "MISSING_POINT over budget: %v > %v",
    [input.drift_counts["MISSING_POINT"], max_missing_per_run]
  )
}

deny[msg] {
  input.drift_counts["SCHEMA_DRIFT"] > max_schema_drift_per_run
  msg := sprintf(
    "SCHEMA_DRIFT over budget: %v > %v",
    [input.drift_counts["SCHEMA_DRIFT"], max_schema_drift_per_run]
  )
}

deny[msg] {
  input.drift_counts["MISMATCH_PAYLOAD"] > max_mismatch_payload_per_run
  msg := sprintf(
    "MISMATCH_PAYLOAD over budget: %v > %v",
    [input.drift_counts["MISMATCH_PAYLOAD"], max_mismatch_payload_per_run]
  )
}

deny[msg] {
  input.last_success_age_seconds > max_last_success_age_seconds
  msg := sprintf(
    "Last success too old: %vs > %vs",
    [input.last_success_age_seconds, max_last_success_age_seconds]
  )
}

deny[msg] {
  input.run_duration_seconds > max_run_duration_seconds
  msg := sprintf(
    "Run duration too high: %vs > %vs",
    [input.run_duration_seconds, max_run_duration_seconds]
  )
}

allow {
  count(deny) == 0
}
