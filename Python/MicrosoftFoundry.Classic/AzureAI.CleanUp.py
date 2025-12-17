# Copyright (c) Microsoft. All rights reserved.

import asyncio
import os
from dotenv import load_dotenv

from azure.ai.agents.aio import AgentsClient
from azure.identity.aio import DefaultAzureCredential

"""
Azure AI Foundry Cleanup Script

This script cleans up all agents and threads created in Microsoft Foundry.
It lists and deletes all agents, threads, vector stores, and files in the specified project.
"""


async def cleanup_agents(agents_client: AgentsClient) -> tuple[int, int]:
    """
    List and delete all agents in the project.
    
    Returns:
        Tuple of (deleted_count, failed_count)
    """
    deleted = 0
    failed = 0
    
    print("\n" + "=" * 50)
    print("CLEANING UP AGENTS")
    print("=" * 50)
    
    try:
        # List all agents - the API returns AsyncItemPaged
        agent_list = []
        async for agent in agents_client.list_agents():
            agent_list.append(agent)
        
        if not agent_list:
            print("No agents found.")
            return deleted, failed
        
        print(f"Found {len(agent_list)} agent(s):\n")
        
        for agent in agent_list:
            agent_name = getattr(agent, 'name', 'Unnamed') or 'Unnamed'
            agent_id = agent.id
            print(f"  - Agent: {agent_name} (ID: {agent_id})")
        
        # Delete agents
        print(f"\nDeleting {len(agent_list)} agent(s)...")
        
        for agent in agent_list:
            try:
                agent_name = getattr(agent, 'name', 'Unnamed') or 'Unnamed'
                agent_id = agent.id
                await agents_client.delete_agent(agent_id)
                print(f"  ✓ Deleted agent: {agent_name} (ID: {agent_id})")
                deleted += 1
            except Exception as e:
                print(f"  ✗ Failed to delete agent {agent_id}: {e}")
                failed += 1
                
    except Exception as e:
        print(f"Error listing agents: {e}")
    
    return deleted, failed


async def cleanup_threads(agents_client: AgentsClient) -> tuple[int, int]:
    """
    List and delete all threads in the project.
    
    Returns:
        Tuple of (deleted_count, failed_count)
    """
    deleted = 0
    failed = 0
    
    print("\n" + "=" * 50)
    print("CLEANING UP THREADS")
    print("=" * 50)
    
    try:
        # List all threads - the API returns AsyncItemPaged
        thread_list = []
        async for thread in agents_client.threads.list():
            thread_list.append(thread)
        
        if not thread_list:
            print("No threads found.")
            return deleted, failed
        
        print(f"Found {len(thread_list)} thread(s):\n")
        
        for thread in thread_list:
            thread_id = thread.id
            created_at = getattr(thread, 'created_at', 'Unknown')
            print(f"  - Thread ID: {thread_id} (Created: {created_at})")
        
        # Delete threads
        print(f"\nDeleting {len(thread_list)} thread(s)...")
        
        for thread in thread_list:
            try:
                thread_id = thread.id
                await agents_client.threads.delete(thread_id)
                print(f"  ✓ Deleted thread: {thread_id}")
                deleted += 1
            except Exception as e:
                print(f"  ✗ Failed to delete thread {thread_id}: {e}")
                failed += 1
                
    except Exception as e:
        print(f"Error listing threads: {e}")
    
    return deleted, failed


async def cleanup_vector_stores(agents_client: AgentsClient) -> tuple[int, int]:
    """
    List and delete all vector stores in the project.
    
    Returns:
        Tuple of (deleted_count, failed_count)
    """
    deleted = 0
    failed = 0
    
    print("\n" + "=" * 50)
    print("CLEANING UP VECTOR STORES")
    print("=" * 50)
    
    try:
        # List all vector stores - the API returns AsyncItemPaged
        vs_list = []
        async for vs in agents_client.vector_stores.list():
            vs_list.append(vs)
        
        if not vs_list:
            print("No vector stores found.")
            return deleted, failed
        
        print(f"Found {len(vs_list)} vector store(s):\n")
        
        for vs in vs_list:
            vs_id = vs.id
            vs_name = getattr(vs, 'name', 'Unnamed') or 'Unnamed'
            print(f"  - Vector Store: {vs_name} (ID: {vs_id})")
        
        # Delete vector stores
        print(f"\nDeleting {len(vs_list)} vector store(s)...")
        
        for vs in vs_list:
            try:
                vs_id = vs.id
                vs_name = getattr(vs, 'name', 'Unnamed') or 'Unnamed'
                await agents_client.vector_stores.delete(vs_id)
                print(f"  ✓ Deleted vector store: {vs_name} (ID: {vs_id})")
                deleted += 1
            except Exception as e:
                print(f"  ✗ Failed to delete vector store {vs_id}: {e}")
                failed += 1
                
    except Exception as e:
        print(f"Error listing vector stores: {e}")
    
    return deleted, failed


async def cleanup_files(agents_client: AgentsClient) -> tuple[int, int]:
    """
    List and delete all files in the project.
    
    Returns:
        Tuple of (deleted_count, failed_count)
    """
    deleted = 0
    failed = 0
    
    print("\n" + "=" * 50)
    print("CLEANING UP FILES")
    print("=" * 50)
    
    try:
        # List all files - files.list() needs to be awaited first
        file_list = []
        files_response = await agents_client.files.list()
        # Check if it's a pageable or has data attribute
        if hasattr(files_response, 'data'):
            file_list = files_response.data
        elif hasattr(files_response, '__aiter__'):
            async for file in files_response:
                file_list.append(file)
        else:
            file_list = list(files_response) if files_response else []
        
        if not file_list:
            print("No files found.")
            return deleted, failed
        
        print(f"Found {len(file_list)} file(s):\n")
        
        for file in file_list:
            file_id = file.id
            file_name = getattr(file, 'filename', 'Unknown') or 'Unknown'
            print(f"  - File: {file_name} (ID: {file_id})")
        
        # Delete files
        print(f"\nDeleting {len(file_list)} file(s)...")
        
        for file in file_list:
            try:
                file_id = file.id
                file_name = getattr(file, 'filename', 'Unknown') or 'Unknown'
                await agents_client.files.delete(file_id)
                print(f"  ✓ Deleted file: {file_name} (ID: {file_id})")
                deleted += 1
            except Exception as e:
                print(f"  ✗ Failed to delete file {file_id}: {e}")
                failed += 1
                
    except Exception as e:
        print(f"Error listing files: {e}")
    
    return deleted, failed


async def main():
    """Main cleanup function."""
    
    print("\n" + "=" * 60)
    print("  AZURE AI FOUNDRY CLEANUP SCRIPT")
    print("=" * 60)
    
    project_endpoint = os.environ.get("AZURE_AI_PROJECT_ENDPOINT") or os.environ.get("PROJECT_ENDPOINT") or os.environ.get("AZURE_AI_PROJECT")
    
    if not project_endpoint:
        print("\nError: AZURE_AI_PROJECT_ENDPOINT environment variable not set.")
        print("Please set the endpoint to your Foundry project.")
        return
    
    print(f"\nProject Endpoint: {project_endpoint}")
    print("\nThis script will delete ALL agents, threads, vector stores, and files")
    print("in your Microsoft Foundry project. This action cannot be undone!")
    
    # Prompt for confirmation
    confirmation = input("\nType 'DELETE ALL' to confirm cleanup: ")
    if confirmation != "DELETE ALL":
        print("\nCleanup cancelled.")
        return
    
    async with (
        DefaultAzureCredential() as credential,
        AgentsClient(endpoint=project_endpoint, credential=credential) as agents_client,
    ):
        # Track totals
        total_deleted = 0
        total_failed = 0
        
        # Cleanup agents
        agents_deleted, agents_failed = await cleanup_agents(agents_client)
        total_deleted += agents_deleted
        total_failed += agents_failed
        
        # Cleanup threads
        threads_deleted, threads_failed = await cleanup_threads(agents_client)
        total_deleted += threads_deleted
        total_failed += threads_failed
        
        # Cleanup vector stores
        vs_deleted, vs_failed = await cleanup_vector_stores(agents_client)
        total_deleted += vs_deleted
        total_failed += vs_failed
        
        # Cleanup files
        files_deleted, files_failed = await cleanup_files(agents_client)
        total_deleted += files_deleted
        total_failed += files_failed
        
        # Print summary
        print("\n" + "=" * 50)
        print("CLEANUP SUMMARY")
        print("=" * 50)
        print(f"\n  Agents deleted:        {agents_deleted} (failed: {agents_failed})")
        print(f"  Threads deleted:       {threads_deleted} (failed: {threads_failed})")
        print(f"  Vector stores deleted: {vs_deleted} (failed: {vs_failed})")
        print(f"  Files deleted:         {files_deleted} (failed: {files_failed})")
        print(f"\n  TOTAL: {total_deleted} resources deleted, {total_failed} failures")
        print("\n" + "=" * 50)
        print("Cleanup complete!")
        print("=" * 50 + "\n")


if __name__ == "__main__":
    load_dotenv()
    asyncio.run(main())
