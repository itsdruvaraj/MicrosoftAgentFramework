# Copyright (c) Microsoft. All rights reserved.

import asyncio
from dotenv import load_dotenv

from agent_framework import ChatAgent
from agent_framework.azure import AzureAIAgentClient
from azure.identity.aio import AzureCliCredential

"""
Azure AI Agent Basic Example
"""

async def main():
    async with (
        AzureCliCredential() as credential,
        ChatAgent(
            chat_client=AzureAIAgentClient(
                credential=credential,
                agent_id="asst_m419Lm5ctXI5BDIScwisiIWq",
            ),
        ) as agent,
    ):
        print("Agent: ", end="", flush=True)
        async for chunk in agent.run_stream("What do you know about agents?"):
            if chunk.text:
                print(chunk.text, end="", flush=True)
        print("\n")

if __name__ == "__main__":
    load_dotenv()
    asyncio.run(main())