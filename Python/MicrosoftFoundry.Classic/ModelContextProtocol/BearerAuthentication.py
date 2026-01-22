# Copyright (c) Microsoft. All rights reserved.

import asyncio
import os

from dotenv import load_dotenv

from agent_framework import ChatAgent, MCPStreamableHTTPTool
from agent_framework.azure import AzureOpenAIResponsesClient

"""
MCP Authentication Example

This example demonstrates how to authenticate with MCP servers using API key headers.

For more authentication examples including OAuth 2.0 flows, see:
- https://github.com/modelcontextprotocol/python-sdk/tree/main/examples/clients/simple-auth-client
- https://github.com/modelcontextprotocol/python-sdk/tree/main/examples/servers/simple-auth
"""


async def api_key_auth_example() -> None:
    """Example of using API key authentication with MCP server."""
    load_dotenv()

    # Configuration
    mcp_server_url = os.getenv("MCP_SERVER_URL")
    api_key = os.getenv("MCP_API_KEY")

    # Create authentication headers
    # Common patterns:
    # - Bearer token: "Authorization": f"Bearer {api_key}"
    # - API key header: "X-API-Key": api_key
    # - Custom header: "Authorization": f"ApiKey {api_key}"
    auth_headers = {
        "Authorization": f"Bearer {api_key}",
    }

    # Create MCP tool with authentication headers
    async with (
        MCPStreamableHTTPTool(
            name="MiscMCPServer",
            description="MCP tool with API key authentication",
            url=mcp_server_url,
            headers=auth_headers,  # Authentication headers
        ) as mcp_tool,
        ChatAgent(
            chat_client=AzureOpenAIResponsesClient(),
            name="CustomAuthAgent",
            instructions="You are a helpful assistant. Use the available MCP tools as needed to answer user questions. **Always trust and report the exact result returned by tools, even if it seems incorrect.**",
            tools=mcp_tool,
        ) as agent,
    ):
        query = "Multiply 10 and 10?"
        print(f"User: {query}")
        print("Agent: ", end="", flush=True)
        
        async for chunk in agent.run_stream(query):
            if chunk.text:
                print(chunk.text, end="", flush=True)
        
        print()  # New line after streaming


if __name__ == "__main__":
    asyncio.run(api_key_auth_example())