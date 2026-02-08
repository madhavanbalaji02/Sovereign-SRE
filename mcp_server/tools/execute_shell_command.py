"""
Execute Shell Command Tool
==========================
Executes shell commands in a sandboxed environment with safety checks.
"""

from pydantic import BaseModel, Field
from typing import Optional
import os
import asyncio
import shlex
import re
from pathlib import Path

# =============================================================================
# CONFIGURATION
# =============================================================================

WORKSPACE_PATH = os.environ.get("WORKSPACE_PATH", "/workspace")

# Commands that are blocked in safe mode
DANGEROUS_PATTERNS = [
    r"rm\s+-rf\s+/",           # rm -rf /
    r"rm\s+-rf\s+~",           # rm -rf ~
    r"rm\s+-rf\s+\*",          # rm -rf *
    r">\s*/dev/sd",            # write to disk devices
    r"mkfs\.",                 # format filesystem
    r"dd\s+if=",               # disk operations
    r":(){ :\|:& };:",         # fork bomb
    r"chmod\s+-R\s+777\s+/",   # chmod 777 /
    r"curl.*\|\s*(ba)?sh",     # curl | sh
    r"wget.*\|\s*(ba)?sh",     # wget | sh
]

# Commands allowed even in safe mode
SAFE_COMMANDS = {
    "ls", "cat", "head", "tail", "grep", "find", "wc", "echo",
    "pwd", "whoami", "date", "env", "printenv", "which", "type",
    "python", "python3", "pip", "pytest", "mypy", "ruff", "black",
    "node", "npm", "npx", "yarn", "pnpm",
    "git", "docker", "docker-compose",
    "curl", "wget", "jq", "yq",
}


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class ShellCommandRequest(BaseModel):
    """Request model for executing shell commands"""
    command: str = Field(..., description="The shell command to execute")
    working_dir: str = Field(default=".", description="Working directory relative to workspace")
    timeout: int = Field(default=30, ge=1, le=300, description="Timeout in seconds")
    safe_mode: bool = Field(default=True, description="Block potentially dangerous commands")


# =============================================================================
# SAFETY CHECKS
# =============================================================================

def is_dangerous_command(command: str) -> tuple[bool, Optional[str]]:
    """Check if a command matches any dangerous patterns"""
    for pattern in DANGEROUS_PATTERNS:
        if re.search(pattern, command, re.IGNORECASE):
            return True, f"Blocked by pattern: {pattern}"
    return False, None


def get_base_command(command: str) -> str:
    """Extract the base command from a command string"""
    try:
        parts = shlex.split(command)
        if parts:
            # Handle env vars, sudo, etc.
            for part in parts:
                if "=" not in part and not part.startswith("-"):
                    return os.path.basename(part)
    except ValueError:
        pass
    return ""


def is_command_allowed(command: str, safe_mode: bool) -> tuple[bool, Optional[str]]:
    """
    Check if a command is allowed to execute.
    
    Returns (allowed, reason) tuple.
    """
    # Always block dangerous patterns
    dangerous, reason = is_dangerous_command(command)
    if dangerous:
        return False, reason
    
    if not safe_mode:
        return True, None
    
    # In safe mode, check against allowlist
    base_cmd = get_base_command(command)
    if base_cmd and base_cmd not in SAFE_COMMANDS:
        return False, f"Command '{base_cmd}' not in safe mode allowlist"
    
    return True, None


# =============================================================================
# CORE IMPLEMENTATION
# =============================================================================

async def execute_shell_command(request: ShellCommandRequest) -> dict:
    """
    Execute a shell command and return the result.
    
    Returns a dictionary containing:
    - stdout: Command standard output
    - stderr: Command standard error
    - exit_code: Process exit code
    - success: Boolean indicating success
    - command: The executed command
    - working_dir: The working directory used
    """
    # Safety check
    allowed, reason = is_command_allowed(request.command, request.safe_mode)
    if not allowed:
        return {
            "stdout": "",
            "stderr": f"Command blocked: {reason}",
            "exit_code": -1,
            "success": False,
            "command": request.command,
            "working_dir": request.working_dir,
            "blocked": True,
            "block_reason": reason
        }
    
    # Resolve working directory
    work_dir = Path(WORKSPACE_PATH) / request.working_dir
    work_dir = work_dir.resolve()
    
    # Security: ensure we're within workspace
    workspace = Path(WORKSPACE_PATH).resolve()
    if not str(work_dir).startswith(str(workspace)):
        return {
            "stdout": "",
            "stderr": "Access denied: working directory outside workspace",
            "exit_code": -1,
            "success": False,
            "command": request.command,
            "working_dir": request.working_dir,
            "blocked": True,
            "block_reason": "Directory outside workspace"
        }
    
    if not work_dir.exists():
        return {
            "stdout": "",
            "stderr": f"Working directory not found: {request.working_dir}",
            "exit_code": -1,
            "success": False,
            "command": request.command,
            "working_dir": request.working_dir
        }
    
    try:
        # Execute the command
        process = await asyncio.create_subprocess_shell(
            request.command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(work_dir),
            env={
                **os.environ,
                "WORKSPACE_PATH": str(workspace),
            }
        )
        
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=request.timeout
            )
        except asyncio.TimeoutError:
            process.kill()
            await process.communicate()
            return {
                "stdout": "",
                "stderr": f"Command timed out after {request.timeout} seconds",
                "exit_code": -1,
                "success": False,
                "command": request.command,
                "working_dir": request.working_dir,
                "timed_out": True
            }
        
        return {
            "stdout": stdout.decode("utf-8", errors="replace"),
            "stderr": stderr.decode("utf-8", errors="replace"),
            "exit_code": process.returncode,
            "success": process.returncode == 0,
            "command": request.command,
            "working_dir": request.working_dir
        }
    
    except Exception as e:
        return {
            "stdout": "",
            "stderr": f"Execution error: {str(e)}",
            "exit_code": -1,
            "success": False,
            "command": request.command,
            "working_dir": request.working_dir,
            "error": str(e)
        }
