# Copyright (c) Microsoft. All rights reserved.

import asyncio

from azure.identity.aio import DefaultAzureCredential
from dotenv import load_dotenv

from agent_framework import (
    ChatAgent,
    ChatMessage,
    FileCheckpointStorage,
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

NOTE: Checkpointing with AzureAIAgentClient
===========================================
When using AzureAIAgentClient with checkpointing:

1. Workflow-level messages (in the `messages` and `full_conversation` sections) ARE
   captured in checkpoints and used when resuming.

2. The `service_thread_id` (e.g., "thread_jARWduNCvlFG3tlwBw3RdFqK") is also captured,
   allowing the agent to continue on the same server-side thread if needed.

3. When resuming from a checkpoint, the framework uses the captured message state to
   determine where to continue execution in the workflow graph.

This means checkpointing works correctly for Azure AI agents - the workflow state is
properly preserved and restored.
"""


# Agent IDs for existing agents in Azure AI Foundry
CATALOG_AGENT_ID = "asst_Fcv2cxSExE2lePzBGB3L3z5H"  # Replace with your existing Catalog Agent ID
ORDER_AGENT_ID = "asst_2PHQdBB4vDXgW69gVKSI35CF"  # Replace with your existing Order Agent ID
INVOICE_AGENT_ID = "asst_8058Ofu6OAuddxL3Vjqk6eup"  # Replace with your existing Invoice Agent ID


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


async def run_workflow(workflow: Workflow, query: str | None = None, checkpoint_id: str | None = None) -> None:
    """Run or resume a workflow.
    
    Args:
        workflow: The workflow to run
        query: The input message for a new run (mutually exclusive with checkpoint_id)
        checkpoint_id: The checkpoint ID to resume from (mutually exclusive with query)
    """
    if checkpoint_id:
        print(f"Resuming from checkpoint: {checkpoint_id}")
        events = await workflow.run(checkpoint_id=checkpoint_id)
    else:
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

    # Initialize checkpoint storage for persistence
    checkpoint_storage = FileCheckpointStorage(storage_path="./checkpoints")

    # Check for existing checkpoints to resume from
    existing_checkpoints = await checkpoint_storage.list_checkpoints()
    selected_checkpoint = None
    
    if existing_checkpoints:
        # Sort by timestamp to show checkpoints in order
        sorted_checkpoints = sorted(existing_checkpoints, key=lambda cp: cp.timestamp)
        print(f"Found {len(existing_checkpoints)} existing checkpoint(s):")
        for i, cp in enumerate(sorted_checkpoints):
            print(f"  [{i}] ID: {cp.checkpoint_id[:20]}..., Timestamp: {cp.timestamp}")
        print(f"  [n] Start a new workflow run")
        
        # Ask user which checkpoint to use
        choice = input("\nEnter checkpoint number to resume, or 'n' for new run: ").strip().lower()
        
        if choice != 'n' and choice != '':
            try:
                idx = int(choice)
                if 0 <= idx < len(sorted_checkpoints):
                    selected_checkpoint = sorted_checkpoints[idx]
                    print(f"Selected checkpoint: {selected_checkpoint.checkpoint_id}")
                else:
                    print(f"Invalid index. Starting new run.")
            except ValueError:
                print(f"Invalid input. Starting new run.")
    else:
        print("No existing checkpoints found. Starting new run.")

    async with DefaultAzureCredential() as credential:
        # 1) Create a builder with participant factories for order processing
        # Pass credential to factory functions to create clients with existing agent IDs
        builder = SequentialBuilder().register_participants([
            lambda: create_catalog_agent(credential),
            lambda: create_order_agent(credential),
            lambda: create_invoice_agent(credential),
        ]).with_checkpointing(checkpoint_storage)

        # 2) Build the workflow
        workflow = builder.build()

        # 3) Either resume from selected checkpoint or start a new run
        if selected_checkpoint:
            print(f"\n=== Resuming from Checkpoint ===")
            await run_workflow(workflow, checkpoint_id=selected_checkpoint.checkpoint_id)
        else:
            # Start a new workflow run
            print("\n=== Order Processing Run (New) ===")
            await run_workflow(
                workflow,
                query="Process an order for a customer who wants: 3 Apples, 2 Oranges, and 1 Mango. "
                "First, get the product codes and prices from the catalog. "
                "Then create the order with the exact codes. "
                "Finally, generate an invoice showing all codes and the grand total."
            )

    """
    Sample Output (New Run):

    Found 0 existing checkpoint(s):
    
    === Order Processing Run (New) ===
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

    Sample Output (Resume from Checkpoint):

    Found 3 existing checkpoint(s):
      [0] ID: abc123..., Timestamp: 2025-12-17T10:00:00
      [1] ID: def456..., Timestamp: 2025-12-17T10:00:01
      [2] ID: ghi789..., Timestamp: 2025-12-17T10:00:02

    === Resuming from Checkpoint ===
    Resuming from checkpoint: ghi789...
    InvoiceAgent: INVOICE
                  ---
                  (continues from where it left off)
    """


if __name__ == "__main__":
    asyncio.run(main())