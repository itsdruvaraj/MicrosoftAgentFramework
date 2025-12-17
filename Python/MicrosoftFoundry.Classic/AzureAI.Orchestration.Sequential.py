# Copyright (c) Microsoft. All rights reserved.

import asyncio
from dotenv import load_dotenv
from typing import Any

from agent_framework import ChatAgent, MCPStreamableHTTPTool, ChatMessage, SequentialBuilder
from agent_framework.azure import AzureAIAgentClient
from azure.identity.aio import AzureCliCredential
from pydantic import Field

"""
Azure AI Agent with Sequential Orchestration Example
"""

async def main():

    mcpTools1 = MCPStreamableHTTPTool(
        name="AgentFrameworkMCPTool1",
        url="https://app-ext-eus2-mcp-profx-01.azurewebsites.net/mcp",
        approval_mode="never_require",
        allowed_tools=["multiply"],
        headers={"Authorization": "Bearer <YOUR_BEARER_TOKEN>"},
    )

    mcpTools2 = MCPStreamableHTTPTool(
        name="AgentFrameworkMCPTool2",
        url="https://app-ext-eus2-mcp-profx-01.azurewebsites.net/mcp",
        approval_mode="never_require",
        allowed_tools=["celsius_to_fahrenheit"],
        headers={"Authorization": "Bearer <YOUR_BEARER_TOKEN>"},
    )

    async with (
        AzureCliCredential() as credential,
        ChatAgent(
            chat_client=AzureAIAgentClient(credential=credential, agent_id="asst_SVSNpSIC6uoMIWmM0nWiNAl0"),
            tools=[mcpTools1],
        ) as mathAgent,

        ChatAgent(
            chat_client=AzureAIAgentClient(credential=credential, agent_id="asst_Cct8boe3WxHHwjlnu3fULgrg"),
            tools=[mcpTools2],
        ) as tempAgent,
    ):
        workflow = SequentialBuilder().participants([mathAgent, tempAgent]).build()
        events = await workflow.run("What is 25 degrees Celsius in Fahrenheit and what is 15 multiplied by 7?")
        outputs = events.get_outputs()

        if outputs:
            print("===== Final Aggregated Conversation (messages) =====")
            for output in outputs:
                messages: list[ChatMessage] | Any = output
                for i, msg in enumerate(messages, start=1):
                    name = msg.author_name if msg.author_name else "user"
                    print(f"{'-' * 60}\n\n{i:02d} [{name}]:\n{msg.text}")


if __name__ == "__main__":
    load_dotenv()
    asyncio.run(main())