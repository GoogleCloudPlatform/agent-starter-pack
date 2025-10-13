# CrewAI Coding Crew Agent

This agent combines CrewAI's collaborative AI capabilities with LangGraph to provide an interactive coding assistant that can understand requirements and generate code solutions through conversation.

## Architecture

The agent implements a conversational interface using LangGraph that coordinates with a CrewAI development team. The workflow consists of:

1. A conversational agent that:
   - Gathers requirements through natural dialogue
   - Clarifies ambiguities by asking follow-up questions
   - Delegates actual coding work to the CrewAI development team

2. A CrewAI development team consisting of:
   - Senior Engineer: Responsible for implementing the code solution
   - Chief QA Engineer: Evaluates and validates the implemented code

## Key Features

- **Interactive Requirements Gathering**: Uses LangGraph to maintain a natural conversation flow while collecting and clarifying coding requirements
- **Collaborative AI Development**: Leverages CrewAI's multi-agent system to divide work between specialized AI agents
- **Sequential Processing**: Tasks are processed in order, from requirements gathering to implementation to quality assurance

## How It Works

1. The LangGraph workflow manages the conversation state and determines when to:
   - Continue the conversation to gather more requirements
   - Delegate work to the CrewAI development team
   - Return results to the user

2. When coding is needed, the CrewAI team is activated through a custom tool that:
   - Passes requirements to the Senior Engineer agent
   - Routes the implementation to the QA Engineer for validation
   - Returns the final, validated solution
