# Load Testing for ADK Java Agent

This directory provides load testing for your ADK Java Agent application.

## Local Load Testing

Follow these steps to execute load tests on your local machine:

**1. Start the Java Server:**

Launch the Java server in a separate terminal:

```bash
make local-backend
```

**2. Run the Load Test:**

In another terminal, run the load test using the Makefile target:

```bash
make load-test
```

Or with custom parameters:

```bash
make load-test DURATION=60 USERS=20 RAMP=5
```

**Parameters:**
- `URL`: Target server URL (default: http://127.0.0.1:8080)
- `DURATION`: Test duration in seconds (default: 30)
- `USERS`: Number of concurrent users (default: 10)
- `RAMP`: Ramp-up rate in users per second (default: 2)

### Alternative: Direct Maven Command

You can also run the load test directly with Maven:

```bash
mvn test-compile failsafe:integration-test failsafe:verify \
  -Dstaging.url=http://127.0.0.1:8080 \
  -Dload.duration=30 \
  -Dload.users=10 \
  -Dload.ramp=2
```

**Note:** This approach compiles test classes and runs only failsafe goals (skips surefire/unit tests entirely).

## Remote Load Testing (Targeting Cloud Run)

This framework also supports load testing against remote targets, such as a staging Cloud Run instance.

**Prerequisites:**

- **Cloud Run Invoker Role:** You'll need the `roles/run.invoker` role to invoke the Cloud Run service.

**Steps:**

**1. Obtain ID Token:**

Retrieve the ID token required for authentication:

```bash
export _ID_TOKEN=$(gcloud auth print-identity-token -q)
```

**2. Execute the Load Test:**

Use the `URL` parameter to target your Cloud Run service:

```bash
make load-test URL=https://your-service.run.app DURATION=30 USERS=60 RAMP=2
```

## Results

Test results are printed to stdout with the following metrics:
- Total Requests
- Successes
- Failures
- Rate Limited requests
- Latency percentiles (P50, P95, P99)

The test will fail if the failure rate exceeds 10%.
