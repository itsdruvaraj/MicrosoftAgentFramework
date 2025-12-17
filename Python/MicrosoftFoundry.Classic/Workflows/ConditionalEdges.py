# Copyright (c) Microsoft. All rights reserved.

import asyncio
from typing import Any

from azure.identity.aio import DefaultAzureCredential
from dotenv import load_dotenv

from agent_framework import (
    AgentExecutorRequest,
    AgentExecutorResponse,
    ChatAgent,
    ChatMessage,
    Role,
    WorkflowBuilder,
    WorkflowContext,
    executor,
)
from agent_framework.azure import AzureAIAgentClient
from pydantic import BaseModel
from typing_extensions import Never

"""
Sample: Conditional Edges with Stop on Failure

This sample demonstrates how to use conditional edges to control workflow execution
based on agent response validation. If an agent's response indicates failure or
doesn't contain expected data, the workflow routes to an error handler instead
of continuing to the next agent.

Order Processing Flow:
1. CatalogAgent - Retrieves product codes and prices
2. Validation - Check if catalog response is valid
   - If valid: Continue to OrderAgent
   - If invalid: Route to ErrorHandler (stop workflow)
3. OrderAgent - Creates the order
4. InvoiceAgent - Generates invoice

Product Codes (for validation):
- Apple: 93
- Orange: 97
- Banana: 84
- Mango: 76
"""


# Agent IDs for existing agents in Azure AI Foundry
CATALOG_AGENT_ID = "asst_Fcv2cxSExE2lePzBGB3L3z5H"
ORDER_AGENT_ID = "asst_2PHQdBB4vDXgW69gVKSI35CF"
INVOICE_AGENT_ID = "asst_8058Ofu6OAuddxL3Vjqk6eup"


class ValidationResult(BaseModel):
    """Result of validating an agent response."""
    is_valid: bool
    error_message: str | None = None


def is_valid_response(response: AgentExecutorResponse) -> bool:
    """Check if the agent response is valid and contains expected content."""
    if response is None or response.agent_run_response is None:
        return False
    
    text = response.agent_run_response.text.lower()
    
    # Check for error indicators
    error_indicators = ["error", "failed", "cannot", "unable", "sorry"]
    if any(indicator in text for indicator in error_indicators):
        return False
    
    # Check that we have some meaningful content
    if len(response.agent_run_response.text.strip()) < 10:
        return False
    
    return True


def is_invalid_response(response: AgentExecutorResponse) -> bool:
    """Inverse of is_valid_response for routing to error handler."""
    return not is_valid_response(response)


@executor(id="error_handler")
async def error_handler(response: AgentExecutorResponse, ctx: WorkflowContext[Never, str]) -> None:
    """Handle invalid responses by yielding an error message and stopping the workflow."""
    error_text = "Unknown error"
    if response and response.agent_run_response:
        error_text = response.agent_run_response.text[:200]
    
    await ctx.yield_output(f"WORKFLOW STOPPED: Agent response validation failed.\nDetails: {error_text}")


@executor(id="success_handler")
async def success_handler(response: AgentExecutorResponse, ctx: WorkflowContext[Never, str]) -> None:
    """Handle successful workflow completion."""
    if response and response.agent_run_response:
        await ctx.yield_output(f"ORDER COMPLETE:\n{response.agent_run_response.text}")
    else:
        await ctx.yield_output("ORDER COMPLETE (no details available)")


def create_catalog_agent(credential) -> ChatAgent:
    """Create a ChatAgent using an existing Azure AI Agent."""
    return ChatAgent(
        chat_client=AzureAIAgentClient(
            credential=credential,
            agent_id=CATALOG_AGENT_ID,
        ),
        name="CatalogAgent",
    )


def create_broken_tool():
    """Create a tool that will fail when called."""
    from agent_framework import ai_function
    
    @ai_function(description="Process order by connecting to the order database. YOU MUST CALL THIS FUNCTION for every order.")
    def process_order_database(order_items: str) -> str:
        """Process the order items by connecting to the database. This is required for all orders."""
        raise ConnectionError("DATABASE ERROR: Failed to connect to order database at orders.internal.example.com:5432 - Connection refused")
    
    return process_order_database


async def create_order_agent_with_broken_tool(credential) -> ChatAgent:
    """Create a NEW Foundry agent with a broken tool that will fail.
    
    This creates an agent in Azure AI Foundry with instructions that FORCE it to use
    the broken tool, which will raise an exception.
    """
    broken_tool = create_broken_tool()
    
    # Create a new agent in Foundry with the broken tool
    agent_client = AzureAIAgentClient(
        credential=credential,
        should_cleanup_agent=True  # Clean up after the test
    )
    
    # Create the agent with instructions that REQUIRE using the tool
    # This returns a ChatAgent context manager
    chat_agent = await agent_client.create_agent(
        name="OrderAgent-BrokenTool",
        instructions="""You are an order processing agent. 
        
        CRITICAL: For EVERY order you receive, you MUST call the process_order_database function.
        Do NOT process orders manually - you MUST use the tool.
        The tool is required for compliance and auditing purposes.
        
        When you receive order items, immediately call process_order_database with the items.""",
        tools=[broken_tool]
    ).__aenter__()
    
    return chat_agent


def create_invoice_agent(credential) -> ChatAgent:
    """Create a ChatAgent using an existing Azure AI Agent."""
    return ChatAgent(
        chat_client=AzureAIAgentClient(
            credential=credential,
            agent_id=INVOICE_AGENT_ID,
        ),
        name="InvoiceAgent",
    )


async def main() -> None:
    load_dotenv()

    async with DefaultAzureCredential() as credential:
        # Create the broken order agent first (it's async)
        print("Creating OrderAgent with broken tool...")
        order_agent = await create_order_agent_with_broken_tool(credential)
        
        # Build workflow with conditional edges
        # Each agent's output is validated before proceeding to the next
        workflow = (
            WorkflowBuilder()
            # Register agents
            .register_agent(lambda: create_catalog_agent(credential), name="CatalogAgent")
            .register_agent(lambda: order_agent, name="OrderAgent")  # Use pre-created agent
            .register_agent(lambda: create_invoice_agent(credential), name="InvoiceAgent")
            # Register handlers
            .register_executor(lambda: error_handler, name="ErrorHandler")
            .register_executor(lambda: success_handler, name="SuccessHandler")
            # Set start executor
            .set_start_executor("CatalogAgent")
            # CatalogAgent -> OrderAgent (only if valid response)
            .add_edge("CatalogAgent", "OrderAgent", condition=is_valid_response)
            # CatalogAgent -> ErrorHandler (if invalid response)
            .add_edge("CatalogAgent", "ErrorHandler", condition=is_invalid_response)
            # OrderAgent -> InvoiceAgent (only if valid response)
            .add_edge("OrderAgent", "InvoiceAgent", condition=is_valid_response)
            # OrderAgent -> ErrorHandler (if invalid response)
            .add_edge("OrderAgent", "ErrorHandler", condition=is_invalid_response)
            # InvoiceAgent -> SuccessHandler (only if valid response)
            .add_edge("InvoiceAgent", "SuccessHandler", condition=is_valid_response)
            # InvoiceAgent -> ErrorHandler (if invalid response)
            .add_edge("InvoiceAgent", "ErrorHandler", condition=is_invalid_response)
            .build()
        )

        # Create request for the workflow
        request = AgentExecutorRequest(
            messages=[
                ChatMessage(
                    Role.USER,
                    text="Process an order for a customer who wants: 3 Apples, 2 Oranges, and 1 Mango. "
                         "First, get the product codes and prices from the catalog. "
                         "Then create the order with the exact codes. "
                         "Finally, generate an invoice showing all codes and the grand total."
                )
            ],
            should_respond=True,
        )

        # Run workflow
        print("=== Order Processing with Conditional Edges ===")
        events = await workflow.run(request)
        outputs = events.get_outputs()

        if outputs:
            print(f"\nWorkflow Output:\n{outputs[0]}")
        else:
            print("No outputs received from the workflow.")

    """
    Sample Output (Success):
    
    === Order Processing with Conditional Edges ===
    
    Workflow Output:
    ORDER COMPLETE:
    INVOICE
    ---
    Apple (Code: 93) x 3 = $4.50
    Orange (Code: 97) x 2 = $2.50
    Mango (Code: 76) x 1 = $2.00
    ---
    GRAND TOTAL: $9.00
    CODES USED: 93, 97, 76

    Sample Output (Failure - if CatalogAgent returns error):
    
    === Order Processing with Conditional Edges ===
    
    Workflow Output:
    WORKFLOW STOPPED: Agent response validation failed.
    Details: Sorry, I couldn't find those products in the catalog...
    """


if __name__ == "__main__":
    asyncio.run(main())
