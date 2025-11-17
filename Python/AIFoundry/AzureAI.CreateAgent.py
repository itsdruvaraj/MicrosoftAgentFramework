# Copyright (c) Microsoft. All rights reserved.

import asyncio
from random import randint
from typing import Annotated
from dotenv import load_dotenv

from agent_framework.azure import AzureAIAgentClient
from azure.identity.aio import AzureCliCredential
from pydantic import Field

"""
Azure AI Agent Basic Example
"""

async def main():
    load_dotenv()

    async with (
        AzureCliCredential() as credential,
        AzureAIAgentClient(async_credential=credential).create_agent(
            name="AgentFramework.BasicAgent",
            instructions="You are just a basic agent created with Microsoft Agent Framework, just say hello!",
        ) as agent,
    ):
        result = await agent.run("What can you do?")
        print(result.text)

if __name__ == "__main__":
    asyncio.run(main())