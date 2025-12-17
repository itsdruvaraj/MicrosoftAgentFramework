# Copyright (c) Microsoft. All rights reserved.

import asyncio
from dotenv import load_dotenv

from agent_framework import ChatAgent
from agent_framework.azure import AzureAIAgentClient
from azure.identity.aio import AzureCliCredential

"""
Azure AI Existing Agent Example
"""

async def main():
    async with (
        AzureCliCredential() as credential,
        ChatAgent(
            chat_client=AzureAIAgentClient(
                credential=credential,
                agent_id="asst_hvBPbv7zF3whlYtuldKndBtR", # The ID of an existing agent to use. If not provided and agents_client is provided, a new agent will be created (and deleted after the request). If neither agents_client nor agent_id is provided, both will be created and managed automatically.
            ),
        ) as agent,
    ):
        result = await agent.run("What do you know about agents?")
        print(result.text)

if __name__ == "__main__":
    load_dotenv()
    asyncio.run(main())