"""
Sovereign-SRE MCP Server
=========================
Model Context Protocol server exposing tools for repository analysis and command execution.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, Any
import os
import json
from datetime import datetime

from tools.read_repo_structure import read_repo_structure, RepoStructureRequest
from tools.execute_shell_command import execute_shell_command, ShellCommandRequest

# =============================================================================
# APP INITIALIZATION
# =============================================================================

app = FastAPI(
    title="Sovereign-SRE MCP Server",
    description="Model Context Protocol server for autonomous SRE operations",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =============================================================================
# MCP PROTOCOL MODELS
# =============================================================================

class MCPToolDefinition(BaseModel):
    """MCP Tool definition schema"""
    name: str
    description: str
    input_schema: dict


class MCPToolCallRequest(BaseModel):
    """MCP Tool call request"""
    name: str
    arguments: dict = Field(default_factory=dict)


class MCPToolCallResponse(BaseModel):
    """MCP Tool call response"""
    content: list[dict]
    is_error: bool = False


# =============================================================================
# TOOL REGISTRY
# =============================================================================

TOOLS: list[MCPToolDefinition] = [
    MCPToolDefinition(
        name="read_repo_structure",
        description=(
            "Recursively scans a repository directory and returns its structure "
            "as a tree. Useful for understanding project layout, finding files, "
            "and navigating codebases."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to scan (relative to workspace root)",
                    "default": "."
                },
                "max_depth": {
                    "type": "integer",
                    "description": "Maximum depth to recurse",
                    "default": 5
                },
                "include_hidden": {
                    "type": "boolean",
                    "description": "Include hidden files/directories",
                    "default": False
                },
                "file_extensions": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Filter by file extensions (e.g., ['.py', '.js'])",
                    "default": None
                }
            },
            "required": []
        }
    ),
    MCPToolDefinition(
        name="execute_shell_command",
        description=(
            "Executes a shell command in a sandboxed environment. "
            "Use for running tests, checking status, or performing safe operations. "
            "Commands that modify files require explicit approval."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The shell command to execute"
                },
                "working_dir": {
                    "type": "string",
                    "description": "Working directory (relative to workspace)",
                    "default": "."
                },
                "timeout": {
                    "type": "integer",
                    "description": "Command timeout in seconds",
                    "default": 30
                },
                "safe_mode": {
                    "type": "boolean",
                    "description": "If true, block potentially destructive commands",
                    "default": True
                }
            },
            "required": ["command"]
        }
    )
]


# =============================================================================
# HEALTH & INFO ENDPOINTS
# =============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "mcp-server"
    }


@app.get("/info")
async def server_info():
    """Server information"""
    return {
        "name": "Sovereign-SRE MCP Server",
        "version": "1.0.0",
        "protocol_version": "2024-11-05",
        "capabilities": {
            "tools": True,
            "resources": False,
            "prompts": False
        }
    }


# =============================================================================
# MCP PROTOCOL ENDPOINTS
# =============================================================================

@app.get("/tools")
async def list_tools() -> list[dict]:
    """List all available MCP tools"""
    return [tool.model_dump() for tool in TOOLS]


@app.post("/tools/call")
async def call_tool(request: MCPToolCallRequest) -> MCPToolCallResponse:
    """Execute an MCP tool"""
    try:
        if request.name == "read_repo_structure":
            req = RepoStructureRequest(**request.arguments)
            result = await read_repo_structure(req)
            return MCPToolCallResponse(
                content=[{"type": "text", "text": json.dumps(result, indent=2)}]
            )
        
        elif request.name == "execute_shell_command":
            req = ShellCommandRequest(**request.arguments)
            result = await execute_shell_command(req)
            return MCPToolCallResponse(
                content=[{"type": "text", "text": json.dumps(result, indent=2)}],
                is_error=result.get("exit_code", 0) != 0
            )
        
        else:
            raise HTTPException(
                status_code=404,
                detail=f"Unknown tool: {request.name}"
            )
    
    except Exception as e:
        return MCPToolCallResponse(
            content=[{"type": "text", "text": f"Error: {str(e)}"}],
            is_error=True
        )


# =============================================================================
# DIRECT TOOL ENDPOINTS (for convenience)
# =============================================================================

@app.post("/api/repo-structure")
async def api_read_repo_structure(request: RepoStructureRequest):
    """Direct endpoint for reading repository structure"""
    return await read_repo_structure(request)


@app.post("/api/execute")
async def api_execute_command(request: ShellCommandRequest):
    """Direct endpoint for executing shell commands"""
    return await execute_shell_command(request)
