# Copyright (c) Microsoft. All rights reserved.

import asyncio
import os

from dotenv import load_dotenv

from agent_framework import AgentRunUpdateEvent, ChatAgent, WorkflowBuilder, WorkflowOutputEvent
from agent_framework.azure import AzureAIAgentClient
from azure.ai.agents.aio import AgentsClient
from azure.identity.aio import AzureCliCredential

"""
Sample: Agents in a workflow with streaming using pre-created Azure AI Foundry agents

A Writer agent generates content, then a Reviewer agent critiques it.
The workflow uses streaming so you can observe incremental AgentRunUpdateEvent chunks as each agent produces tokens.

This sample creates agents separately using AgentsClient, then uses them in the workflow
via AzureAIAgentClient with agent_id parameter to ensure both agents are created in Foundry.

Prerequisites:
- Azure AI Agent Service configured with environment variables:
  - AZURE_AI_PROJECT_ENDPOINT
  - AZURE_AI_MODEL_DEPLOYMENT_NAME
- Authentication via azure-identity. Use AzureCliCredential and run az login before executing the sample.
"""


def create_writer_chat_agent(agents_client: AgentsClient, writer_agent_id: str) -> ChatAgent:
    """Create a ChatAgent wrapper for the pre-existing Writer agent."""
    chat_client = AzureAIAgentClient(agents_client=agents_client, agent_id=writer_agent_id)
    return ChatAgent(chat_client=chat_client, name="Writer")


def create_reviewer_chat_agent(agents_client: AgentsClient, reviewer_agent_id: str) -> ChatAgent:
    """Create a ChatAgent wrapper for the pre-existing Reviewer agent."""
    chat_client = AzureAIAgentClient(agents_client=agents_client, agent_id=reviewer_agent_id)
    return ChatAgent(chat_client=chat_client, name="Reviewer")


async def main() -> None:
    async with (
        AzureCliCredential() as credential,
        AgentsClient(endpoint=os.environ["AZURE_AI_PROJECT_ENDPOINT"], credential=credential) as agents_client,
    ):
        # Create both agents separately in Azure AI Foundry
        writer_agent = await agents_client.create_agent(
            model=os.environ["AZURE_AI_MODEL_DEPLOYMENT_NAME"],
            name="AgentFramework-Writer",
            instructions=(
                "You are an excellent content writer. You create new content and edit contents based on the feedback."
            ),
        )
        print(f"Created Writer agent: {writer_agent.id}")

        reviewer_agent = await agents_client.create_agent(
            model=os.environ["AZURE_AI_MODEL_DEPLOYMENT_NAME"],
            name="AgentFramework-Reviewer",
            instructions=(
                "You are an excellent content reviewer. "
                "You will receive content created by a writer. Your job is to REVIEW and CRITIQUE that content. "
                "Do NOT create new content yourself. Instead, provide specific, actionable feedback about: "
                "- What works well in the content "
                "- What could be improved "
                "- Suggestions for making it more effective "
                "Keep your feedback concise and constructive."
            ),
        )
        print(f"Created Reviewer agent: {reviewer_agent.id}")

        # Create ChatAgent wrappers for both pre-created agents
        writer_agent_wrapper = create_writer_chat_agent(agents_client, writer_agent.id)
        reviewer_agent_wrapper = create_reviewer_chat_agent(agents_client, reviewer_agent.id)

        # Build the workflow using the pre-created agents
        workflow = (
            WorkflowBuilder()
            .set_start_executor("writer_agent", writer_agent_wrapper)
            .add_edge("writer_agent", "reviewer_agent")
            .build()
        )

        last_executor_id: str | None = None

        events = workflow.run_stream("Create a slogan for a new electric SUV that is affordable and fun to drive.")
        async for event in events:
            if isinstance(event, AgentRunUpdateEvent):
                eid = event.executor_id
                if eid != last_executor_id:
                    if last_executor_id is not None:
                        print()
                    print(f"{eid}:", end=" ", flush=True)
                    last_executor_id = eid
                print(event.data, end="", flush=True)
            elif isinstance(event, WorkflowOutputEvent):
                print("\n===== Final output =====")
                print(event.data)

        # Note: Agents are NOT deleted - they persist in Azure AI Foundry
        # To clean up manually, uncomment the following:
        # await agents_client.delete_agent(writer_agent.id)
        # await agents_client.delete_agent(reviewer_agent.id)


if __name__ == "__main__":
    load_dotenv()
    asyncio.run(main())