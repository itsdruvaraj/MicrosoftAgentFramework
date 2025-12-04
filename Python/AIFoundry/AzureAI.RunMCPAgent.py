# Copyright (c) Microsoft. All rights reserved.

import asyncio
from dotenv import load_dotenv

from agent_framework import ChatAgent, MCPStreamableHTTPTool, HostedMCPTool
from agent_framework.azure import AzureAIAgentClient
from azure.identity.aio import AzureCliCredential
from pydantic import Field

"""
Azure AI Agent with Microsoft Learn MCP Tool Example
"""

async def main():

    async with (
        AzureCliCredential() as credential,
        ChatAgent(
            chat_client=AzureAIAgentClient(
                async_credential=credential, 
                agent_id="asst_U2bDCEO78J8KmkCyA6rn1yyH"
            ),
            tools=[MCPStreamableHTTPTool(
                name="AgentFrameworkMCPTool10",
                url="https://app-ext-eus2-mcp-profx-01.azurewebsites.net/mcp",
                approval_mode="never_require",
                allowed_tools=["celsius_to_fahrenheit"],
                headers={"Authorization": "Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsIng1dCI6InJ0c0ZULWItN0x1WTdEVlllU05LY0lKN1ZuYyIsImtpZCI6InJ0c0ZULWItN0x1WTdEVlllU05LY0lKN1ZuYyJ9.eyJhdWQiOiJhcGk6Ly9hZjYzMzliYS02MzlkLTQ2MTYtYjk1OS04ZDk4NDhhNGZhYTMiLCJpc3MiOiJodHRwczovL3N0cy53aW5kb3dzLm5ldC85NzhiYmFkMi0wMzdmLTQ4NTktOGE3OC0zODVkMzZkMjY0ZWUvIiwiaWF0IjoxNzY0ODMxNzg2LCJuYmYiOjE3NjQ4MzE3ODYsImV4cCI6MTc2NDgzNTY4NiwiYWlvIjoiazJKZ1lKQ2VzUDlldDgxQi9XTnp3MjRXaXBibEFRQT0iLCJhcHBpZCI6ImFmNjMzOWJhLTYzOWQtNDYxNi1iOTU5LThkOTg0OGE0ZmFhMyIsImFwcGlkYWNyIjoiMSIsImlkcCI6Imh0dHBzOi8vc3RzLndpbmRvd3MubmV0Lzk3OGJiYWQyLTAzN2YtNDg1OS04YTc4LTM4NWQzNmQyNjRlZS8iLCJvaWQiOiIyNzAyOTc3YS0wMTJlLTQ5MmUtYjhhNi04NTVjYTA0MjVhYzkiLCJyaCI6IjEuQVdNQjBycUxsMzhEV1VpS2VEaGROdEprN3JvNVk2LWRZeFpHdVZtTm1FaWstcVBJQVFCakFRLiIsInN1YiI6IjI3MDI5NzdhLTAxMmUtNDkyZS1iOGE2LTg1NWNhMDQyNWFjOSIsInRpZCI6Ijk3OGJiYWQyLTAzN2YtNDg1OS04YTc4LTM4NWQzNmQyNjRlZSIsInV0aSI6IkYzZlVJV1dYQWtDSURKNDJQZ0pQQVEiLCJ2ZXIiOiIxLjAiLCJ4bXNfZnRkIjoicDNYYVI1akRfbHBsdVFFcm5fRUc5OENESWR4YVRDLUszODliNy1VSk9NQUJkWE4zWlhOME15MWtjMjF6In0.ZD54-D3SiBtsNi8ULI-Hoz1ur4tk1lveyOx1v2WS_Gzpl1p7NmkmjpFo_xIRZV1OUVDyBnNX0KXrYdjOSqhCN_RwCQrH2FusZt9U6V4NhydjNmCavhLCdURAGAQHmvXVefSLqK8NvxHs2WM1_oR_KY-tFb2iOwd0teqXhwlkAEoU6CY-je_g18Jfcj-ImHdFXL8aI7XwZtmL9r1-T_N2jTduPXIfZ7tg0TM7deNPIJ5K__y50cNPCW9g2OT7Zip7bng97ojrvT0-vi3IyQh-_NZire_DtWtlHGTALunc31S0hg7GmIOPQaHVgUU6oP0djcBg4jL1EcRrMWi5mppdpg"},
            )],
        ) as agent,

    ):
        print("Starting agent run...")
        result = await agent.run("Convert 100 degrees Celsius to Fahrenheit")
        print("Agent run completed")
        print(f"Result text length: {len(result.text) if result.text else 0}")
        if result.text:
            print(result.text)
        else:
            print("No text in result")

if __name__ == "__main__":
    load_dotenv()
    asyncio.run(main())