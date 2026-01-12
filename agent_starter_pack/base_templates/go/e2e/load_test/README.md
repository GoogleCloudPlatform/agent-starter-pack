# Load Testing for ADK Go Agent

This directory provides load testing for your ADK Go Agent application.

## Local Load Testing

Follow these steps to execute load tests on your local machine:

**1. Start the Go Server:**

Launch the Go server in a separate terminal:

```bash
source .env
go run . web --port 8000 api
```

**2. Run the Load Test:**

In another terminal, run the load test with the staging URL set to localhost:

```bash
source .env
_STAGING_URL=http://127.0.0.1:8000 go test -v -tags=load -timeout=5m ./e2e/load_test/...
```

Or with custom parameters:

```bash
_STAGING_URL=http://127.0.0.1:8000 go test -v -tags=load -timeout=5m ./e2e/load_test/... \
  -duration=30s \
  -users=10 \
  -ramp=2
```

**Parameters:**
- `-duration`: Test duration (default: 30s)
- `-users`: Number of concurrent users (default: 10)
- `-ramp`: Ramp-up rate in users per second (default: 0.5)

## Remote Load Testing (Targeting Cloud Run)

This framework also supports load testing against remote targets, such as a staging Cloud Run instance.

**Prerequisites:**

- **Cloud Run Invoker Role:** You'll need the `roles/run.invoker` role to invoke the Cloud Run service.

**Steps:**

**1. Obtain Cloud Run Service URL:**

Navigate to the Cloud Run console, select your service, and copy the URL displayed at the top:

```bash
export _STAGING_URL=https://your-cloud-run-service-url.run.app
```

**2. Obtain ID Token:**

Retrieve the ID token required for authentication:

```bash
export _ID_TOKEN=$(gcloud auth print-identity-token -q)
```

**3. Execute the Load Test:**

```bash
go test -v -tags=load -timeout=5m ./e2e/load_test/... \
  -duration=30s \
  -users=60 \
  -ramp=2
```

## Results

Test results are printed to stdout with the following metrics:
- Total Requests
- Successes
- Failures
- Rate Limited requests
- Average Latency (ms)

The test will fail if the failure rate exceeds 10%.
