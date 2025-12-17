# Copyright (c) Microsoft. All rights reserved.

import asyncio
import logging
from pathlib import Path
from typing import Annotated, cast

from azure.identity import DefaultAzureCredential
from azure.identity.aio import DefaultAzureCredential as AsyncDefaultAzureCredential

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
    ai_function,
)
from agent_framework.azure import AzureOpenAIChatClient

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

"""
Sample: Agent Clarification via Tool Calls in Magentic Workflows

This sample demonstrates how agents can ask clarifying questions to users during
execution via the HITL (Human-in-the-Loop) mechanism.

Scenario: "Onboard Jessica Smith"
- User provides an ambiguous task: "Onboard Jessica Smith"
- The onboarding agent recognizes missing information and uses the ask_user tool
- The ask_user call surfaces as a TOOL_APPROVAL request via RequestInfoEvent
- User provides the answer (e.g., "Engineering, Software Engineer")
- The answer is fed back to the agent as a FunctionResultContent
- Agent continues execution with the clarified information

Why AzureOpenAIChatClient for TOOL_APPROVAL:
    AzureOpenAIChatClient is the recommended client for agent clarification (TOOL_APPROVAL)
    patterns. Server-side stateful clients (AzureAIAgentClient, AzureOpenAIResponsesClient)
    don't work with Magentic's TOOL_APPROVAL pattern because:
    
    1. Agent calls ask_user -> pending tool call stored on server
    2. Human provides answer
    3. Magentic calls agent again with chat history including the function result
    4. But the new API call doesn't link back to the previous server-side state
    5. Server returns: "No tool call found for function call output with call_id..."
    
    AzureOpenAIChatClient is stateless - each call sends the complete chat history,
    so there's no server-side state to get out of sync.

How it works:
1. Agent has an `ask_user` tool decorated with `@ai_function(approval_mode="always_require")`
2. When agent calls `ask_user`, it surfaces as a FunctionApprovalRequestContent
3. MagenticAgentExecutor converts this to a MagenticHumanInterventionRequest(kind=TOOL_APPROVAL)
4. User provides answer via MagenticHumanInterventionReply with response_text
5. The response_text becomes the function result fed back to the agent
6. Agent receives the result and continues processing

Prerequisites:
- Azure OpenAI credentials configured for `AzureOpenAIChatClient`.
- AZURE_OPENAI_ENDPOINT environment variable set.
- AZURE_OPENAI_DEPLOYMENT_NAME environment variable set.
"""


@ai_function(approval_mode="always_require")
def ask_user(question: Annotated[str, "The question to ask the user for clarification"]) -> str:
    """Ask the user a clarifying question to gather missing information.

    Use this tool when you need additional information from the user to complete
    your task effectively. The user's response will be returned so you can
    continue with your work.

    Args:
        question: The question to ask the user

    Returns:
        The user's response to the question
    """
    # This function body is a placeholder - the actual interaction happens via HITL.
    # When the agent calls this tool:
    # 1. The tool call surfaces as a FunctionApprovalRequestContent
    # 2. MagenticAgentExecutor detects this and emits a HITL request
    # 3. The user provides their answer
    # 4. The answer is fed back as the function result
    return f"User was asked: {question}"


async def main() -> None:
    # Get the path to the .env file in MicrosoftFoundry.Classic directory
    env_file = str(Path(__file__).resolve().parent.parent.parent.parent / ".env")
    
    # Use sync DefaultAzureCredential for AzureOpenAIChatClient
    credential = DefaultAzureCredential()
    
    # AzureOpenAIChatClient is stateless - perfect for TOOL_APPROVAL patterns
    # Each call sends the complete chat history, no server-side state conflicts
    # Use base_url for Azure AI Foundry endpoints (services.ai.azure.com)
    base_url = "https://mfbr-ext-eus2-aiml-profx-01.services.ai.azure.com/openai/v1/"
    deployment_name = "gpt-4.1"
    
    onboarding_client = AzureOpenAIChatClient(
        credential=credential,
        base_url=base_url,
        deployment_name=deployment_name,
    )
    manager_client = AzureOpenAIChatClient(
        credential=credential,
        base_url=base_url,
        deployment_name=deployment_name,
    )

    # Create an onboarding agent that asks clarifying questions
    onboarding_agent = ChatAgent(
        name="OnboardingAgent",
        description="HR specialist who handles employee onboarding",
        instructions=(
            "You are an HR Onboarding Specialist. Your job is to onboard new employees.\n\n"
            "IMPORTANT: When given an onboarding request, you MUST gather the following "
            "information before proceeding:\n"
            "1. Department (e.g., Engineering, Sales, Marketing)\n"
            "2. Role/Title (e.g., Software Engineer, Account Executive)\n"
            "3. Start date (if not specified)\n"
            "4. Manager's name (if known)\n\n"
            "CRITICAL: Ask ONLY ONE question at a time using the ask_user tool. "
            "Wait for the user's response before asking the next question. "
            "Do NOT make multiple ask_user calls in parallel.\n\n"
            "Do not proceed with onboarding until you have at least the department and role.\n\n"
            "Once you have the information, create an onboarding plan."
        ),
        chat_client=onboarding_client,
        tools=[ask_user],  # Tool decorated with @ai_function(approval_mode="always_require")
    )

    # Create a manager agent
    manager_agent = ChatAgent(
        name="MagenticManager",
        description="Orchestrator that coordinates the onboarding workflow",
        instructions="You coordinate a team to complete HR tasks efficiently.",
        chat_client=manager_client,
    )

    print("\nBuilding Magentic Workflow with Agent Clarification...")

    workflow = (
        MagenticBuilder()
        .participants(onboarding=onboarding_agent)
        .with_standard_manager(
            agent=manager_agent,
            max_round_count=10,
            max_stall_count=3,
            max_reset_count=2,
        )
        .build()
    )

    # Ambiguous task - agent should ask for clarification
    task = "Onboard Jessica Smith"

    print(f"\nTask: {task}")
    print("(This is intentionally vague - the agent should ask for more details)")
    print("\nStarting workflow execution...")
    print("=" * 60)

    try:
        pending_request: RequestInfoEvent | None = None
        pending_responses: dict[str, object] | None = None
        completed = False
        workflow_output: str | None = None

        last_stream_agent_id: str | None = None
        stream_line_open: bool = False

        while not completed:
            if pending_responses is not None:
                stream = workflow.send_responses_streaming(pending_responses)
            else:
                stream = workflow.run_stream(task)

            async for event in stream:
                if isinstance(event, AgentRunUpdateEvent):
                    props = event.data.additional_properties if event.data else None
                    event_type = props.get("magentic_event_type") if props else None

                    if event_type == MAGENTIC_EVENT_TYPE_ORCHESTRATOR:
                        kind = props.get("orchestrator_message_kind", "") if props else ""
                        text = event.data.text if event.data else ""
                        if stream_line_open:
                            print()
                            stream_line_open = False
                        print(f"\n[ORCHESTRATOR: {kind}]\n{text}\n{'-' * 40}")
                    elif event_type == MAGENTIC_EVENT_TYPE_AGENT_DELTA:
                        agent_id = props.get("agent_id", "unknown") if props else "unknown"
                        if last_stream_agent_id != agent_id or not stream_line_open:
                            if stream_line_open:
                                print()
                            print(f"\n[{agent_id}]: ", end="", flush=True)
                            last_stream_agent_id = agent_id
                            stream_line_open = True
                        if event.data and event.data.text:
                            print(event.data.text, end="", flush=True)

                elif isinstance(event, RequestInfoEvent) and event.request_type is MagenticHumanInterventionRequest:
                    if stream_line_open:
                        print()
                        stream_line_open = False
                    pending_request = event
                    req = cast(MagenticHumanInterventionRequest, event.data)

                    if req.kind == MagenticHumanInterventionKind.TOOL_APPROVAL:
                        print("\n" + "=" * 60)
                        print("AGENT ASKING FOR CLARIFICATION")
                        print("=" * 60)
                        print(f"\nAgent: {req.agent_id}")
                        print(f"Question: {req.prompt}")
                        if req.context:
                            print(f"Details: {req.context}")
                        print()

                elif isinstance(event, WorkflowOutputEvent):
                    if stream_line_open:
                        print()
                        stream_line_open = False
                    workflow_output = event.data if event.data else None
                    completed = True

            if stream_line_open:
                print()
                stream_line_open = False
            pending_responses = None

            if pending_request is not None:
                req = cast(MagenticHumanInterventionRequest, pending_request.data)

                if req.kind == MagenticHumanInterventionKind.TOOL_APPROVAL:
                    # Agent is asking for clarification
                    print("Please provide your answer:")
                    answer = input("> ").strip()  # noqa: ASYNC250

                    if answer.lower() == "exit":
                        print("Exiting workflow...")
                        return

                    # Send the answer back - it will be fed to the agent as the function result
                    reply = MagenticHumanInterventionReply(
                        decision=MagenticHumanInterventionDecision.APPROVE,
                        response_text=answer if answer else "No additional information provided.",
                    )
                    pending_responses = {pending_request.request_id: reply}
                pending_request = None

        print("\n" + "=" * 60)
        print("WORKFLOW COMPLETED")
        print("=" * 60)
        if workflow_output:
            messages = cast(list[ChatMessage], workflow_output)
            if messages:
                final_msg = messages[-1]
                print(f"\nFinal Result:\n{final_msg.text}")

        except Exception as e:
            print(f"Workflow execution failed: {e}")
            logger.exception("Workflow exception", exc_info=e)


if __name__ == "__main__":
    asyncio.run(main())
