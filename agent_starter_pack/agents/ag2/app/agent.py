# ruff: noqa
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

import os

from autogen import ConversableAgent, LLMConfig
from autogen.agentchat.group import (
    AgentTarget,
    ContextVariables,
    OnCondition,
    RevertToUserTarget,
    StringLLMCondition,
)
from autogen.agentchat.group.patterns import DefaultPattern
from dotenv import load_dotenv

load_dotenv()

MODEL = "gemini-2.5-flash"
{%- if not cookiecutter.use_google_api_key %}

import google.auth

_, project_id = google.auth.default()
os.environ["GOOGLE_CLOUD_PROJECT"] = project_id
os.environ["GOOGLE_CLOUD_LOCATION"] = "global"
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"
{%- endif %}

llm_config = LLMConfig({"api_type": "google", "model": MODEL})

# --- Agent Definitions ---

architect = ConversableAgent(
    name="architect",
    system_message=(
        "You are a distributed systems architect. "
        "Given a user request, design the system architecture including: "
        "core components and responsibilities, data storage strategy, "
        "API layer and service interfaces, and deployment topology. "
        "Output a clear, actionable design document for the coder."
    ),
    llm_config=llm_config,
    human_input_mode="NEVER",
)

coder = ConversableAgent(
    name="coder",
    system_message=(
        "You are a senior backend engineer. "
        "Implement the system based on the architect's design. "
        "Write production-quality Python code with clean interfaces, "
        "type hints, and proper error handling."
    ),
    llm_config=llm_config,
    human_input_mode="NEVER",
)

reviewer = ConversableAgent(
    name="reviewer",
    system_message=(
        "You are a principal engineer conducting code review. "
        "Review the implementation for correctness, scalability, "
        "and adherence to the design. "
        "Either APPROVE with a summary, or REQUEST CHANGES with specifics."
    ),
    llm_config=llm_config,
    human_input_mode="NEVER",
)

# --- Handoff Routing ---

architect.handoffs.add_llm_conditions([
    OnCondition(
        target=AgentTarget(coder),
        condition=StringLLMCondition(
            prompt="Route to coder when the design is complete and ready to implement."
        ),
    ),
])

coder.handoffs.add_llm_conditions([
    OnCondition(
        target=AgentTarget(reviewer),
        condition=StringLLMCondition(
            prompt="Route to reviewer when the implementation is complete."
        ),
    ),
])

reviewer.handoffs.add_llm_conditions([
    OnCondition(
        target=AgentTarget(coder),
        condition=StringLLMCondition(
            prompt="Route back to coder when changes are requested."
        ),
    ),
])
reviewer.handoffs.set_after_work(RevertToUserTarget())

# --- Orchestration ---

user = ConversableAgent(name="user", human_input_mode="NEVER")

context_variables = ContextVariables(data={"phase": "design"})

pattern = DefaultPattern(
    initial_agent=architect,
    agents=[architect, coder, reviewer],
    user_agent=user,
    context_variables=context_variables,
    group_after_work=RevertToUserTarget(),
)

# Entry point for A2A server
root_agent = architect

# Prevent ADK app injection - AG2 uses its own A2A server
app = None
