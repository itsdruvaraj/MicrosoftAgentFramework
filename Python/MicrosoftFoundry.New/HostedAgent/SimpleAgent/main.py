# Copyright (c) Microsoft. All rights reserved.
"""
Simple Hosted Agent Example

This demonstrates the minimal setup for a hosted agent in Microsoft Foundry.
The agent runs locally on localhost:8088 and can be deployed to Foundry Agent Service.
"""

from agent_framework.azure import AzureOpenAIResponsesClient
from azure.ai.agentserver.agentframework import from_agent_framework
from azure.identity import DefaultAzureCredential

from dotenv import load_dotenv


def create_simple_agent():
    """Create a simple conversational agent."""
    
    # Create the Azure OpenAI client
    client = AzureOpenAIResponsesClient(
        credential=DefaultAzureCredential(),
        # These can be set via environment variables:
        # AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_DEPLOYMENT_NAME
    )
    
    # Create and return the agent
    agent = client.create_agent(
        name="SimpleAgent",
        instructions="""You are a helpful, friendly assistant. 
        Keep your responses concise and helpful.
        If you don't know something, say so honestly.""",
    )
    
    return agent


def main():
    """Entry point - wraps agent with hosting adapter and starts server."""
    load_dotenv()

    # Create the agent
    agent = create_simple_agent()
    
    # Wrap with hosting adapter and run
    # This starts a web server on localhost:8088
    # The adapter handles:
    # - HTTP endpoints for the Foundry Responses API
    # - Conversation management
    # - Streaming support (SSE)
    # - OpenTelemetry tracing
    from_agent_framework(agent).run()


if __name__ == "__main__":
    main()
