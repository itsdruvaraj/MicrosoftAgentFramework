# Copyright (c) Microsoft. All rights reserved.

import asyncio

from agent_framework import MCPStreamableHTTPTool
from agent_framework.azure import AzureOpenAIResponsesClient
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

from azure.ai.agentserver.agentframework import from_agent_framework

MCP_TOOL_NAME = "Microsoft Learn MCP"
MCP_TOOL_URL = "https://learn.microsoft.com/api/mcp"

load_dotenv()


async def main() -> None:
    agent = AzureOpenAIResponsesClient(credential=DefaultAzureCredential()).create_agent(
        instructions="You are a helpful assistant that answers Microsoft documentation questions. Always use the provided tool to look up answers from the Microsoft Learn MCP API.",
        tools=MCPStreamableHTTPTool(name=MCP_TOOL_NAME, url=MCP_TOOL_URL),
    )

    async with agent:
        await from_agent_framework(agent).run_async()


if __name__ == "__main__":
    asyncio.run(main())
