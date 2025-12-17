# Copyright (c) Microsoft. All rights reserved.

import asyncio

from azure.identity.aio import DefaultAzureCredential
from dotenv import load_dotenv

from agent_framework import (
    ChatAgent,
    ChatMessage,
    Executor,
    Role,
    SequentialBuilder,
    Workflow,
    WorkflowContext,
    handler,
)
from agent_framework.azure import AzureOpenAIChatClient

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


class Accumulate(Executor):
    """Simple accumulator.

    Accumulates all messages from the conversation and prints them out.
    """

    def __init__(self, id: str):
        super().__init__(id)
        # Some internal state to accumulate messages
        self._accumulated: list[str] = []

    @handler
    async def accumulate(self, conversation: list[ChatMessage], ctx: WorkflowContext[list[ChatMessage]]) -> None:
        self._accumulated.extend([msg.text for msg in conversation])
        print(f"Number of queries received so far: {len(self._accumulated)}")
        await ctx.send_message(conversation)


# Global credential to be set in main()
_credential: DefaultAzureCredential | None = None


def create_catalog_agent() -> ChatAgent:
    return ChatAgent(
        name="CatalogAgent",
        description="Product catalog specialist who provides product codes and prices",
        instructions=(
            "You are a Catalog Agent. When asked, provide the following EXACT product information:\n"
            "- Apple: Code 93, Price $1.50\n"
            "- Orange: Code 97, Price $1.25\n"
            "- Banana: Code 84, Price $0.75\n"
            "- Mango: Code 76, Price $2.00\n\n"
            "Always format as: 'PRODUCT: [name], CODE: [number], PRICE: $[amount]'\n"
            "These codes are FIXED and must be used exactly as specified."
        ),
        chat_client=AzureOpenAIChatClient(credential=_credential),
    )


def create_order_agent() -> ChatAgent:
    return ChatAgent(
        name="OrderAgent",
        description="Order processor who creates orders using catalog codes",
        instructions=(
            "You are an Order Agent. You MUST use the EXACT product codes provided by the Catalog Agent.\n"
            "When creating an order, format each line item as:\n"
            "'ITEM: [name] (Code: [code]) x [quantity] = $[subtotal]'\n\n"
            "IMPORTANT: The codes must match exactly what the Catalog Agent provided.\n"
            "If Apple has Code 93, you must use Code 93 - never make up codes."
        ),
        chat_client=AzureOpenAIChatClient(credential=_credential),
    )


def create_invoice_agent() -> ChatAgent:
    return ChatAgent(
        name="InvoiceAgent",
        description="Invoice generator who validates codes and calculates totals",
        instructions=(
            "You are an Invoice Agent. Review the Order Agent's order and create an invoice.\n"
            "Your invoice MUST:\n"
            "1. List each item with its CODE from the order\n"
            "2. Show the calculation for each line item\n"
            "3. Calculate and show the GRAND TOTAL\n"
            "4. Add a verification line: 'CODES USED: [list all codes]'\n\n"
            "The codes in your invoice must match the Order Agent's codes exactly."
        ),
        chat_client=AzureOpenAIChatClient(credential=_credential),
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

    global _credential
    async with DefaultAzureCredential() as credential:
        _credential = credential

        # 1) Create a builder with participant factories for order processing
        builder = SequentialBuilder().register_participants([
            lambda: Accumulate("accumulator"),
            create_catalog_agent,
            create_order_agent,
            create_invoice_agent,
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