# Robust Load Testing for Generative AI Applications

This directory provides a comprehensive load testing framework for your Generative AI application, leveraging the power of [Locust](http://locust.io), a leading open-source load testing tool.

##  Load Testing

Before running load tests, ensure you have deployed the backend remotely.

Follow these steps to execute load tests:

**1. Deploy the Backend Remotely:**
   ```bash
   gcloud config set project <your-dev-project-id>
   make backend
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

