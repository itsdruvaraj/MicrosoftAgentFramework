# Copyright (c) Microsoft. All rights reserved.

import asyncio
from dotenv import load_dotenv
from typing import Any

from agent_framework import ChatAgent, MCPStreamableHTTPTool, ChatMessage, GroupChatBuilder, GroupChatStateSnapshot
from agent_framework.azure import AzureAIAgentClient
from azure.identity.aio import AzureCliCredential
from pydantic import Field

"""
Azure AI Agent with Group Chat Orchestration Example
Round-robin speaker selection for collaborative agent interaction
"""

async def main():

    mcpTools1 = MCPStreamableHTTPTool(
        name="AgentFrameworkMCPTool1",
        url="https://app-ext-eus2-mcp-profx-01.azurewebsites.net/mcp",
        approval_mode="never_require",
        allowed_tools=["multiply"],
        headers={"Authorization": "Bearer <>"},
    )

    mcpTools2 = MCPStreamableHTTPTool(
        name="AgentFrameworkMCPTool2",
        url="https://app-ext-eus2-mcp-profx-01.azurewebsites.net/mcp",
        approval_mode="never_require",
        allowed_tools=["celsius_to_fahrenheit"],
        headers={"Authorization": "Bearer <>"},
    )

    def select_next_speaker(state: GroupChatStateSnapshot) -> str | None:
        """Simple round-robin speaker selection alternating between agents.
        
        Args:
            state: Contains task, participants, conversation, history, and round_index
            
        Returns:
            Name of next speaker, or None to finish
        """
        round_idx = state["round_index"]
        history = state["history"]
        
        # Finish after 4 turns (alternating between both agents twice)
        if round_idx >= 4:
            return None
        
        # Alternate speakers in round-robin fashion
        last_speaker = history[-1].speaker if history else None
        if last_speaker == "MathAgent":
            return "TemperatureConversionAgent"
        return "MathAgent"

    async with (
        AzureCliCredential() as credential,
        ChatAgent(
            chat_client=AzureAIAgentClient(credential=credential, agent_id="asst_fhH1VfpWaqDAr8EbK1XDhXMl"),
            name="MathAgent",
            tools=[mcpTools1],
        ) as mathAgent,

        ChatAgent(
            chat_client=AzureAIAgentClient(credential=credential, agent_id="asst_atFufdef4cnJMbtUPs9VeH6E"),
            name="TemperatureConversionAgent",
            tools=[mcpTools2],
        ) as tempAgent,
    ):
        workflow = (
            GroupChatBuilder()
            .select_speakers(select_next_speaker, display_name="RoundRobinOrchestrator")
            .participants([mathAgent, tempAgent])
            .build()
        )
        
        task = "What is 25 degrees Celsius in Fahrenheit and what is 15 multiplied by 7?"
        
        print(f"Task: {task}\n")
        print("=" * 80)
        
        # Run the workflow with streaming events
        from agent_framework import AgentRunUpdateEvent, WorkflowOutputEvent
        
        current_agent = None
        async for event in workflow.run_stream(task):
            if isinstance(event, AgentRunUpdateEvent):
                # Print agent name when switching to new agent
                if current_agent != event.executor_id:
                    if current_agent is not None:
                        print()  # New line after previous agent
                    print(f"\n[{event.executor_id}]: ", end="", flush=True)
                    current_agent = event.executor_id
                # Print just the content without the executor ID prefix
                print(event.data, end="", flush=True)
            elif isinstance(event, WorkflowOutputEvent):
                # Workflow completed - get final output
                print("\n")
                final_message = event.data
                author = getattr(final_message, "author_name", "System")
                text = getattr(final_message, "text", str(final_message))
                print(f"\n[{author}]\n{text}")
                print("-" * 80)
        
        print("\nWorkflow completed.")


if __name__ == "__main__":
    load_dotenv()
    asyncio.run(main())