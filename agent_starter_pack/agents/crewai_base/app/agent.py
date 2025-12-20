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

"""CrewAI agent with utility tools for demonstrations."""

import os
import re
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


@tool("Calculate")
def calculate(expression: str) -> str:
    """Perform basic mathematical calculations.

    Supports addition (+), subtraction (-), multiplication (*), division (/),
    exponentiation (**), and parentheses for grouping.

    Args:
        expression: A mathematical expression to evaluate (e.g., "2 + 2", "10 * (5 + 3)").

    Returns:
        The result of the calculation as a string.
    """
    try:
        # Remove any characters that aren't numbers, operators, parentheses, or decimals
        # This is a simple safeguard against code injection
        if not re.match(r'^[\d\+\-\*/\.\(\)\s\*\*]+$', expression):
            return "Error: Invalid characters in expression. Only numbers and operators (+, -, *, /, **, parentheses) are allowed."

        # Evaluate the expression safely
        result = eval(expression, {"__builtins__": {}}, {})
        return f"The result of {expression} is {result}"
    except ZeroDivisionError:
        return "Error: Division by zero is not allowed."
    except Exception as e:
        return f"Error calculating expression: {e!s}"


@tool("Analyze Text")
def analyze_text(text: str) -> str:
    """Analyze text and provide statistics.

    Provides word count, character count, sentence count, and basic readability metrics.

    Args:
        text: The text to analyze.

    Returns:
        Analysis results as formatted text.
    """
    if not text or not text.strip():
        return "Error: No text provided for analysis."

    # Basic text statistics
    char_count = len(text)
    char_count_no_spaces = len(text.replace(" ", ""))
    word_count = len(text.split())
    sentence_count = len([s for s in re.split(r'[.!?]+', text) if s.strip()])

    # Average word length
    words = text.split()
    avg_word_length = sum(len(word) for word in words) / len(words) if words else 0

    # Simple sentiment indicators (very basic)
    positive_words = ['good', 'great', 'excellent', 'amazing', 'wonderful', 'fantastic', 'happy', 'love']
    negative_words = ['bad', 'terrible', 'awful', 'horrible', 'hate', 'sad', 'angry', 'poor']

    text_lower = text.lower()
    positive_count = sum(1 for word in positive_words if word in text_lower)
    negative_count = sum(1 for word in negative_words if word in text_lower)

    sentiment = "Neutral"
    if positive_count > negative_count:
        sentiment = "Positive"
    elif negative_count > positive_count:
        sentiment = "Negative"

    return f"""Text Analysis Results:
- Characters (with spaces): {char_count}
- Characters (without spaces): {char_count_no_spaces}
- Word count: {word_count}
- Sentence count: {sentence_count}
- Average word length: {avg_word_length:.1f} characters
- Estimated sentiment: {sentiment} ({positive_count} positive indicators, {negative_count} negative indicators)"""


@tool("Generate Ideas")
def generate_ideas(topic: str, count: int = 5) -> str:
    """Generate creative ideas or suggestions on a given topic.

    This tool helps brainstorm ideas, suggestions, or approaches for a topic.
    The LLM will use its knowledge to generate relevant ideas.

    Args:
        topic: The topic or problem to generate ideas about.
        count: Number of ideas to generate (default: 5, max: 10).

    Returns:
        A list of generated ideas.
    """
    # Limit count to reasonable range
    count = max(1, min(int(count), 10))

    # This tool returns a structured prompt for the LLM to process
    # The actual idea generation happens via the LLM's reasoning
    return f"""Generate {count} creative ideas for: {topic}

Please provide {count} distinct, practical, and creative ideas or approaches."""


# Create CrewAI agent with utility tools
assistant_agent = Agent(
    role="AI Assistant",
    goal="Help users with calculations, text analysis, and brainstorming",
    backstory=(
        "You are a helpful AI assistant with multiple utility tools. "
        "You can perform calculations, analyze text for statistics and sentiment, "
        "check the current time, and help generate creative ideas. "
        "You always use the appropriate tool for each task and provide clear, helpful responses."
    ),
    tools=[get_current_time, calculate, analyze_text, generate_ideas],
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
        agent=assistant_agent,
    )

    crew = Crew(
        agents=[assistant_agent],
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
        self.assistant_agent = assistant_agent
        self.tools = [get_current_time, calculate, analyze_text, generate_ideas]

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
