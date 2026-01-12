{%- if cookiecutter.agent_name == "adk_live" %}
# WebSocket Load Testing for Remote Agent Engine

This directory provides a comprehensive load testing framework for your Agent Engine application using WebSocket connections, leveraging the power of [Locust](http://locust.io), a leading open-source load testing tool.

The load test simulates realistic user interactions by:
- Establishing WebSocket connections
- Sending audio chunks in the proper `realtimeInput` format
- Sending text messages to complete turns
- Collecting and measuring responses until `turn_complete`

## Load Testing with Remote Agent Engine

**1. Start the Expose App in Remote Mode:**

Launch the expose app server in a separate terminal, pointing to your deployed agent engine:

```bash
uv run python -m app.app_utils.expose_app --mode remote --remote-id <your-agent-engine-id>
```

Or if you have `deployment_metadata.json` in your project root:

```bash
uv run python -m app.app_utils.expose_app --mode remote
```

**2. Execute the Load Test:**

Using another terminal tab, trigger the Locust load test:

```bash
uv run --with locust==2.31.1 --with websockets locust -f tests/load_test/load_test.py \
-H http://127.0.0.1:8000 \
--headless \
-t 30s -u 1 -r 1 \
--csv=tests/load_test/.results/results \
--html=tests/load_test/.results/report.html
```

This command initiates a 30-second load test with 1 concurrent user.

**Results:**

Comprehensive CSV and HTML reports detailing the load test performance will be generated and saved in the `tests/load_test/.results` directory.
{%- else %}
# Robust Load Testing for Generative AI Applications

This directory provides a comprehensive load testing framework for your Generative AI application, leveraging the power of [Locust](http://locust.io), a leading open-source load testing tool.

##  Load Testing

Before running load tests, ensure you have deployed the backend remotely.

Follow these steps to execute load tests:

**1. Deploy the Backend Remotely:**
   ```bash
   gcloud config set project <your-dev-project-id>
   make deploy
   ```

**2. Create a Virtual Environment for Locust:**
   It's recommended to use a separate terminal tab and create a virtual environment for Locust to avoid conflicts with your application's Python environment.

   ```bash
   python3 -m venv .locust_env && source .locust_env/bin/activate && pip install locust==2.31.1
   ```

**3. Execute the Load Test:**
   Trigger the Locust load test with the following command:

   ```bash
   export _AUTH_TOKEN=$(gcloud auth print-access-token -q)
   locust -f tests/load_test/load_test.py \
   --headless \
   -t 30s -u 5 -r 2 \
   --csv=tests/load_test/.results/results \
   --html=tests/load_test/.results/report.html
   ```

   This command initiates a 30-second load test, simulating 2 users spawning per second, reaching a maximum of 10 concurrent users.
{%- endif %}

