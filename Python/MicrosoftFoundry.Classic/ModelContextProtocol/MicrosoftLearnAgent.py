# Copyright (c) Microsoft. All rights reserved.

import asyncio
import os

from dotenv import load_dotenv

from agent_framework import ChatAgent, MCPStreamableHTTPTool
from agent_framework.azure import AzureOpenAIResponsesClient

"""
MCP 
"""
async def main() -> None:
    """Example of using MCP server without authentication."""
    load_dotenv()

    # Configuration
    mcp_server_url = "https://learn.microsoft.com/api/mcp"

    # Create MCP tool without authentication
    async with (
        MCPStreamableHTTPTool(
            name="MCP tool",
            description="MCP tool description",
            url=mcp_server_url,
        ) as mcp_tool,
        ChatAgent(
            chat_client=AzureOpenAIResponsesClient(),
            name="Agent",
            instructions="You are a helpful assistant.",
            tools=mcp_tool,
        ) as agent,
    ):
        query = "What tools are available to you?"
        print(f"User: {query}")
        result = await agent.run(query)
        print(f"Agent: {result.text}")


if __name__ == "__main__":
    asyncio.run(main())