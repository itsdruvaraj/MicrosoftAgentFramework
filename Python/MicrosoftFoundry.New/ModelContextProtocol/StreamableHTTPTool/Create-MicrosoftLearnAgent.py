# Copyright (c) Microsoft. All rights reserved.

import asyncio
import logging
import os
import warnings
from pathlib import Path

# Suppress asyncio cleanup errors (known MCP client issue during shutdown)
logging.getLogger("asyncio").setLevel(logging.WARNING)
warnings.filterwarnings("ignore", message=".*cancel scope.*")

# Enable detailed HTTP tracing (set to INFO for less verbose output)
logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")

# Azure SDK HTTP logging (shows requests/responses)
logging.getLogger("azure.core.pipeline.policies.http_logging_policy").setLevel(logging.INFO)

# httpx logging (used by MCP clients)
logging.getLogger("httpx").setLevel(logging.INFO)

# MCP client logging (set to INFO to see tool calls without noise)
logging.getLogger("mcp").setLevel(logging.INFO)

# Agent Framework internal logging
logging.getLogger("agent_framework").setLevel(logging.INFO)

from agent_framework import MCPStreamableHTTPTool
from agent_framework.azure import AzureAIProjectAgentProvider
from agent_framework.observability import configure_otel_providers
from azure.identity.aio import AzureCliCredential

"""
Azure AI Agent with Local MCP Example

This sample demonstrates integration of Azure AI Agents with local Model Context Protocol (MCP)
servers using MCPStreamableHTTPTool.

Pre-requisites:
- Set AZURE_AI_PROJECT_ENDPOINT and AZURE_AI_MODEL_DEPLOYMENT_NAME environment variables.
"""
from dotenv import load_dotenv

# Load .env from parent directory
ENV_PATH = Path(__file__).parent.parent / ".env"

# ========== TRACING SETUP ==========
# Option 1: Local AI Toolkit trace viewer
configure_otel_providers(
    vs_code_extension_port=4317,  # AI Toolkit gRPC port
    enable_sensitive_data=True,   # Capture prompts, completions, and tool results
)

# Option 2: Send traces to Azure AI Foundry (uncomment to enable)
# This enables tracing in the Foundry portal under "Tracing" tab
from azure.core.settings import settings
settings.tracing_implementation = "opentelemetry"
os.environ["AZURE_TRACING_GEN_AI_INCLUDE_BINARY_DATA"] = "true"

from azure.ai.projects.telemetry import AIProjectInstrumentor
AIProjectInstrumentor().instrument(enable_content_recording=True)
# ========== END TRACING SETUP ==========

async def main() -> None:
    """Example showing MCPStreamableHTTPTool with Azure AI Agent.
    
    Note: With AzureAIProjectAgentProvider, the MCP connection happens SERVER-SIDE
    in Azure AI Foundry, not locally. The MCPStreamableHTTPTool definition is sent
    to the Azure service, which then connects to the MCP server.
    """
    print("=== Azure AI Agent with Local MCP Tools ===\n")
    load_dotenv(ENV_PATH)

    async with (
        AzureCliCredential() as credential,
        AzureAIProjectAgentProvider(credential=credential) as provider,
    ):
        
        mcp_tool = MCPStreamableHTTPTool(
            name="Microsoft Learn MCP",
            url="https://learn.microsoft.com/api/mcp",
        )

        agent = await provider.create_agent(
            name="StreamableDocsAgent",
            instructions="You are a helpful assistant that can help with Microsoft documentation questions. Always use the provided tool to look up answers from the Microsoft Learn MCP server.Provide references in your answers.",
            tools=mcp_tool
        )

        first_query = "What is Azure Sphere?"
        print(f"User: {first_query}")
        first_result = await agent.run(first_query, tools=[mcp_tool])
        print(f"Agent: {first_result}")
        print("\n=======================================\n")


if __name__ == "__main__":
    asyncio.run(main())