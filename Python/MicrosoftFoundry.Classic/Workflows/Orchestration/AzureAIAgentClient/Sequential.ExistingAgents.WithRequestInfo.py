# Copyright (c) Microsoft. All rights reserved.

import asyncio

from azure.identity.aio import DefaultAzureCredential
from dotenv import load_dotenv

from agent_framework import (
    AgentInputRequest,
    ChatAgent,
    ChatMessage,
    RequestInfoEvent,
    Role,
    SequentialBuilder,
    Workflow,
    WorkflowOutputEvent,
    WorkflowRunState,
    WorkflowStatusEvent,
)
from agent_framework.azure import AzureAIAgentClient

"""
Sample: Sequential workflow with participant factories and Request Info - Order Processing

This sample demonstrates how to create a sequential workflow with participant factories
and the with_request_info() method, which allows human steering before each agent runs.

Product Codes (for validation):
- Apple: 93
- Orange: 97
- Banana: 84
- Mango: 76

The with_request_info() method pauses the workflow before each agent runs, emitting a
RequestInfoEvent. This allows external input (e.g., human guidance) to be injected into
the conversation before the agent responds.

In this example, we create a sequential workflow with three existing agents:
CatalogAgent, OrderAgent, and InvoiceAgent. The workflow pauses before each agent
to allow human review and steering.
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
    """Run the workflow with request info handling for human-in-the-loop steering."""
    pending_responses: dict[str, str] | None = None
    workflow_complete = False

    print("Starting order processing workflow with human steering...")
    print("=" * 60)

    while not workflow_complete:
        # Run or continue the workflow
        stream = (
            workflow.send_responses_streaming(pending_responses)
            if pending_responses
            else workflow.run_stream(query)
        )

        pending_responses = None

        # Process events
        async for event in stream:
            if isinstance(event, RequestInfoEvent):
                if isinstance(event.data, AgentInputRequest):
                    # Display pre-agent context for steering
                    print("\n" + "-" * 40)
                    print("REQUEST INFO: INPUT REQUESTED")
                    print(f"About to call agent: {event.data.target_agent_id}")
                    print("-" * 40)
                    print("Conversation context:")
                    recent = (
                        event.data.conversation[-2:] if len(event.data.conversation) > 2 else event.data.conversation
                    )
                    for msg in recent:
                        role = msg.role.value if msg.role else "unknown"
                        text = (msg.text or "")[:200]
                        print(f"  [{role}]: {text}...")
                    print("-" * 40)

                    # Get input to steer the agent (or auto-continue)
                    user_input = input("Your guidance (or press Enter to continue): ")
                    if not user_input.strip():
                        user_input = "Please continue with the order processing."

                    pending_responses = {event.request_id: user_input}
                    print("(Resuming workflow...)")

            elif isinstance(event, WorkflowOutputEvent):
                print("\n" + "=" * 60)
                print("WORKFLOW COMPLETE")
                print("=" * 60)
                print("Final conversation:")
                if event.data:
                    messages: list[ChatMessage] = event.data
                    for message in messages:
                        name = message.author_name or ("assistant" if message.role == Role.ASSISTANT else "user")
                        print(f"{name}: {message.text}")
                workflow_complete = True

            elif isinstance(event, WorkflowStatusEvent) and event.state == WorkflowRunState.IDLE:
                workflow_complete = True


async def main() -> None:
    load_dotenv()

    async with DefaultAzureCredential() as credential:
        # 1) Create a builder with participant factories for order processing
        # Pass credential to factory functions to create clients with existing agent IDs
        # Enable request info to pause before each agent for human steering
        builder = SequentialBuilder().register_participants([
            lambda: create_catalog_agent(credential),
            lambda: create_order_agent(credential),
            lambda: create_invoice_agent(credential),
        ]).with_request_info()

        # 2) Build workflow with request info enabled
        workflow = builder.build()

        # 3) Run workflow with human-in-the-loop handling
        print("=== Order Processing Run with Human Steering ===")
        await run_workflow(
            workflow,
            "Process an order for a customer who wants: 3 Apples, 2 Oranges, and 1 Mango. "
            "First, get the product codes and prices from the catalog. "
            "Then create the order with the exact codes. "
            "Finally, generate an invoice showing all codes and the grand total."
        )

    """
    Sample Output:

    === Order Processing Run with Human Steering ===
    Starting order processing workflow with human steering...
    ============================================================
    
    ----------------------------------------
    REQUEST INFO: INPUT REQUESTED
    About to call agent: CatalogAgent
    ----------------------------------------
    Conversation context:
      [user]: Process an order for a customer who wants: 3 Apples, 2 Oranges, and 1 Mango...
    ----------------------------------------
    Your guidance (or press Enter to continue): 
    (Resuming workflow...)
    
    ----------------------------------------
    REQUEST INFO: INPUT REQUESTED
    About to call agent: OrderAgent
    ----------------------------------------
    Conversation context:
      [assistant]: PRODUCT: Apple, CODE: 93, PRICE: $1.50...
    ----------------------------------------
    Your guidance (or press Enter to continue): Make sure to add tax
    (Resuming workflow...)
    
    ----------------------------------------
    REQUEST INFO: INPUT REQUESTED
    About to call agent: InvoiceAgent
    ----------------------------------------
    Conversation context:
      [assistant]: ITEM: Apple (Code: 93) x 3 = $4.50...
    ----------------------------------------
    Your guidance (or press Enter to continue): 
    (Resuming workflow...)
    
    ============================================================
    WORKFLOW COMPLETE
    ============================================================
    Final conversation:
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