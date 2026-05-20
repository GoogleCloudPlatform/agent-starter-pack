# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Google Ads Management Agent — ADK template for campaign analysis and optimization."""

import os
from typing import Optional

import google.auth
from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.models import Gemini
from google.genai import types

_, project_id = google.auth.default()
os.environ["GOOGLE_CLOUD_PROJECT"] = project_id
os.environ["GOOGLE_CLOUD_LOCATION"] = "global"
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"

GOOGLE_ADS_CUSTOMER_ID = os.environ.get("GOOGLE_ADS_CUSTOMER_ID", "")
GOOGLE_ADS_DEVELOPER_TOKEN = os.environ.get("GOOGLE_ADS_DEVELOPER_TOKEN", "")
GOOGLE_ADS_LOGIN_CUSTOMER_ID = os.environ.get("GOOGLE_ADS_LOGIN_CUSTOMER_ID", "")


def _get_ads_client():
    """Initialize the Google Ads API client."""
    try:
        from google.ads.googleads.client import GoogleAdsClient

        return GoogleAdsClient.load_from_env()
    except Exception as e:
        return None


def _run_gaql(query: str, customer_id: Optional[str] = None) -> list[dict]:
    """Execute a GAQL query and return results as a list of dicts."""
    client = _get_ads_client()
    if not client:
        return [{"error": "Google Ads API not configured. Set GOOGLE_ADS_DEVELOPER_TOKEN and GOOGLE_ADS_CUSTOMER_ID environment variables."}]

    cid = (customer_id or GOOGLE_ADS_CUSTOMER_ID).replace("-", "")
    service = client.get_service("GoogleAdsService")
    rows = []
    try:
        response = service.search(customer_id=cid, query=query)
        for row in response:
            rows.append(_row_to_dict(row))
    except Exception as e:
        return [{"error": str(e)}]
    return rows


def _row_to_dict(row) -> dict:
    """Convert a Google Ads API row to a flat dictionary."""
    result = {}
    for field in row._pb.DESCRIPTOR.fields:
        val = getattr(row, field.name, None)
        if val is not None:
            try:
                result[field.name] = {f.name: getattr(val, f.name, None) for f in val._pb.DESCRIPTOR.fields}
            except AttributeError:
                result[field.name] = val
    return result


def get_account_summary(date_range: str = "LAST_30_DAYS") -> str:
    """Get a summary of Google Ads account performance.

    Args:
        date_range: Date range for the report. Options: YESTERDAY, LAST_7_DAYS,
            LAST_14_DAYS, LAST_30_DAYS, LAST_90_DAYS, THIS_MONTH, LAST_MONTH.

    Returns:
        Account performance summary including spend, clicks, conversions, CPA, and ROAS.
    """
    query = f"""
        SELECT customer.descriptive_name, customer.id,
               metrics.cost_micros, metrics.clicks, metrics.impressions,
               metrics.conversions, metrics.conversions_value,
               metrics.ctr, metrics.average_cpc
        FROM customer
        WHERE segments.date DURING {date_range}
    """
    rows = _run_gaql(query)
    if rows and "error" in rows[0]:
        return f"Error: {rows[0]['error']}"

    if not rows:
        return "No data returned. Check that the account has activity in the selected date range."

    metrics = rows[0].get("metrics", {})
    spend = (metrics.get("cost_micros", 0) or 0) / 1e6
    conversions = metrics.get("conversions", 0) or 0
    conv_value = metrics.get("conversions_value", 0) or 0
    cpa = spend / conversions if conversions > 0 else 0
    roas = conv_value / spend if spend > 0 else 0

    return (
        f"Account: {rows[0].get('customer', {}).get('descriptive_name', 'Unknown')}\n"
        f"Date range: {date_range}\n"
        f"Spend: ${spend:,.2f}\n"
        f"Clicks: {metrics.get('clicks', 0):,}\n"
        f"Impressions: {metrics.get('impressions', 0):,}\n"
        f"CTR: {(metrics.get('ctr', 0) or 0):.2%}\n"
        f"Avg CPC: ${(metrics.get('average_cpc', 0) or 0) / 1e6:,.2f}\n"
        f"Conversions: {conversions:,.1f}\n"
        f"CPA: ${cpa:,.2f}\n"
        f"Conversion Value: ${conv_value:,.2f}\n"
        f"ROAS: {roas:.2f}x"
    )


def list_campaigns(date_range: str = "LAST_30_DAYS", status: str = "ENABLED") -> str:
    """List all campaigns with performance metrics.

    Args:
        date_range: Date range for metrics. Options: YESTERDAY, LAST_7_DAYS,
            LAST_14_DAYS, LAST_30_DAYS, LAST_90_DAYS.
        status: Campaign status filter. Options: ENABLED, PAUSED, ALL.

    Returns:
        Campaign list with spend, conversions, CPA, and ROAS for each.
    """
    status_filter = f"AND campaign.status = '{status}'" if status != "ALL" else ""
    query = f"""
        SELECT campaign.name, campaign.status, campaign.advertising_channel_type,
               campaign_budget.amount_micros,
               metrics.cost_micros, metrics.clicks, metrics.impressions,
               metrics.conversions, metrics.conversions_value,
               metrics.cost_per_conversion
        FROM campaign
        WHERE segments.date DURING {date_range} {status_filter}
        ORDER BY metrics.cost_micros DESC
    """
    rows = _run_gaql(query)
    if rows and "error" in rows[0]:
        return f"Error: {rows[0]['error']}"
    if not rows:
        return "No campaigns found."

    lines = [f"Campaigns ({date_range}, {status}):\n"]
    for i, row in enumerate(rows[:20], 1):
        c = row.get("campaign", {})
        m = row.get("metrics", {})
        spend = (m.get("cost_micros", 0) or 0) / 1e6
        conv = m.get("conversions", 0) or 0
        cpa = spend / conv if conv > 0 else 0
        lines.append(
            f"{i}. {c.get('name', '?')} | {c.get('status', '?')} | "
            f"${spend:,.2f} | {conv:.0f} conv | ${cpa:,.2f} CPA"
        )
    return "\n".join(lines)


def find_wasted_spend(date_range: str = "LAST_30_DAYS") -> str:
    """Find search terms with spend but zero conversions (wasted spend).

    Args:
        date_range: Date range to analyze. Options: YESTERDAY, LAST_7_DAYS,
            LAST_14_DAYS, LAST_30_DAYS.

    Returns:
        List of search terms wasting budget, sorted by cost descending.
    """
    query = f"""
        SELECT search_term_view.search_term, campaign.name,
               metrics.cost_micros, metrics.clicks, metrics.impressions,
               metrics.conversions
        FROM search_term_view
        WHERE segments.date DURING {date_range}
          AND metrics.conversions = 0
        ORDER BY metrics.cost_micros DESC
        LIMIT 50
    """
    rows = _run_gaql(query)
    if rows and "error" in rows[0]:
        return f"Error: {rows[0]['error']}"
    if not rows:
        return "No wasted spend found — all search terms have conversions."

    total_waste = sum((r.get("metrics", {}).get("cost_micros", 0) or 0) / 1e6 for r in rows)
    lines = [f"Wasted Spend Report ({date_range}):\nTotal waste: ${total_waste:,.2f}\n"]
    for i, row in enumerate(rows[:20], 1):
        st = row.get("search_term_view", {}).get("search_term", "?")
        m = row.get("metrics", {})
        spend = (m.get("cost_micros", 0) or 0) / 1e6
        clicks = m.get("clicks", 0) or 0
        lines.append(f'{i}. "{st}" | ${spend:,.2f} | {clicks} clicks | 0 conversions')
    return "\n".join(lines)


def get_quality_scores() -> str:
    """Get Quality Score distribution for all active keywords.

    Returns:
        Quality Score breakdown with keyword count per score level and recommendations.
    """
    query = """
        SELECT ad_group_criterion.keyword.text,
               ad_group_criterion.quality_info.quality_score,
               ad_group_criterion.quality_info.creative_quality_score,
               ad_group_criterion.quality_info.post_click_quality_score,
               ad_group_criterion.quality_info.search_predicted_ctr,
               campaign.name, metrics.impressions, metrics.cost_micros
        FROM keyword_view
        WHERE ad_group_criterion.quality_info.quality_score IS NOT NULL
          AND segments.date DURING LAST_30_DAYS
        ORDER BY metrics.cost_micros DESC
    """
    rows = _run_gaql(query)
    if rows and "error" in rows[0]:
        return f"Error: {rows[0]['error']}"
    if not rows:
        return "No Quality Score data available."

    scores = {}
    for row in rows:
        qs = row.get("ad_group_criterion", {}).get("quality_info", {}).get("quality_score")
        if qs is not None:
            scores[qs] = scores.get(qs, 0) + 1

    total = sum(scores.values())
    low = sum(v for k, v in scores.items() if k <= 4)
    high = sum(v for k, v in scores.items() if k >= 7)

    lines = [f"Quality Score Distribution ({total} keywords):\n"]
    for qs in sorted(scores.keys()):
        bar = "#" * min(scores[qs], 40)
        lines.append(f"  QS {qs:2d}: {scores[qs]:4d} keywords {bar}")
    lines.append(f"\nLow QS (<=4): {low} ({low/total:.0%})")
    lines.append(f"High QS (>=7): {high} ({high/total:.0%})")
    if low > total * 0.3:
        lines.append("\nRecommendation: Over 30% of keywords have low Quality Score. "
                      "Focus on improving ad relevance and landing page experience.")
    return "\n".join(lines)


def get_recommendations() -> str:
    """Get Google Ads optimization recommendations.

    Returns:
        List of recommendations with type, current metrics, and projected improvement.
    """
    query = """
        SELECT recommendation.type,
               recommendation.impact.base_metrics.conversions,
               recommendation.impact.potential_metrics.conversions,
               recommendation.impact.base_metrics.cost_micros,
               recommendation.impact.potential_metrics.cost_micros
        FROM recommendation
        LIMIT 20
    """
    rows = _run_gaql(query)
    if rows and "error" in rows[0]:
        return f"Error: {rows[0]['error']}"
    if not rows:
        return "No recommendations available."

    lines = ["Google Ads Recommendations:\n"]
    for i, row in enumerate(rows, 1):
        rec = row.get("recommendation", {})
        impact = rec.get("impact", {})
        base = impact.get("base_metrics", {})
        potential = impact.get("potential_metrics", {})
        base_conv = base.get("conversions", 0) or 0
        pot_conv = potential.get("conversions", 0) or 0
        lift = pot_conv - base_conv
        lines.append(f"{i}. {rec.get('type', '?')} — projected +{lift:.0f} conversions")
    return "\n".join(lines)


SYSTEM_INSTRUCTION = """You are a Google Ads management agent. You help advertisers analyze,
audit, and optimize their Google Ads campaigns using live API data.

When the user asks about their account:
1. Pull the relevant data using your tools
2. Analyze the results and identify key findings
3. Present insights with specific numbers and metrics
4. Recommend actionable next steps

Always lead with a summary, then provide details. Use tables for comparisons.
Show costs in dollars (not micros). Bold key metrics.

If the user asks for an audit, follow this sequence:
- Account summary first (establish baseline)
- Campaign performance (identify top/bottom performers)
- Wasted spend (search terms with zero conversions)
- Quality Scores (identify improvement opportunities)
- Recommendations (Google's optimization suggestions)
"""

root_agent = Agent(
    name="google_ads_agent",
    model=Gemini(
        model="gemini-3-flash-preview",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=SYSTEM_INSTRUCTION,
    tools=[
        get_account_summary,
        list_campaigns,
        find_wasted_spend,
        get_quality_scores,
        get_recommendations,
    ],
)

app = App(
    root_agent=root_agent,
    name="{{cookiecutter.agent_directory}}",
)
