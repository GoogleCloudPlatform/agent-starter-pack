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

from google.adk.agents import Agent
from google.adk.apps.app import App
from .a2ui_logic import get_a2ui_prompt

{%- if not cookiecutter.use_google_api_key %}

import os
import google.auth

# Vertex AI Configuration
try:
    _, project_id = google.auth.default()
    os.environ["GOOGLE_CLOUD_PROJECT"] = project_id
    os.environ["GOOGLE_CLOUD_LOCATION"] = "global"
    os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"
except Exception as e:
    print(f"Warning: Could not automatically configure Vertex AI. Defaulting to standard Auth. Error: {e}")
{%- endif %}

def list_items(category: str) -> str:
    """Call this to list items in a category for UI rendering."""
    # Simulation: In a real app, this would fetch from a database
    if category.lower() == "packages":
        return "Found: Premium Package, Standard Package"
    return "No items found in this category."

def confirm_selection(item_id: str) -> str:
    """Call this when a user selects an item from the UI to confirm the selection."""
    return f"Selection {item_id} has been confirmed on the server."

root_agent = Agent(
    name="a2ui_base_agent",
    model="gemini-2.5-flash",
    description="A foundational agent for building A2UI experiences with multi-turn flow logic.",
    instruction=f"""
    You are a helpful assistant that uses A2UI to provide a rich interactive experience.
    
    YOUR CAPABILITIES:
    - You can list items using the `list_items` tool.
    - You can confirm selections using the `confirm_selection` tool.
    
    YOUR FLOW:
    1. If the user asks for options, call `list_items` and then use the `LIST_EXAMPLE` A2UI template.
    2. If the user selects an item (detected by button action or text input), call `confirm_selection` and use the `ACTION_CONFIRMATION` A2UI template.
    
    {get_a2ui_prompt()}
    """,
    tools=[list_items, confirm_selection],
)

app = App(root_agent=root_agent, name="app")
