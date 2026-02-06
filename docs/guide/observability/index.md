# Monitoring and Observability

The Agent Starter Pack offers robust options to monitor your agent's behavior, performance, and resource usage. This allows you to debug issues, optimize costs, and understand how your agent is functioning.

There are two primary observability features available:

1.  **[Agent Telemetry Events (Cloud Trace)](cloud-trace.md):** Provides OpenTelemetry-based tracing and spans for all agent operations, automatically exported to Google Cloud Trace. This is **always enabled** and great for understanding execution flow and latency.

2.  **[BigQuery Agent Analytics Plugin](bq-agent-analytics.md):** An **opt-in** plugin for ADK-based agents that logs detailed agent events, including LLM interactions, tool calls, and outcomes, directly to BigQuery. This enables in-depth analysis, LLM based evals and observability, use of [BigQuery conversational analytics](https://cloud.google.com/bigquery/docs/conversational-analytics) and custom dashboards.

## Choosing an Approach

| Feature                 | [Cloud Trace Telemetry](cloud-trace.md) | [BigQuery Agent Analytics Plugin](bq-agent-analytics.md) |
| :---------------------- | :------------------------------------ | :------------------------------------------------------- |
| **Enabling**            | Always On                             | Opt-in via `--bq-analytics` flag                         |
| **Primary Use Case**    | Execution flow, latency, debugging    | Deep analysis, llm-as-a-judge, conversational analytics, dashboards      |
| **Data Destination**    | Google Cloud Trace                    | Google BigQuery                                          |
| **Schema**              | OpenTelemetry Spans                   | Predefined BigQuery Table Schema                         |
| **Content Logging**     | Span attributes (Metadata)            | Detailed JSON payloads, GCS offloading for large content |
| **Agent Compatibility** | All Templates                         | ADK-based agents only                                    |
| **Setup**               | None                                  | Enable flag during project creation                      |

**Recommendation:**

*   Use **[Cloud Trace Telemetry](cloud-trace.md)** for real-time debugging and performance monitoring of all agents.
*   Enable the **[BigQuery Agent Analytics Plugin](bq-agent-analytics.md)** when you need to perform detailed analysis on agent behavior, run LLM based evaluations, use BigQuery conversational analytics, track events over time, or build custom reporting dashboards for your ADK-based agents.

The old GCS-based prompt-response logging is deprecated in favor of the BigQuery Agent Analytics Plugin when the `--bq-analytics` flag is used.

## Deprecated: GCS/Logging Based Prompt-Response Logging

Previously, a system logged LLM interactions to GCS and Cloud Logging. This method is **disabled** and superseded by the BigQuery Agent Analytics Plugin when `--bq-analytics` is enabled during project creation. If the flag is not used, the old system remains in place for ADK-based agents (excluding LangGraph).
