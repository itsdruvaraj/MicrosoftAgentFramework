# Copyright (c) Microsoft. All rights reserved.

import asyncio
import logging
from pathlib import Path
from typing import cast

from azure.identity.aio import DefaultAzureCredential
from dotenv import load_dotenv

from agent_framework import (
    MAGENTIC_EVENT_TYPE_AGENT_DELTA,
    MAGENTIC_EVENT_TYPE_ORCHESTRATOR,
    AgentRunUpdateEvent,
    ChatAgent,
    ChatMessage,
    MagenticBuilder,
    WorkflowOutputEvent,
)
from agent_framework.azure import AzureOpenAIChatClient

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

"""
Sample: Magentic Orchestration (multi-agent) - Order Processing Pipeline

What it does:
- Orchestrates three agents in an order processing pipeline with specific product codes
  that can be easily validated across agent handoffs.

Product Codes (for validation):
- Apple: 93
- Orange: 97
- Banana: 84
- Mango: 76

- CatalogAgent: Provides the product codes and prices
- OrderAgent: Creates an order using the exact codes from the catalog
- InvoiceAgent: Generates an invoice with the codes and calculates the total

This use case validates that each agent correctly uses data from previous agents.

Why AzureOpenAIChatClient:
- Stateless client that sends complete chat history with each request
- Works well with all Magentic patterns including TOOL_APPROVAL
- No server-side state management conflicts

Prerequisites:
- Azure OpenAI resource with a deployed model
- Environment variables:
  - AZURE_OPENAI_ENDPOINT: Your Azure OpenAI endpoint
  - AZURE_OPENAI_DEPLOYMENT_NAME: The name of your model deployment
- Azure CLI authenticated (az login)
"""


async def main() -> None:
    async with DefaultAzureCredential() as credential:
        catalog_agent = ChatAgent(
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
            chat_client=AzureOpenAIChatClient(credential=credential),
        )

        order_agent = ChatAgent(
            name="OrderAgent",
            description="Order processor who creates orders using catalog codes",
            instructions=(
                "You are an Order Agent. You MUST use the EXACT product codes provided by the Catalog Agent.\n"
                "When creating an order, format each line item as:\n"
                "'ITEM: [name] (Code: [code]) x [quantity] = $[subtotal]'\n\n"
                "IMPORTANT: The codes must match exactly what the Catalog Agent provided.\n"
                "If Apple has Code 93, you must use Code 93 - never make up codes."
            ),
            chat_client=AzureOpenAIChatClient(credential=credential),
        )

        invoice_agent = ChatAgent(
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
            chat_client=AzureOpenAIChatClient(credential=credential),
        )

        # Create a manager agent for orchestration
        manager_agent = ChatAgent(
            name="MagenticManager",
            description="Orchestrator that coordinates the catalog, order, and invoice workflow",
            instructions=(
                "You coordinate a team to process orders. "
                "The workflow MUST be: Catalog Agent provides codes -> Order Agent creates order -> Invoice Agent generates invoice. "
                "Ensure each agent uses the data from the previous agent."
            ),
            chat_client=AzureOpenAIChatClient(credential=credential),
        )

        print("\nBuilding Magentic Workflow...")

        # State used by on_agent_stream callback
        last_stream_agent_id: str | None = None
        stream_line_open: bool = False

        workflow = (
            MagenticBuilder()
            .participants(catalog=catalog_agent, order=order_agent, invoice=invoice_agent)
            .with_standard_manager(
                agent=manager_agent,
                max_round_count=10,
                max_stall_count=3,
                max_reset_count=2,
            )
            .build()
        )

        task = (
            "Process an order for a customer who wants: 3 Apples, 2 Oranges, and 1 Mango. "
            "First, get the product codes and prices from the catalog. "
            "Then create the order with the exact codes. "
            "Finally, generate an invoice showing all codes and the grand total."
        )

        print(f"\nTask: {task}")
        print("\nStarting workflow execution...")

        try:
            output: str | None = None
            async for event in workflow.run_stream(task):
                if isinstance(event, AgentRunUpdateEvent):
                    props = event.data.additional_properties if event.data else None
                    event_type = props.get("magentic_event_type") if props else None

                    if event_type == MAGENTIC_EVENT_TYPE_ORCHESTRATOR:
                        kind = props.get("orchestrator_message_kind", "") if props else ""
                        text = event.data.text if event.data else ""
                        print(f"\n[ORCH:{kind}]\n\n{text}\n{'-' * 26}")
                    elif event_type == MAGENTIC_EVENT_TYPE_AGENT_DELTA:
                        agent_id = props.get("agent_id", event.executor_id) if props else event.executor_id
                        if last_stream_agent_id != agent_id or not stream_line_open:
                            if stream_line_open:
                                print()
                            print(f"\n[STREAM:{agent_id}]: ", end="", flush=True)
                            last_stream_agent_id = agent_id
                            stream_line_open = True
                        if event.data and event.data.text:
                            print(event.data.text, end="", flush=True)
                    elif event.data and event.data.text:
                        print(event.data.text, end="", flush=True)
                elif isinstance(event, WorkflowOutputEvent):
                    output_messages = cast(list[ChatMessage], event.data)
                    if output_messages:
                        output = output_messages[-1].text

            if stream_line_open:
                print()
                stream_line_open = False

            if output is not None:
                print(f"Workflow completed with result:\n\n{output}")

        except Exception as e:
            print(f"Workflow execution failed: {e}")


if __name__ == "__main__":
    # Load .env from the MicrosoftFoundry.Classic directory
    env_path = Path(__file__).resolve().parent.parent.parent.parent / ".env"
    load_dotenv(env_path)
    asyncio.run(main())
