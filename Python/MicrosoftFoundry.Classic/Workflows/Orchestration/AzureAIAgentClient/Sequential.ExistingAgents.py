# Copyright (c) Microsoft. All rights reserved.

import asyncio

from azure.identity.aio import DefaultAzureCredential
from dotenv import load_dotenv

from agent_framework import (
    ChatAgent,
    ChatMessage,
    Role,
    SequentialBuilder,
    Workflow,
)
from agent_framework.azure import AzureAIAgentClient

"""
Sample: Sequential workflow with participant factories - Order Processing

This sample demonstrates how to create a sequential workflow with participant factories
using an order processing scenario similar to the Magentic example.

Product Codes (for validation):
- Apple: 93
- Orange: 97
- Banana: 84
- Mango: 76

Using participant factories allows you to set up proper state isolation between workflow
instances created by the same builder. This is particularly useful when you need to handle
requests or tasks in parallel with stateful participants.

In this example, we create a sequential workflow with an accumulator and three agents:
CatalogAgent, OrderAgent, and InvoiceAgent. The accumulator is stateful and maintains 
a list of all messages it has received.
"""


# Agent IDs for existing agents in Azure AI Foundry
CATALOG_AGENT_ID = "asst_u08e4d5530B6mtS9HNe39R36"  # Replace with your existing Catalog Agent ID
ORDER_AGENT_ID = "asst_0hbHqSWGzFr4o314E65crcUS"  # Replace with your existing Order Agent ID
INVOICE_AGENT_ID = "asst_Nc7l34VarDzEWOgYC3EQETfk"  # Replace with your existing Invoice Agent ID


def create_catalog_agent(credential) -> ChatAgent:
    """Create a ChatAgent using an existing Azure AI Agent."""
    return ChatAgent(
        chat_client=AzureAIAgentClient(
            credential=credential,
            agent_id=CATALOG_AGENT_ID,
        ),
        name="CatalogAgent",
    )


def create_order_agent(credential) -> ChatAgent:
    """Create a ChatAgent using an existing Azure AI Agent."""
    return ChatAgent(
        chat_client=AzureAIAgentClient(
            credential=credential,
            agent_id=ORDER_AGENT_ID,
        ),
        name="OrderAgent",
    )


def create_invoice_agent(credential) -> ChatAgent:
    """Create a ChatAgent using an existing Azure AI Agent."""
    return ChatAgent(
        chat_client=AzureAIAgentClient(
            credential=credential,
            agent_id=INVOICE_AGENT_ID,
        ),
        name="InvoiceAgent",
    )


async def run_workflow(workflow: Workflow, query: str) -> None:
    events = await workflow.run(query)
    outputs = events.get_outputs()

    if outputs:
        messages: list[ChatMessage] = outputs[0]
        for message in messages:
            name = message.author_name or ("assistant" if message.role == Role.ASSISTANT else "user")
            print(f"{name}: {message.text}")
    else:
        raise RuntimeError("No outputs received from the workflow.")


async def main() -> None:
    load_dotenv()

    async with DefaultAzureCredential() as credential:
        # 1) Create a builder with participant factories for order processing
        # Pass credential to factory functions to create clients with existing agent IDs
        builder = SequentialBuilder().register_participants([
            lambda: create_catalog_agent(credential),
            lambda: create_order_agent(credential),
            lambda: create_invoice_agent(credential),
        ])

        # 2) Build workflow_a
        workflow_a = builder.build()

        # 3) Run workflow_a with order processing task
        print("=== Order Processing Run ===")
        await run_workflow(
            workflow_a,
            "Process an order for a customer who wants: 3 Apples, 2 Oranges, and 1 Mango. "
            "First, get the product codes and prices from the catalog. "
            "Then create the order with the exact codes. "
            "Finally, generate an invoice showing all codes and the grand total."
        )

    """
    Sample Output:

    === Order Processing Run ===
    Number of queries received so far: 1
    user: Process an order for a customer who wants: 3 Apples, 2 Oranges, and 1 Mango...
    CatalogAgent: PRODUCT: Apple, CODE: 93, PRICE: $1.50
                  PRODUCT: Orange, CODE: 97, PRICE: $1.25
                  PRODUCT: Mango, CODE: 76, PRICE: $2.00
    OrderAgent: ITEM: Apple (Code: 93) x 3 = $4.50
                ITEM: Orange (Code: 97) x 2 = $2.50
                ITEM: Mango (Code: 76) x 1 = $2.00
    InvoiceAgent: INVOICE
                  ---
                  Apple (Code: 93) x 3 = $4.50
                  Orange (Code: 97) x 2 = $2.50
                  Mango (Code: 76) x 1 = $2.00
                  ---
                  GRAND TOTAL: $9.00
                  CODES USED: 93, 97, 76
    """


if __name__ == "__main__":
    asyncio.run(main())