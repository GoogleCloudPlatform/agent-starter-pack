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
from langchain_google_vertexai import ChatVertexAI
from langgraph.prebuilt import create_react_agent

from .crew.crew import DevCrew

LOCATION = "global"
LLM = "gemini-2.5-flash"

llm = ChatVertexAI(model=LLM, location=LOCATION, temperature=0)


def coding_tool(code_instructions: str) -> str:
    """Use this tool to write a python program given a set of requirements and or instructions."""
    inputs = {"code_instructions": code_instructions}
    return DevCrew().crew().kickoff(inputs=inputs)


system_message = (
    "You are an expert Lead Software Engineer Manager.\n"
    "Your role is to speak to a user and understand what kind of code they need to "
    "build.\n"
    "Part of your task is therefore to gather requirements and clarifying ambiguity "
    "by asking followup questions. Don't ask all the questions together as the user "
    "has a low attention span, rather ask a question at the time.\n"
    "Once the problem to solve is clear, you will call your tool for writing the "
    "solution.\n"
    "Remember, you are an expert in understanding requirements but you cannot code, "
    "use your coding tool to generate a solution. Keep the test cases if any, they "
    "are useful for the user."
)

agent = create_react_agent(model=llm, tools=[coding_tool], prompt=system_message)
