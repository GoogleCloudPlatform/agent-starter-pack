# Copyright 2025 Google LLC
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

# mypy: disable-error-code="union-attr"
from langchain_core.messages import BaseMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from langchain_google_vertexai import ChatVertexAI
from langgraph.graph import END, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode
import json
import os
from typing import Any, Dict, List, Optional, Union

from app.utils.github_integration import CodeFix, GitHubIntegration
from app.utils.lighthouse import LighthouseConfig, LighthouseRunner, ReportChunker

LOCATION = "us-central1"
LLM = "gemini-2.0-flash-001"

# Initialize Lighthouse runner
lighthouse_runner = LighthouseRunner(LighthouseConfig())

# Initialize GitHub integration if token is available
github_integration = None
if github_token := os.getenv("GITHUB_TOKEN"):
    github_integration = GitHubIntegration(github_token)


# 1. Define tools
@tool
def run_lighthouse_audit(url: str, output_path: Optional[str] = None) -> str:
    """Run a Lighthouse audit on the specified URL.
    
    Args:
        url: The URL to audit
        output_path: Optional path to save the report
        
    Returns:
        JSON string containing audit results
    """
    try:
        results = lighthouse_runner.run_audit(url, output_path)
        return json.dumps(results)
    except Exception as e:
        return f"Error running Lighthouse audit: {str(e)}"


@tool
def analyze_lighthouse_report(report: str) -> str:
    """Analyze a Lighthouse report and extract key issues.
    
    Args:
        report: JSON string containing Lighthouse report
        
    Returns:
        Analysis of issues found
    """
    try:
        # Parse report and extract issues
        if isinstance(report, str):
            report_data = json.loads(report)
        else:
            report_data = report
            
        issues = lighthouse_runner.extract_issues(report_data)
        
        # Format response
        response = ["# Lighthouse Audit Analysis\n"]
        
        for issue in issues:
            response.extend([
                f"## {issue.title} (Impact: {issue.impact})",
                f"Score: {issue.score}",
                f"\n{issue.description}\n",
                "### Suggestions:"
            ])
            
            for suggestion in issue.suggestions:
                response.append(f"- {suggestion}")
                
            if issue.code_snippet:
                response.extend([
                    "\n### Problematic Code:",
                    "```",
                    issue.code_snippet,
                    "```\n"
                ])
                
        return "\n".join(response)
    except Exception as e:
        return f"Error analyzing report: {str(e)}"


@tool
def create_github_pr(repo: str, fixes: List[Dict[str, Any]], base_branch: str = "main") -> str:
    """Create a GitHub pull request with fixes.
    
    Args:
        repo: Repository name (owner/repo)
        fixes: List of fixes to apply
        base_branch: Base branch name
        
    Returns:
        URL of created pull request
    """
    if not github_integration:
        return "GitHub integration not configured. Set GITHUB_TOKEN environment variable."
        
    try:
        # Convert fixes to CodeFix objects
        code_fixes = []
        for fix in fixes:
            code_fixes.append(CodeFix(
                file_path=fix["file_path"],
                original_content=fix["original_content"],
                fixed_content=fix["fixed_content"],
                description=fix["description"],
                issue_title=fix["issue_title"]
            ))
            
        # Create pull request
        pr = github_integration.apply_fixes(repo, code_fixes, base_branch)
        return f"Created pull request: {pr.html_url}"
    except Exception as e:
        return f"Error creating pull request: {str(e)}"


tools = [run_lighthouse_audit, analyze_lighthouse_report, create_github_pr]

# 2. Set up the language model
llm = ChatVertexAI(
    model=LLM,
    location=LOCATION,
    temperature=0,
    max_tokens=1024,
    streaming=True
).bind_tools(tools)


# 3. Define workflow components
def should_continue(state: MessagesState) -> str:
    """Determines whether to use tools or end the conversation."""
    last_message = state["messages"][-1]
    return "tools" if last_message.tool_calls else END


def call_model(state: MessagesState, config: RunnableConfig) -> dict[str, BaseMessage]:
    """Calls the language model and returns the response."""
    system_message = """You are a Lighthouse performance auditor that helps improve web applications.
    You can:
    1. Run Lighthouse audits on URLs using the installed Chromium browser
    2. Analyze Lighthouse reports to identify issues
    3. Create GitHub pull requests with fixes
    
    When given a URL:
    1. First verify Chromium is available at /snap/bin/chromium
    2. Run the audit using the Chromium installation
    3. Analyze the results and suggest improvements
    4. If GitHub integration is configured, create PRs with fixes
    
    When given a Lighthouse report:
    1. Parse and analyze the report
    2. Identify key performance, accessibility, and SEO issues
    3. Suggest specific improvements for each issue
    4. If GitHub integration is configured, create PRs with fixes
    
    When encountering errors:
    1. For Chrome/Chromium errors:
       - First check if Chromium is installed: `chromium --version`
       - If installed but not found, verify chrome-launcher config is correct
       - If config is correct but still failing, try with Chrome instead
    2. For network errors: 
       - Check URL accessibility
       - Try with different network settings
       - Consider using throttling config
    3. For parsing errors:
       - Verify report format is valid JSON
       - Check for missing required fields
       - Handle large reports with chunking
    4. For GitHub errors:
       - Verify token is set and valid
       - Check repository permissions
       - Ensure branch exists and is accessible
    
    Always explain your findings, recommendations, and any error handling steps clearly."""
    
    messages_with_system = [{"type": "system", "content": system_message}] + state["messages"]
    response = llm.invoke(messages_with_system, config)
    return {"messages": response}


# 4. Create the workflow graph
workflow = StateGraph(MessagesState)
workflow.add_node("agent", call_model)
workflow.add_node("tools", ToolNode(tools))
workflow.set_entry_point("agent")

# 5. Define graph edges
workflow.add_conditional_edges("agent", should_continue)
workflow.add_edge("tools", "agent")

# 6. Compile the workflow
agent = workflow.compile()
