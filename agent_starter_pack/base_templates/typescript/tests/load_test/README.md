# Load Testing

This directory provides load testing for the ADK agent.

## Local Load Testing

**1. Start the API Server:**

In a separate terminal:

```bash
make local-backend
```

**2. Run the Load Test:**

In another terminal:

```bash
make load-test
```

This runs a load test with 5 concurrent users, 2 requests each against `http://localhost:8000`.

## Remote Load Testing (Cloud Run)

Set the `STAGING_URL` environment variable to target a remote instance:

```bash
STAGING_URL=https://your-cloud-run-service-url.run.app make load-test
```

## Configuration

Edit `load_test.ts` to adjust:
- `numUsers`: Number of concurrent users (default: 5)
- `requestsPerUser`: Requests per user (default: 2)
- Request payload and endpoint
