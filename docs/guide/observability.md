# Monitoring and Observability

![monitoring_flow](https://storage.googleapis.com/github-repo/generative-ai/sample-apps/e2e-gen-ai-app-starter-pack/monitoring_flow.png)

### Trace and Log Capture

Templated agents utilize [OpenTelemetry](https://opentelemetry.io/) for comprehensive observability, emitting events to Google Cloud Trace and Google Cloud Logging. Every interaction with the LLM instrumented, enabling detailed tracing of request flows throughout agents built with this framework.

Leveraging the [CloudTraceSpanExporter](https://cloud.google.com/python/docs/reference/spanner/latest/opentelemetry-tracing), the framework captures and exports tracing data. To address the limitations of Cloud Trace ([256-byte attribute value limit](https://cloud.google.com/trace/docs/quotas#limits_on_spans)) and [Cloud Logging](https://cloud.google.com/logging/quotas) ([256KB log entry size](https://cloud.google.com/logging/quotas)), a custom extension of the CloudTraceSpanExporter is implemented in `app/utils/tracing.py` of the templated project.

This extension enhances observability by:

- Creating a corresponding Google Cloud Logging entry for every captured event.
- Automatically storing event data in Google Cloud Storage when the payload exceeds 256KB.

Logged payloads are associated with the original trace, ensuring seamless access from the Cloud Trace console.

### Log Router

Events are forwarded to BigQuery through a [log router](https://cloud.google.com/logging/docs/routing/overview) for long-term storage and analysis. The deployment of the log router is handled via Terraform code in `deployment/terraform` in the templated project.

### Looker Studio Dashboard

Once the data is written to BigQuery, it can be used to populate a [Looker Studio dashboard](https://lookerstudio.google.com/c/reporting/46b35167-b38b-4e44-bd37-701ef4307418/page/tEnnC). Use [this dashboard](https://lookerstudio.google.com/c/reporting/fa742264-4b4b-4c56-81e6-a667dd0f853f/page/tEnnC) if using non-ADK agents.

This dashboard template provides a starting point for building custom visualizations on top of the captured data.

## Disclaimer 

**Note:** The templated agents are designed to enable *your* use-case observability in your Google Cloud Project. Google Cloud does not log, monitor, or otherwise access any data generated from the deployed resources. See the [Google Cloud Service Terms](https://cloud.google.com/terms/service-terms) for more details.
