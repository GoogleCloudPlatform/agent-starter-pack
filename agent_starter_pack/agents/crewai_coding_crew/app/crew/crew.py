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

# mypy: disable-error-code="attr-defined"
from typing import Any

from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task


@CrewBase
class DevCrew:
    """Developer crew"""

    agents_config: dict[str, Any]
    tasks_config: dict[str, Any]

    llm = "vertex_ai/gemini-2.0-flash-001"

    @agent
    def senior_engineer_agent(self) -> Agent:
        return Agent(
            config=self.agents_config.get("senior_engineer_agent"),
            allow_delegation=False,
            verbose=True,
            llm=self.llm,
        )

    @agent
    def chief_qa_engineer_agent(self) -> Agent:
        return Agent(
            config=self.agents_config.get("chief_qa_engineer_agent"),
            allow_delegation=True,
            verbose=True,
            llm=self.llm,
        )

    @task
    def code_task(self) -> Task:
        return Task(
            config=self.tasks_config.get("code_task"),
            agent=self.senior_engineer_agent(),
        )

    @task
    def evaluate_task(self) -> Task:
        return Task(
            config=self.tasks_config.get("evaluate_task"),
            agent=self.chief_qa_engineer_agent(),
        )

    @crew
    def crew(self) -> Crew:
        """Creates the Dev Crew"""
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )
