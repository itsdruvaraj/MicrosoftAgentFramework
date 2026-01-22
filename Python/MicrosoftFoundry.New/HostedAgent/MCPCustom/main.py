# Copyright (c) Microsoft. All rights reserved.

import asyncio
import os
from typing import Any, AsyncGenerator, Union

from agent_framework import MCPStreamableHTTPTool
from agent_framework.azure import AzureOpenAIResponsesClient
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

from azure.ai.agentserver.agentframework import from_agent_framework
from azure.ai.agentserver.core import AgentRunContext as HostingRunContext
from azure.ai.agentserver.core.models import Response as OpenAIResponse, ResponseStreamEvent

load_dotenv()

# MCP Server configuration - load from environment
MCP_TOOL_NAME = os.getenv("MCP_TOOL_NAME", "Custom MCP Server")
MCP_TOOL_URL = os.getenv("MCP_TOOL_URL", "https://app-ext-eus2-mcp-profx-01.azurewebsites.net/mcp")
MCP_BEARER_TOKEN = os.getenv("MCP_BEARER_TOKEN")  # Default bearer token for MCP connection


def wrap_with_mcp_token_update(hosted_agent, mcp_tool: MCPStreamableHTTPTool):
    """Wrap the hosted agent to update MCP tool's bearer token per request.
    
    If the request metadata contains a different bearer token, the MCP tool
    will be disconnected and reconnected with the new token.
    """
    original_agent_run = hosted_agent.agent_run
    current_token = [mcp_tool.headers.get("Authorization")]  # Track current token
    
    async def wrapped_agent_run(
        context: HostingRunContext
    ) -> Union[OpenAIResponse, AsyncGenerator[ResponseStreamEvent, Any]]:
        # Extract bearer token from request metadata
        request = context.request
        metadata = request.get("metadata", {}) or {}
        bearer_token = metadata.get("mcp_bearer_token") or metadata.get("authorization")
        
        # Format the token
        new_token = None
        if bearer_token:
            new_token = bearer_token if bearer_token.startswith("Bearer ") else f"Bearer {bearer_token}"
        
        # Check if token changed - if so, reconnect MCP
        if new_token != current_token[0]:
            print(f"[MCP] Token changed, reconnecting MCP tool...")
            
            # Close existing connection if connected
            if mcp_tool.is_connected:
                try:
                    await mcp_tool.close()
                except Exception as e:
                    print(f"[MCP] Warning during close: {e}")
            
            # Update headers
            if new_token:
                mcp_tool.headers["Authorization"] = new_token
            else:
                mcp_tool.headers.pop("Authorization", None)
            
            # Reconnect with new headers
            await mcp_tool.connect()
            current_token[0] = new_token
            print(f"[MCP] Reconnected with new token")
        
        return await original_agent_run(context)
    
    hosted_agent.agent_run = wrapped_agent_run
    return hosted_agent


async def main() -> None:
    # Create initial headers
    initial_headers = {}
    if MCP_BEARER_TOKEN:
        token = MCP_BEARER_TOKEN if MCP_BEARER_TOKEN.startswith("Bearer ") else f"Bearer {MCP_BEARER_TOKEN}"
        initial_headers["Authorization"] = token
    
    # Create MCP tool
    mcp_tool = MCPStreamableHTTPTool(
        name=MCP_TOOL_NAME,
        url=MCP_TOOL_URL,
        headers=initial_headers,
    )
    
    # Create chat client and agent
    chat_client = AzureOpenAIResponsesClient(credential=DefaultAzureCredential())
    agent = chat_client.create_agent(
        instructions="You are a helpful assistant that answers questions. Always use the provided tool to look up answers from the available MCP tools.",
        tools=mcp_tool,
    )
    
    # Host the agent
    hosted_agent = from_agent_framework(agent)
    
    # Wrap to update MCP token per request
    hosted_agent = wrap_with_mcp_token_update(hosted_agent, mcp_tool)
    
    # Run with the agent context (keeps MCP connected)
    async with agent:
        await hosted_agent.run_async()


if __name__ == "__main__":
    asyncio.run(main())