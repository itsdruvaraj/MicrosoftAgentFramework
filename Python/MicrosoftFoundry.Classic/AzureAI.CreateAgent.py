# Copyright (c) Microsoft. All rights reserved.

import asyncio
from dotenv import load_dotenv

from agent_framework.azure import AzureAIAgentClient
from azure.identity.aio import AzureCliCredential
from pydantic import Field

"""
Azure AI Agent Basic Example
"""

async def main():
    async with (
        AzureCliCredential() as credential,
        AzureAIAgentClient(credential=credential,should_cleanup_agent=False).create_agent(
            name="AgentFramework-BasicAgent",
            instructions="You are just a basic agent created with Microsoft Agent Framework, that can talk about AI agents!",
        ) as agent,
    ):
        result = await agent.run("What do you know about agents?")
        print(result.text)

if __name__ == "__main__":
    load_dotenv()
    asyncio.run(main())