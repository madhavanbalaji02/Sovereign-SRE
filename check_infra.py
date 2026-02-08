#!/usr/bin/env python3
"""
Sovereign-SRE Infrastructure Verification Script
=================================================
Verifies that all infrastructure components are running and accessible.

Usage:
    python check_infra.py [--docker] [--local]
    
Options:
    --docker  Use Docker internal hostnames (default)
    --local   Use localhost addresses for local development
"""

import asyncio
import sys
import os
from datetime import datetime

try:
    import httpx
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn
except ImportError:
    print("❌ Missing dependencies. Run: pip install httpx rich")
    sys.exit(1)

# =============================================================================
# CONFIGURATION
# =============================================================================

# Check if we're running locally or in Docker
USE_LOCAL = "--local" in sys.argv or os.environ.get("USE_LOCAL", "false").lower() == "true"

if USE_LOCAL:
    OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
    CHROMA_HOST = os.environ.get("CHROMA_HOST", "http://localhost:8000")
    MCP_HOST = os.environ.get("MCP_SERVER_HOST", "http://localhost:8080")
    BACKEND_HOST = os.environ.get("BACKEND_HOST", "http://localhost:8001")
else:
    OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://ollama:11434")
    CHROMA_HOST = os.environ.get("CHROMA_HOST", "http://chromadb:8000")
    MCP_HOST = os.environ.get("MCP_SERVER_HOST", "http://mcp-server:8080")
    BACKEND_HOST = os.environ.get("BACKEND_HOST", "http://backend:8001")

console = Console()

# =============================================================================
# SERVICE CHECKS
# =============================================================================

async def check_ollama(client: httpx.AsyncClient) -> dict:
    """Check Ollama API and list models"""
    try:
        # Check tags endpoint
        response = await client.get(f"{OLLAMA_HOST}/api/tags", timeout=10.0)
        response.raise_for_status()
        data = response.json()
        models = [m.get("name", "unknown") for m in data.get("models", [])]
        
        return {
            "status": "✅ Healthy",
            "models": models if models else ["No models loaded"],
            "details": f"{len(models)} model(s) available"
        }
    except httpx.ConnectError:
        return {"status": "❌ Connection Failed", "models": [], "details": "Cannot connect to Ollama"}
    except Exception as e:
        return {"status": "⚠️ Error", "models": [], "details": str(e)}


async def check_chromadb(client: httpx.AsyncClient) -> dict:
    """Check ChromaDB health"""
    try:
        response = await client.get(f"{CHROMA_HOST}/api/v1/heartbeat", timeout=10.0)
        response.raise_for_status()
        data = response.json()
        
        # Get collections count
        try:
            cols_response = await client.get(f"{CHROMA_HOST}/api/v1/collections", timeout=5.0)
            collections = cols_response.json() if cols_response.status_code == 200 else []
        except:
            collections = []
        
        return {
            "status": "✅ Healthy",
            "heartbeat": data.get("nanosecond_heartbeat", "N/A"),
            "collections": len(collections),
            "details": f"{len(collections)} collection(s)"
        }
    except httpx.ConnectError:
        return {"status": "❌ Connection Failed", "details": "Cannot connect to ChromaDB"}
    except Exception as e:
        return {"status": "⚠️ Error", "details": str(e)}


async def check_mcp_server(client: httpx.AsyncClient) -> dict:
    """Check MCP Server health and tools"""
    try:
        # Health check
        health_response = await client.get(f"{MCP_HOST}/health", timeout=10.0)
        health_response.raise_for_status()
        
        # Get tools
        tools_response = await client.get(f"{MCP_HOST}/tools", timeout=5.0)
        tools = tools_response.json() if tools_response.status_code == 200 else []
        tool_names = [t.get("name", "unknown") for t in tools]
        
        return {
            "status": "✅ Healthy",
            "tools": tool_names,
            "details": f"{len(tool_names)} tool(s) available"
        }
    except httpx.ConnectError:
        return {"status": "❌ Connection Failed", "tools": [], "details": "Cannot connect to MCP Server"}
    except Exception as e:
        return {"status": "⚠️ Error", "tools": [], "details": str(e)}


async def check_backend(client: httpx.AsyncClient) -> dict:
    """Check Backend API health"""
    try:
        response = await client.get(f"{BACKEND_HOST}/health", timeout=10.0)
        response.raise_for_status()
        data = response.json()
        
        return {
            "status": "✅ Healthy",
            "details": data.get("status", "OK")
        }
    except httpx.ConnectError:
        return {"status": "❌ Connection Failed", "details": "Cannot connect to Backend"}
    except Exception as e:
        return {"status": "⚠️ Error", "details": str(e)}


# =============================================================================
# MAIN
# =============================================================================

async def run_checks():
    """Run all infrastructure checks"""
    console.print(Panel.fit(
        "[bold cyan]🔍 Sovereign-SRE Infrastructure Check[/bold cyan]",
        subtitle=f"Mode: {'Local' if USE_LOCAL else 'Docker'}"
    ))
    
    async with httpx.AsyncClient() as client:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Checking services...", total=4)
            
            # Run checks
            progress.update(task, description="Checking Ollama...")
            ollama = await check_ollama(client)
            progress.advance(task)
            
            progress.update(task, description="Checking ChromaDB...")
            chroma = await check_chromadb(client)
            progress.advance(task)
            
            progress.update(task, description="Checking MCP Server...")
            mcp = await check_mcp_server(client)
            progress.advance(task)
            
            progress.update(task, description="Checking Backend...")
            backend = await check_backend(client)
            progress.advance(task)
    
    # Display results
    console.print()
    
    # Services Table
    table = Table(title="Service Status", show_header=True, header_style="bold magenta")
    table.add_column("Service", style="cyan")
    table.add_column("Status")
    table.add_column("Details", style="dim")
    
    table.add_row("Ollama", ollama["status"], ollama.get("details", ""))
    table.add_row("ChromaDB", chroma["status"], chroma.get("details", ""))
    table.add_row("MCP Server", mcp["status"], mcp.get("details", ""))
    table.add_row("Backend", backend["status"], backend.get("details", ""))
    
    console.print(table)
    console.print()
    
    # Models Table
    if ollama.get("models"):
        models_table = Table(title="Ollama Models", show_header=True, header_style="bold green")
        models_table.add_column("Model Name", style="cyan")
        for model in ollama["models"]:
            models_table.add_row(model)
        console.print(models_table)
        console.print()
    
    # MCP Tools Table
    if mcp.get("tools"):
        tools_table = Table(title="MCP Tools", show_header=True, header_style="bold blue")
        tools_table.add_column("Tool Name", style="cyan")
        for tool in mcp["tools"]:
            tools_table.add_row(tool)
        console.print(tools_table)
        console.print()
    
    # Summary
    all_healthy = all([
        "✅" in ollama["status"],
        "✅" in chroma["status"],
        "✅" in mcp["status"],
        "✅" in backend["status"]
    ])
    
    if all_healthy:
        console.print(Panel.fit(
            "[bold green]✅ All systems operational![/bold green]",
            subtitle=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))
        return 0
    else:
        console.print(Panel.fit(
            "[bold yellow]⚠️ Some services are not healthy[/bold yellow]\n"
            "Run [cyan]docker-compose up -d[/cyan] to start services",
            subtitle=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))
        return 1


def main():
    """Entry point"""
    if "--help" in sys.argv or "-h" in sys.argv:
        console.print(__doc__)
        return 0
    
    return asyncio.run(run_checks())


if __name__ == "__main__":
    sys.exit(main())
