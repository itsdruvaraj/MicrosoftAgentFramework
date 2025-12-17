# Copyright (c) Microsoft. All rights reserved.

import asyncio

from azure.identity.aio import DefaultAzureCredential
from dotenv import load_dotenv

from agent_framework import (
    ChatAgent,
    ChatMessage,
    ExecutorFailedEvent,
    Role,
    SequentialBuilder,
    Workflow,
    WorkflowFailedEvent,
    WorkflowStatusEvent,
    WorkflowRunState,
)
from agent_framework.azure import AzureAIAgentClient

"""
Sample: Sequential workflow with Error Handling - Raise Exception to Stop

This sample demonstrates how raising an exception in an agent's response triggers
ExecutorFailedEvent and WorkflowFailedEvent, stopping the workflow immediately.

When an agent encounters an error condition and raises an exception:
1. ExecutorFailedEvent is emitted with the executor ID and exception details
2. WorkflowFailedEvent is emitted with structured error details
3. WorkflowStatusEvent with FAILED state is emitted
4. The workflow stops - no subsequent agents execute

Order Processing Flow:
1. CatalogAgent - Retrieves product codes and prices (may raise exception)
2. OrderAgent - Creates the order (skipped if CatalogAgent fails)
3. InvoiceAgent - Generates invoice (skipped if any previous agent fails)

Product Codes (for validation):
- Apple: 93
- Orange: 97
- Banana: 84
- Mango: 76
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
    """Create a ChatAgent using a FAKE agent ID to simulate failure.
    
    This uses a non-existent agent ID to demonstrate how the workflow
    handles agent failures. When this agent is invoked, it will raise
    an exception which triggers ExecutorFailedEvent and WorkflowFailedEvent.
    """
    # Using a fake agent ID that doesn't exist - this will cause an error
    FAKE_ORDER_AGENT_ID = "asst_FAKE_DOES_NOT_EXIST_12345"
    
    return ChatAgent(
        chat_client=AzureAIAgentClient(
            credential=credential,
            agent_id=FAKE_ORDER_AGENT_ID,  # This will fail!
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
    """Run workflow with streaming to observe ExecutorFailedEvent and WorkflowFailedEvent.
    
    When an agent raises an exception:
    1. ExecutorFailedEvent is emitted - contains executor ID and exception
    2. WorkflowFailedEvent is emitted - contains structured error details
    3. WorkflowStatusEvent(FAILED) is emitted - terminal state
    4. The exception is re-raised after all events are yielded
    """
    try:
        async for event in workflow.run_stream(query):
            # Monitor for failure events
            if isinstance(event, ExecutorFailedEvent):
                print(f"\n[ExecutorFailedEvent] Executor '{event.executor_id}' failed!")
                print(f"  Exception: {event.data}")
                
            elif isinstance(event, WorkflowFailedEvent):
                print(f"\n[WorkflowFailedEvent] Workflow failed!")
                print(f"  Error Type: {event.details.error_type}")
                print(f"  Message: {event.details.message}")
                if event.details.executor_id:
                    print(f"  Failed Executor: {event.details.executor_id}")
                    
            elif isinstance(event, WorkflowStatusEvent):
                if event.state == WorkflowRunState.FAILED:
                    print(f"\n[WorkflowStatusEvent] State: FAILED - Workflow stopped")
                elif event.state == WorkflowRunState.IDLE:
                    print(f"\n[WorkflowStatusEvent] State: IDLE - Workflow completed successfully")
                    
    except Exception as e:
        # The exception is re-raised after WorkflowFailedEvent
        print(f"\n=== Caught Exception ===")
        print(f"Type: {type(e).__name__}")
        print(f"Message: {str(e)}")
        print("\nWorkflow stopped - subsequent agents did NOT execute.")


async def main() -> None:
    load_dotenv()

    async with DefaultAzureCredential() as credential:
        # Create a simple sequential workflow
        # If any agent raises an exception, the workflow stops immediately
        builder = SequentialBuilder().register_participants([
            lambda: create_catalog_agent(credential),
            lambda: create_order_agent(credential),
            lambda: create_invoice_agent(credential),
        ])

        workflow = builder.build()

        # Run workflow - if any agent fails, ExecutorFailedEvent and WorkflowFailedEvent
        # will be emitted and the workflow will stop
        print("=== Order Processing with Exception-based Error Handling ===")
        print("(If any agent raises an exception, the workflow stops immediately)")
        await run_workflow(
            workflow,
            "Process an order for a customer who wants: 3 Apples, 2 Oranges, and 1 Mango. "
            "First, get the product codes and prices from the catalog. "
            "Then create the order with the exact codes. "
            "Finally, generate an invoice showing all codes and the grand total."
        )

    """
    Sample Output (Success - all agents complete):

    === Order Processing with Exception-based Error Handling ===
    (If any agent raises an exception, the workflow stops immediately)
    
    [WorkflowStatusEvent] State: IDLE - Workflow completed successfully
    
    Sample Output (Failure - agent raises exception):

    === Order Processing with Exception-based Error Handling ===
    (If any agent raises an exception, the workflow stops immediately)
    
    [ExecutorFailedEvent] Executor 'CatalogAgent' failed!
      Exception: RuntimeError('Product not found in catalog')
    
    [WorkflowFailedEvent] Workflow failed!
      Error Type: RuntimeError
      Message: Product not found in catalog
      Failed Executor: CatalogAgent
    
    [WorkflowStatusEvent] State: FAILED - Workflow stopped
    
    === Caught Exception ===
    Type: RuntimeError
    Message: Product not found in catalog
    
    Workflow stopped - subsequent agents did NOT execute.
    """


if __name__ == "__main__":
    asyncio.run(main())