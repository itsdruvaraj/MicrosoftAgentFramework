# Copyright (c) Microsoft. All rights reserved.

import asyncio
from pathlib import Path

from agent_framework import HostedMCPTool
from agent_framework.azure import AzureAIProjectAgentProvider
from azure.identity.aio import AzureCliCredential

from dotenv import load_dotenv

# Load .env from parent directory
ENV_PATH = Path(__file__).parent.parent / ".env"

"""
Azure AI Agent with Local MCP Example

This sample demonstrates integration of Azure AI Agents with local Model Context Protocol (MCP)
servers.

Pre-requisites:
- Make sure to set up the AZURE_AI_PROJECT_ENDPOINT and AZURE_AI_MODEL_DEPLOYMENT_NAME
  environment variables before running this sample.
"""


async def main() -> None:
    """Example showing use of Local MCP Tool with AzureAIProjectAgentProvider."""
    print("=== Azure AI Agent with Local MCP Tools Example ===\n")
    load_dotenv(ENV_PATH)

    async with (
        AzureCliCredential() as credential,
        AzureAIProjectAgentProvider(credential=credential) as provider,
    ):
        
        agent = await provider.create_agent(
            name="AF-MCP-Hosted-MicrosoftLearnAgent",
            instructions="You are a helpful assistant that can help with Microsoft documentation questions. Always use the available Microsoft Learn MCP tools to answer the user's questions.",
            tools=HostedMCPTool(
                name="Microsoft Learn MCP",
                url="https://learn.microsoft.com/api/mcp",
                allowed_tools=["microsoft_docs_search", "microsoft_docs_fetch"],
                approval_mode="never_require",
                # approval_mode={
                #     "always_require_approval": ["microsoft_docs_search"],
                #     "never_require_approval": ["microsoft_docs_fetch"],
                # },
            ),
        )

        query = "List available MCP tools?"
        print(f"User: {query}")
        result = await agent.run(query)
        print(f"Agent: {result}")

if __name__ == "__main__":
    asyncio.run(main())