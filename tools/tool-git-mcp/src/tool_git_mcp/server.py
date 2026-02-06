"""FastMCP server for Git operations.

Exposes 13 Git tools through FastMCP/HTTP transport.
"""

import os
from typing import List, Optional, Any, Dict

from dotenv import load_dotenv

try:
    from mcp import FastMCP
except ImportError:
    from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from starlette.requests import Request
from starlette.responses import JSONResponse

from .security import SecurityManager
from .git_operations import GitOperations

load_dotenv()
load_dotenv(".env.local")

# Get configuration from environment
GIT_WORKSPACE_ROOT = os.getenv("GIT_WORKSPACE_ROOT", "/app/workspace")

# Initialize security and operations
security_manager = SecurityManager(GIT_WORKSPACE_ROOT)
git_ops = GitOperations(security_manager)

# Disable DNS rebinding protection to allow requests via Docker networking
mcp = FastMCP(
    "tool-git-mcp",
    transport_security=TransportSecuritySettings(
        enable_dns_rebinding_protection=False,
    ),
)


@mcp.custom_route("/health", methods=["GET"])
async def health_check(_request: Request) -> JSONResponse:
    """Health check endpoint with workspace info."""
    return JSONResponse({
        "status": "healthy",
        "workspace": GIT_WORKSPACE_ROOT,
        "git_available": True
    })


# File Operations

@mcp.tool()
async def clone_repository(
    url: str,
    path: Optional[str] = None,
    branch: Optional[str] = None
) -> Dict[str, Any]:
    """Clone a Git repository into workspace.

    Args:
        url: Repository URL (https or git protocol)
        path: Optional subdirectory name (uses repo name if not provided)
        branch: Optional branch to checkout after cloning

    Returns:
        Dict with status, repo_path, and branch information
    """
    return await git_ops.clone_repository(url, path, branch)


@mcp.tool()
async def read_file(repo_path: str, file_path: str) -> Dict[str, Any]:
    """Read file content from repository.

    Args:
        repo_path: Path to repository within workspace
        file_path: Path to file within repository

    Returns:
        Dict with file content or error
    """
    return await git_ops.read_file(repo_path, file_path)


@mcp.tool()
async def write_file(
    repo_path: str,
    file_path: str,
    content: str
) -> Dict[str, Any]:
    """Write content to file in repository.

    Args:
        repo_path: Path to repository within workspace
        file_path: Path to file within repository
        content: Content to write to file

    Returns:
        Dict with success status and file information
    """
    return await git_ops.write_file(repo_path, file_path, content)


@mcp.tool()
async def list_files(
    repo_path: str,
    path: Optional[str] = None,
    recursive: bool = False
) -> Dict[str, Any]:
    """List files in repository directory.

    Args:
        repo_path: Path to repository within workspace
        path: Optional subdirectory within repository
        recursive: Whether to list files recursively

    Returns:
        Dict with file listing
    """
    return await git_ops.list_files(repo_path, path, recursive)


# Git Status & Inspection

@mcp.tool()
async def git_status(repo_path: str) -> Dict[str, Any]:
    """Get working tree status.

    Args:
        repo_path: Path to repository within workspace

    Returns:
        Dict with branch, commit, modified, staged, and untracked files
    """
    return await git_ops.git_status(repo_path)


@mcp.tool()
async def git_diff_unstaged(
    repo_path: str,
    context_lines: int = 3
) -> Dict[str, Any]:
    """Get unstaged changes (working tree vs index).

    Args:
        repo_path: Path to repository within workspace
        context_lines: Number of context lines in diff (default: 3)

    Returns:
        Dict with diff content
    """
    return await git_ops.git_diff_unstaged(repo_path, context_lines)


@mcp.tool()
async def git_diff_staged(
    repo_path: str,
    context_lines: int = 3
) -> Dict[str, Any]:
    """Get staged changes (index vs HEAD).

    Args:
        repo_path: Path to repository within workspace
        context_lines: Number of context lines in diff (default: 3)

    Returns:
        Dict with diff content
    """
    return await git_ops.git_diff_staged(repo_path, context_lines)


@mcp.tool()
async def git_log(
    repo_path: str,
    max_count: int = 10,
    branch: Optional[str] = None
) -> Dict[str, Any]:
    """Get commit history.

    Args:
        repo_path: Path to repository within workspace
        max_count: Maximum number of commits to return (default: 10)
        branch: Optional branch name (uses current if not provided)

    Returns:
        Dict with commit history
    """
    return await git_ops.git_log(repo_path, max_count, branch)


# Git Write Operations

@mcp.tool()
async def git_add(repo_path: str, files: List[str]) -> Dict[str, Any]:
    """Stage files for commit.

    Args:
        repo_path: Path to repository within workspace
        files: List of file paths to stage

    Returns:
        Dict with staged files
    """
    return await git_ops.git_add(repo_path, files)


@mcp.tool()
async def create_branch(
    repo_path: str,
    branch_name: str,
    base_branch: Optional[str] = None
) -> Dict[str, Any]:
    """Create new branch.

    Args:
        repo_path: Path to repository within workspace
        branch_name: Name for new branch
        base_branch: Optional base branch (uses current if not provided)

    Returns:
        Dict with new branch information
    """
    return await git_ops.create_branch(repo_path, branch_name, base_branch)


@mcp.tool()
async def commit_changes(
    repo_path: str,
    message: str,
    files: Optional[List[str]] = None
) -> Dict[str, Any]:
    """Stage and commit changes.

    Args:
        repo_path: Path to repository within workspace
        message: Commit message
        files: Optional list of files to stage (stages all if None)

    Returns:
        Dict with commit information
    """
    return await git_ops.commit_changes(repo_path, message, files)


@mcp.tool()
async def git_checkout(repo_path: str, branch_name: str) -> Dict[str, Any]:
    """Switch to branch.

    Args:
        repo_path: Path to repository within workspace
        branch_name: Branch name to checkout

    Returns:
        Dict with current branch information
    """
    return await git_ops.git_checkout(repo_path, branch_name)


@mcp.tool()
async def push_changes(
    repo_path: str,
    remote: str = "origin",
    branch: Optional[str] = None
) -> Dict[str, Any]:
    """Push changes to remote repository.

    Args:
        repo_path: Path to repository within workspace
        remote: Remote name (default: "origin")
        branch: Optional branch name (uses current if not provided)

    Returns:
        Dict with push status
    """
    return await git_ops.push_changes(repo_path, remote, branch)


# Create FastAPI application
app = mcp.streamable_http_app()
