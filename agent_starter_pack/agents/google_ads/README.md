# Google Ads Management Agent

An ADK agent for Google Ads campaign analysis, auditing, and optimization using the Google Ads API.

## What It Does

This agent connects to a Google Ads account via the API and provides:

- **Account Summary** — Total spend, conversions, CPA, ROAS for any date range
- **Campaign Performance** — All campaigns ranked by spend with key metrics
- **Wasted Spend Analysis** — Search terms with clicks but zero conversions
- **Quality Score Audit** — Distribution across all keywords with improvement recommendations
- **Optimization Recommendations** — Google's own suggestions with projected conversion lift

## Setup

### Prerequisites

- Google Ads API developer token ([apply here](https://developers.google.com/google-ads/api/docs/get-started/dev-token))
- OAuth2 credentials for Google Ads API access
- A Google Ads account with campaign data

### Environment Variables

```bash
export GOOGLE_ADS_DEVELOPER_TOKEN="your-developer-token"
export GOOGLE_ADS_CUSTOMER_ID="123-456-7890"
export GOOGLE_ADS_LOGIN_CUSTOMER_ID="your-mcc-id"  # if using MCC
```

The agent uses `google-ads` Python client library which reads credentials from environment variables or a `google-ads.yaml` file.

### Install Dependencies

```bash
pip install google-ads>=25.1.0 google-adk>=1.15.0
```

## Example Interactions

**User:** "Show me my account performance for the last 30 days"

**Agent:** Calls `get_account_summary(date_range="LAST_30_DAYS")`, presents spend, conversions, CPA, ROAS with analysis.

**User:** "Run a full audit of my account"

**Agent:** Chains 5 tool calls: account summary → campaign list → wasted spend → quality scores → recommendations. Presents structured findings with severity ratings.

**User:** "Where am I wasting money?"

**Agent:** Calls `find_wasted_spend()`, identifies search terms with zero conversions, calculates total waste, recommends negative keywords.

## Architecture

```
User → ADK Agent → Google Ads API (GAQL queries)
                 → Gemini (analysis + recommendations)
```

The agent uses GAQL (Google Ads Query Language) to pull live data, then Gemini analyzes the results and provides expert-level recommendations.

## About

Created by [John Williams](https://itallstartedwithaidea.com) — Lead, Paid Media at Seer Interactive. Part of the [googleadsagent.ai](https://googleadsagent.ai) platform.

For the full skill library (73 skills across 10 categories), see [Agent Skills](https://github.com/itallstartedwithaidea/agent-skills).
