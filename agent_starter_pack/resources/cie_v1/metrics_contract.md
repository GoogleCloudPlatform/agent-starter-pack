# Vector Validation Metrics Contract

## Metrics

- `vector_validation_runs_total{role,collection,result}` (counter; `result ∈ {success,fail}`)
- `vector_validation_run_duration_seconds{role,collection}` (histogram)
- `vector_validation_points_sampled_total{role,collection}` (counter)
- `vector_validation_drift_events_total{role,collection,drift_class}` (counter)
- `vector_validation_last_run_timestamp_seconds{role,collection}` (gauge)
- `vector_validation_last_success_timestamp_seconds{role,collection}` (gauge)
- `vector_validation_current_drift_rate{role,collection,drift_class}` (gauge; optional derived)
- `vector_validation_receipt_chain_head_ok{role,collection}` (gauge; 1/0 if chain head checks)

## Label Discipline

Keep labels low-cardinality. Avoid point IDs, chunk IDs, or receipt IDs.

## Emission Patterns

### CronJob (Pushgateway)
Use `prometheus_client` with `push_to_gateway` for short-lived jobs.

### Deployment (/metrics)
Run an HTTP server with `prometheus_client.start_http_server` and scrape the pod.
