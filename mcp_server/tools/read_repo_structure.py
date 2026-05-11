"""
Read Repository Structure Tool
==============================
Recursively scans a repository and returns its structure as a tree.
"""

from pydantic import BaseModel, Field
from typing import Optional
import os
from pathlib import Path

# =============================================================================
# CONFIGURATION
# =============================================================================

WORKSPACE_PATH = os.environ.get("WORKSPACE_PATH", "/workspace")

# Directories to always ignore
IGNORE_DIRS = {
    ".git", "__pycache__", "node_modules", ".next", "venv", ".venv",
    "env", ".env", "dist", "build", ".pytest_cache", ".mypy_cache",
    ".ruff_cache", "eggs", "*.egg-info", ".tox", "htmlcov", ".coverage",
    "chroma_data"
}

# Files to always ignore
IGNORE_FILES = {
    ".DS_Store", "Thumbs.db", "*.pyc", "*.pyo", "*.so", "*.dylib"
}


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class RepoStructureRequest(BaseModel):
    """Request model for reading repo structure"""
    path: str = Field(default=".", description="Path relative to workspace root")
    max_depth: int = Field(default=5, ge=1, le=20, description="Maximum recursion depth")
    include_hidden: bool = Field(default=False, description="Include hidden files/dirs")
    file_extensions: Optional[list[str]] = Field(
        default=None,
        description="Filter by extensions (e.g., ['.py', '.js'])"
    )


class FileNode(BaseModel):
    """Represents a file or directory in the tree"""
    name: str
    path: str
    type: str  # "file" or "directory"
    size: Optional[int] = None
    extension: Optional[str] = None
    children: Optional[list["FileNode"]] = None


# =============================================================================
# CORE IMPLEMENTATION
# =============================================================================

def should_ignore(name: str, is_dir: bool) -> bool:
    """Check if a file or directory should be ignored"""
    if is_dir:
        return name in IGNORE_DIRS
    
    for pattern in IGNORE_FILES:
        if pattern.startswith("*"):
            if name.endswith(pattern[1:]):
                return True
        elif name == pattern:
            return True
    
    return False


def scan_directory(
    base_path: Path,
    current_path: Path,
    max_depth: int,
    current_depth: int,
    include_hidden: bool,
    file_extensions: Optional[list[str]]
) -> list[FileNode]:
    """Recursively scan a directory and build tree structure"""
    nodes = []
    
    if current_depth > max_depth:
        return nodes
    
    try:
        entries = sorted(current_path.iterdir(), key=lambda e: (not e.is_dir(), e.name.lower()))
    except PermissionError:
        return nodes
    
    for entry in entries:
        # Skip hidden files/dirs if not requested
        if not include_hidden and entry.name.startswith("."):
            continue
        
        # Skip ignored paths
        if should_ignore(entry.name, entry.is_dir()):
            continue
        
        relative_path = str(entry.relative_to(base_path))
        
        if entry.is_dir():
            children = scan_directory(
                base_path, entry, max_depth, current_depth + 1,
                include_hidden, file_extensions
            )
            # Only include non-empty directories or if at max depth
            if children or current_depth == max_depth:
                nodes.append(FileNode(
                    name=entry.name,
                    path=relative_path,
                    type="directory",
                    children=children if children else None
                ))
        else:
            # Apply extension filter
            ext = entry.suffix.lower() if entry.suffix else None
            if file_extensions and ext not in file_extensions:
                continue
            
            try:
                size = entry.stat().st_size
            except (OSError, PermissionError):
                size = None
            
            nodes.append(FileNode(
                name=entry.name,
                path=relative_path,
                type="file",
                size=size,
                extension=ext
            ))
    
    return nodes


async def read_repo_structure(request: RepoStructureRequest) -> dict:
    """
    Main entry point for reading repository structure.
    
    Returns a dictionary containing:
    - tree: The file/directory tree structure
    - stats: Summary statistics (file count, dir count, extensions)
    """
    # Resolve the target path
    target_path = Path(WORKSPACE_PATH) / request.path
    target_path = target_path.resolve()
    
    # Security: ensure we're still within workspace
    workspace = Path(WORKSPACE_PATH).resolve()
    if not str(target_path).startswith(str(workspace)):
        return {
            "error": "Access denied: path outside workspace",
            "tree": [],
            "stats": {}
        }
    
    if not target_path.exists():
        return {
            "error": f"Path not found: {request.path}",
            "tree": [],
            "stats": {}
        }
    
    if not target_path.is_dir():
        return {
            "error": f"Not a directory: {request.path}",
            "tree": [],
            "stats": {}
        }
    
    # Scan the directory
    tree = scan_directory(
        base_path=workspace,
        current_path=target_path,
        max_depth=request.max_depth,
        current_depth=0,
        include_hidden=request.include_hidden,
        file_extensions=request.file_extensions
    )
    
    # Calculate stats
    def count_nodes(nodes: list[FileNode]) -> tuple[int, int, dict]:
        files, dirs = 0, 0
        extensions: dict[str, int] = {}
        
        for node in nodes:
            if node.type == "file":
                files += 1
                if node.extension:
                    extensions[node.extension] = extensions.get(node.extension, 0) + 1
            else:
                dirs += 1
                if node.children:
                    f, d, e = count_nodes(node.children)
                    files += f
                    dirs += d
                    for ext, count in e.items():
                        extensions[ext] = extensions.get(ext, 0) + count
        
        return files, dirs, extensions
    
    file_count, dir_count, ext_counts = count_nodes(tree)
    
    return {
        "tree": [node.model_dump() for node in tree],
        "stats": {
            "total_files": file_count,
            "total_directories": dir_count,
            "extensions": ext_counts,
            "scanned_path": str(target_path.relative_to(workspace))
        }
    }
