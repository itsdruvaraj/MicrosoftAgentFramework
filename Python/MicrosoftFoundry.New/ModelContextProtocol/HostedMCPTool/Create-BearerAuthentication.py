# Copyright (c) Microsoft. All rights reserved.

import asyncio
import os
from pathlib import Path

from agent_framework import HostedMCPTool
from agent_framework.azure import AzureAIProjectAgentProvider
from azure.identity.aio import AzureCliCredential

from dotenv import load_dotenv

# Load .env from parent directory
ENV_PATH = Path(__file__).parent.parent / ".env"

"""
Azure AI Agent with Hosted MCP Tool - Project Connection Authentication Example

This sample demonstrates how to use Bearer Token authentication with a Hosted MCP Tool
when using AzureAIProjectAgentProvider. 

IMPORTANT: When using AzureAIProjectAgentProvider, you cannot pass sensitive headers 
(like Authorization) directly. Instead, you must use a project connection stored in 
your Azure AI Foundry project via the `project_connection_id` in additional_properties.

KNOWN LIMITATION: The current framework version may not properly pass project_connection_id 
to the Azure AI Agent Service when using AzureAIProjectAgentProvider. This is a framework 
gap that needs to be addressed.

Pre-requisites:
- Set up the AZURE_AI_PROJECT_ENDPOINT and AZURE_AI_MODEL_DEPLOYMENT_NAME environment variables.
- Create a Custom Key connection in your Azure AI Foundry project with the bearer token.
- Set the MCP_CUSTOM_PROJECT_CONNECTION_ID environment variable with the connection name/id.
"""


async def main() -> None:
    """Example showing use of Hosted MCP Tool with Project Connection Authentication."""
    print("=== Azure AI Agent with Hosted MCP Tool - Project Connection Auth ===\n")
    load_dotenv(ENV_PATH)

    # For Azure AI Foundry, use project_connection_id instead of headers
    # Create a connection in Azure AI Foundry portal and reference it by name
    project_connection_id = os.getenv("MCP_CUSTOM_PROJECT_CONNECTION_ID")

    async with (
        AzureCliCredential() as credential,
        AzureAIProjectAgentProvider(credential=credential) as provider,
    ):
        
        agent = await provider.create_agent(
            name="AF-MCP-Hosted-BearerAuth-Agent",
            instructions="You are a helpful assistant that can help with user questions. Always use the available tools to answer the user's questions.",
            tools=HostedMCPTool(
                name="Custom_MCP",
                url="https://app-ext-eus2-mcp-profx-01.azurewebsites.net/mcp",
                allowed_tools=["multiply", "validate_user"],
                approval_mode="never_require",
                # Use project_connection_id for authenticated MCP servers
                # NOTE: Framework limitation - this may not be passed through properly
                additional_properties={"project_connection_id": project_connection_id}
            ),
        )

        query = "Multiply 10 and 20"
        print(f"User: {query}")
        result = await agent.run(query)
        print(f"Agent: {result}")

if __name__ == "__main__":
    asyncio.run(main())