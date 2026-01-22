# Copyright (c) Microsoft. All rights reserved.

import asyncio
from pathlib import Path

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
        
        agent = await provider.get_agent(
            name="FoundryNew-MCP-MSLearnAgent"
        )

        query = "List available MCP tools?"
        print(f"User: {query}")
        result = await agent.run(query)
        print(f"Agent: {result}")

if __name__ == "__main__":
    asyncio.run(main())