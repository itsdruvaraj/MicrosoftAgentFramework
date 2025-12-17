# Copyright (c) Microsoft. All rights reserved.

import asyncio
import logging
from typing import cast

from dotenv import load_dotenv

from agent_framework import (
    MAGENTIC_EVENT_TYPE_AGENT_DELTA,
    MAGENTIC_EVENT_TYPE_ORCHESTRATOR,
    AgentRunUpdateEvent,
    ChatAgent,
    ChatMessage,
    MagenticBuilder,
    MagenticHumanInterventionDecision,
    MagenticHumanInterventionKind,
    MagenticHumanInterventionReply,
    MagenticHumanInterventionRequest,
    RequestInfoEvent,
    WorkflowOutputEvent,
)
from agent_framework.azure import AzureOpenAIResponsesClient

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

"""
Sample: Magentic Orchestration (multi-agent) - Order Processing with Human Plan Review

What it does:
- Orchestrates three agents in an order processing pipeline with human plan review.
- Before execution begins, the human can approve, revise, or edit the plan.

Product Codes (for validation):
- Apple: 93
- Orange: 97
- Banana: 84
- Mango: 76

- CatalogAgent: Provides the product codes and prices
- OrderAgent: Creates an order using the exact codes from the catalog
- InvoiceAgent: Generates an invoice with the codes and calculates the total

Human Plan Review Options:
1. approve - Approve the plan as-is
2. approve with comments - Approve with feedback for the manager
3. revise - Request revision with your feedback
4. edit - Directly edit the plan text
5. exit - Exit the workflow

Prerequisites:
- Azure OpenAI credentials configured for `AzureOpenAIResponsesClient`.
"""


async def main() -> None:
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
        chat_client=AzureOpenAIResponsesClient(),
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
        chat_client=AzureOpenAIResponsesClient(),
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
        chat_client=AzureOpenAIResponsesClient(),
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
        chat_client=AzureOpenAIResponsesClient(),
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
        .with_plan_review()
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

    def on_exception(exception: Exception) -> None:
        print(f"Exception occurred: {exception}")
        logger.exception("Workflow exception", exc_info=exception)

    try:
        pending_request: RequestInfoEvent | None = None
        pending_responses: dict[str, MagenticHumanInterventionReply] | None = None
        completed = False
        workflow_output: str | None = None

        while not completed:
            # Use streaming for both initial run and response sending
            if pending_responses is not None:
                stream = workflow.send_responses_streaming(pending_responses)
            else:
                stream = workflow.run_stream(task)

            # Collect events from the stream
            async for event in stream:
                if isinstance(event, AgentRunUpdateEvent):
                    props = event.data.additional_properties if event.data else None
                    event_type = props.get("magentic_event_type") if props else None

                    if event_type == MAGENTIC_EVENT_TYPE_ORCHESTRATOR:
                        kind = props.get("orchestrator_message_kind", "") if props else ""
                        text = event.data.text if event.data else ""
                        print(f"\n[ORCH:{kind}]\n\n{text}\n{'-' * 26}")
                    elif event_type == MAGENTIC_EVENT_TYPE_AGENT_DELTA:
                        agent_id = props.get("agent_id", "unknown") if props else "unknown"
                        if last_stream_agent_id != agent_id or not stream_line_open:
                            if stream_line_open:
                                print()
                            print(f"\n[STREAM:{agent_id}]: ", end="", flush=True)
                            last_stream_agent_id = agent_id
                            stream_line_open = True
                        if event.data and event.data.text:
                            print(event.data.text, end="", flush=True)
                elif isinstance(event, RequestInfoEvent) and event.request_type is MagenticHumanInterventionRequest:
                    request = cast(MagenticHumanInterventionRequest, event.data)
                    if request.kind == MagenticHumanInterventionKind.PLAN_REVIEW:
                        pending_request = event
                        if request.plan_text:
                            print(f"\n{'='*50}")
                            print("PLAN REVIEW REQUEST")
                            print(f"{'='*50}")
                            print(request.plan_text)
                            print(f"{'='*50}\n")
                elif isinstance(event, WorkflowOutputEvent):
                    output_messages = cast(list[ChatMessage], event.data)
                    if output_messages:
                        workflow_output = output_messages[-1].text
                    completed = True

            if stream_line_open:
                print()
                stream_line_open = False
            pending_responses = None

            # Handle pending plan review request
            if pending_request is not None:
                print("\nPlan review options:")
                print("1. approve - Approve the plan as-is")
                print("2. approve with comments - Approve with feedback for the manager")
                print("3. revise - Request revision with your feedback")
                print("4. edit - Directly edit the plan text")
                print("5. exit - Exit the workflow")

                while True:
                    choice = input("\nEnter your choice (1-5): ").strip().lower()
                    if choice in ["approve", "1"]:
                        reply = MagenticHumanInterventionReply(decision=MagenticHumanInterventionDecision.APPROVE)
                        break
                    if choice in ["approve with comments", "2"]:
                        comments = input("Enter your comments for the manager: ").strip()
                        reply = MagenticHumanInterventionReply(
                            decision=MagenticHumanInterventionDecision.APPROVE,
                            comments=comments if comments else None,
                        )
                        break
                    if choice in ["revise", "3"]:
                        comments = input("Enter feedback for revising the plan: ").strip()
                        reply = MagenticHumanInterventionReply(
                            decision=MagenticHumanInterventionDecision.REVISE,
                            comments=comments if comments else None,
                        )
                        break
                    if choice in ["edit", "4"]:
                        print("Enter your edited plan (end with an empty line):")
                        lines = []
                        while True:
                            line = input()
                            if line == "":
                                break
                            lines.append(line)
                        edited_plan = "\n".join(lines)
                        reply = MagenticHumanInterventionReply(
                            decision=MagenticHumanInterventionDecision.REVISE,
                            edited_plan_text=edited_plan if edited_plan else None,
                        )
                        break
                    if choice in ["exit", "5"]:
                        print("Exiting workflow...")
                        return
                    print("Invalid choice. Please enter a number 1-5.")

                pending_responses = {pending_request.request_id: reply}
                pending_request = None

        # Show final result
        if workflow_output:
            print(f"\n{'='*50}")
            print("WORKFLOW COMPLETED")
            print(f"{'='*50}")
            print(workflow_output)

    except Exception as e:
        print(f"Workflow execution failed: {e}")
        on_exception(e)


if __name__ == "__main__":
    load_dotenv()
    asyncio.run(main())