# Copyright (c) Microsoft. All rights reserved.

import asyncio
from dotenv import load_dotenv

from agent_framework import MCPStreamableHTTPTool, HostedMCPTool
from agent_framework.azure import AzureAIAgentClient
from azure.identity.aio import AzureCliCredential
from pydantic import Field

"""
Azure AI Agent with Microsoft Learn MCP Tool Example
"""

async def main():

    mcpTools = HostedMCPTool(
       name="my_mcp_tool",
       description="MS Learn MCP",
       url="https://learn.microsoft.com/api/mcp",
       approval_mode="never_require",
   )

    async with (
        AzureCliCredential() as credential,
        AzureAIAgentClient(async_credential=credential,should_cleanup_agent=False).create_agent(
            name="AgentFramework-MCPAgent",
            instructions="You are a utility agent, answer questions based on the utilities available to you!",
            tools=[mcpTools]
        ) as agent,
    ):
        result = await agent.run("New features in Azure Cosmos DB")
        print(result.text)

if __name__ == "__main__":
    load_dotenv()
    asyncio.run(main())