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

"""CrewAI agent with web search capabilities."""

import os
from datetime import datetime

import google.auth
from crewai import LLM, Agent, Crew, Process, Task
from crewai.tools import tool
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up Google Cloud environment for Vertex AI
try:
    credentials, project_id = google.auth.default()
    if project_id:
        os.environ["GOOGLE_CLOUD_PROJECT"] = project_id
except Exception as e:
    print(f"Warning: Could not set up Google Cloud auth: {e}")
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "")


# Configure LLM to use Vertex AI Gemini
# CrewAI uses LiteLLM which supports vertex_ai/ prefix for Vertex AI models
llm = LLM(
    model="vertex_ai/gemini-2.0-flash-exp",
    temperature=0.7,
)


@tool("Get Current Time")
def get_current_time(timezone: str = "UTC") -> str:
    """Get the current time in the specified timezone.

    Args:
        timezone: The timezone (currently only UTC is supported).

    Returns:
        The current time as a formatted string.
    """
    current_time = datetime.now()
    return (
        f"The current time is {current_time.strftime('%Y-%m-%d %I:%M %p')} {timezone}."
    )


@tool("Web Search")
def web_search(query: str) -> str:
    """Search the web for information using Google Custom Search.

    This tool performs web searches to find current information.
    Set GOOGLE_API_KEY and GOOGLE_CSE_ID environment variables to enable real search.
    Without API keys, returns mock results for testing.

    Args:
        query: The search query.

    Returns:
        Search results as formatted text.
    """
    google_api_key = os.getenv("GOOGLE_API_KEY")
    google_cse_id = os.getenv("GOOGLE_CSE_ID")

    if not google_api_key or not google_cse_id:
        # Mock search results for testing without API keys
        return f"""Mock search results for: "{query}"

This is a placeholder response. To enable real web search:
1. Get a Google API key: https://console.cloud.google.com/apis/credentials
2. Create a Custom Search Engine: https://programmablesearchengine.google.com/
3. Set environment variables:
   - GOOGLE_API_KEY=your-api-key
   - GOOGLE_CSE_ID=your-search-engine-id

For testing purposes, you can assume this query would return relevant, up-to-date information about: {query}
"""

    # Real Google Custom Search implementation
    try:
        import requests

        url = "https://www.googleapis.com/customsearch/v1"
        params = {"key": google_api_key, "cx": google_cse_id, "q": query, "num": 5}

        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()

        data = response.json()
        items = data.get("items", [])

        if not items:
            return f"No search results found for: {query}"

        results = [f"Search results for: {query}\n"]
        for i, item in enumerate(items[:5], 1):
            title = item.get("title", "No title")
            snippet = item.get("snippet", "No description")
            link = item.get("link", "")
            results.append(f"\n{i}. {title}\n   {snippet}\n   {link}")

        return "\n".join(results)

    except Exception as e:
        return f"Error performing web search: {e}\nPlease check your API credentials and try again."


# Create CrewAI agent with web search capabilities
research_agent = Agent(
    role="Research Assistant",
    goal="Help users find information and answer questions using web search",
    backstory=(
        "You are a knowledgeable AI research assistant with access to web search. "
        "You provide accurate, up-to-date information by searching the web and "
        "synthesizing results into clear, concise answers."
    ),
    tools=[web_search, get_current_time],
    llm=llm,
    verbose=True,
    allow_delegation=False,
)


def create_crew(user_query: str) -> Crew:
    """Create a crew to handle a user query.

    Args:
        user_query: The user's question or request.

    Returns:
        A configured Crew instance.
    """
    task = Task(
        description=user_query,
        expected_output="A comprehensive answer based on available information",
        agent=research_agent,
    )

    crew = Crew(
        agents=[research_agent],
        tasks=[task],
        process=Process.sequential,
        verbose=True,
    )

    return crew


def run_agent(query: str) -> str:
    """Run the CrewAI agent with a user query.

    Args:
        query: The user's question or request.

    Returns:
        The agent's response.
    """
    crew = create_crew(query)
    result = crew.kickoff()

    # CrewAI returns a CrewOutput object; extract the text
    if hasattr(result, "raw"):
        return result.raw
    return str(result)


class CrewAIWrapper:
    """Wrapper to make CrewAI compatible with Agent Starter Pack deployment targets."""

    def __init__(self):
        """Initialize the wrapper."""
        self.research_agent = research_agent
        self.tools = [web_search, get_current_time]

    def invoke(self, query: str | dict) -> str:
        """Invoke the crew with a query (sync interface).

        Args:
            query: The user's question (string or dict with 'query' or 'messages' key)

        Returns:
            The agent's response.
        """
        if isinstance(query, dict):
            # Handle different input formats from deployment targets
            query_text = query.get("query", "")
            if not query_text:
                messages = query.get("messages", [])
                if messages and len(messages) > 0:
                    if isinstance(messages[0], dict):
                        query_text = messages[0].get("content", "")
                    else:
                        query_text = str(messages[0])
            query = query_text

        return run_agent(str(query))

    async def ainvoke(self, query: str | dict) -> str:
        """Async invoke (CrewAI doesn't support async natively).

        Args:
            query: The user's question

        Returns:
            The agent's response.
        """
        import asyncio

        return await asyncio.to_thread(self.invoke, query)


# Export as root_agent for non-ADK deployment pattern (like LangGraph)
root_agent = CrewAIWrapper()


# For local testing
if __name__ == "__main__":
    test_query = "{{cookiecutter.example_question}}"
    print(f"Query: {test_query}")
    response = run_agent(test_query)
    print(f"Response: {response}")
