"""Security validation for Git MCP tool operations.

Provides path validation, command injection prevention, and workspace isolation.
"""

import os
import re
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse


class SecurityManager:
    """Manages security validations for Git operations."""

    # Regex for valid git references (branches, tags, commit hashes)
    GIT_REF_PATTERN = re.compile(r'^[a-zA-Z0-9._/-]+$')

    # Shell metacharacters to reject in user input
    SHELL_METACHARACTERS = set(';&|`$(){}[]<>')

    # Allowed URL protocols
    ALLOWED_PROTOCOLS = {'https', 'git'}

    def __init__(self, workspace_root: str = "/app/workspace"):
        """Initialize security manager.

        Args:
            workspace_root: Root directory for all Git operations
        """
        self.workspace_root = Path(workspace_root).resolve()

    def validate_repo_path(self, repo_path: str) -> Path:
        """Validate repository path is within workspace.

        Args:
            repo_path: Relative path to repository within workspace

        Returns:
            Resolved absolute path to repository

        Raises:
            ValueError: If path is invalid or outside workspace
        """
        if not repo_path or not repo_path.strip():
            raise ValueError("Repository path cannot be empty")

        # Detect obvious traversal attempts
        if '..' in repo_path:
            raise ValueError("Path traversal detected: '..' not allowed")

        # Check for shell metacharacters
        if any(char in repo_path for char in self.SHELL_METACHARACTERS):
            raise ValueError("Invalid characters in repository path")

        # Resolve path and ensure it's within workspace
        try:
            full_path = (self.workspace_root / repo_path).resolve()
            full_path.relative_to(self.workspace_root)
        except (ValueError, RuntimeError) as e:
            raise ValueError(f"Repository path outside workspace: {e}")

        return full_path

    def validate_file_path(self, repo_path: Path, file_path: str) -> Path:
        """Validate file path is within repository.

        Args:
            repo_path: Validated repository path (from validate_repo_path)
            file_path: Relative path to file within repository

        Returns:
            Resolved absolute path to file

        Raises:
            ValueError: If path is invalid or outside repository
        """
        if not file_path or not file_path.strip():
            raise ValueError("File path cannot be empty")

        # Detect traversal attempts
        if '..' in file_path:
            raise ValueError("Path traversal detected: '..' not allowed")

        # Check for shell metacharacters
        if any(char in file_path for char in self.SHELL_METACHARACTERS):
            raise ValueError("Invalid characters in file path")

        # Resolve path and ensure it's within repository
        try:
            full_path = (repo_path / file_path).resolve()
            full_path.relative_to(repo_path)
        except (ValueError, RuntimeError) as e:
            raise ValueError(f"File path outside repository: {e}")

        return full_path

    def validate_git_ref(self, ref: str) -> str:
        """Validate git reference (branch, tag, commit hash).

        Args:
            ref: Git reference to validate

        Returns:
            Validated reference string

        Raises:
            ValueError: If reference contains invalid characters
        """
        if not ref or not ref.strip():
            raise ValueError("Git reference cannot be empty")

        if not self.GIT_REF_PATTERN.match(ref):
            raise ValueError(
                "Invalid git reference: must contain only alphanumeric "
                "characters, dots, underscores, slashes, and hyphens"
            )

        # Additional checks for dangerous patterns
        if any(char in ref for char in self.SHELL_METACHARACTERS):
            raise ValueError("Shell metacharacters not allowed in git reference")

        return ref

    def validate_branch_name(self, branch: str) -> str:
        """Validate git branch name.

        Args:
            branch: Branch name to validate

        Returns:
            Validated branch name

        Raises:
            ValueError: If branch name is invalid
        """
        if not branch or not branch.strip():
            raise ValueError("Branch name cannot be empty")

        # Use git ref validation
        validated = self.validate_git_ref(branch)

        # Additional branch-specific rules
        if branch.startswith('-'):
            raise ValueError("Branch name cannot start with hyphen")

        if branch.endswith('.lock'):
            raise ValueError("Branch name cannot end with .lock")

        if '//' in branch:
            raise ValueError("Branch name cannot contain consecutive slashes")

        if branch.startswith('/') or branch.endswith('/'):
            raise ValueError("Branch name cannot start or end with slash")

        return validated

    def validate_url(self, url: str) -> str:
        """Validate git repository URL.

        Args:
            url: Repository URL to validate

        Returns:
            Validated URL string

        Raises:
            ValueError: If URL is invalid or uses disallowed protocol
        """
        if not url or not url.strip():
            raise ValueError("URL cannot be empty")

        # Parse URL
        try:
            parsed = urlparse(url)
        except Exception as e:
            raise ValueError(f"Invalid URL format: {e}")

        # Check protocol
        if parsed.scheme not in self.ALLOWED_PROTOCOLS:
            raise ValueError(
                f"Protocol '{parsed.scheme}' not allowed. "
                f"Allowed protocols: {', '.join(sorted(self.ALLOWED_PROTOCOLS))}"
            )

        # Ensure hostname exists for https URLs
        if parsed.scheme == 'https' and not parsed.netloc:
            raise ValueError("HTTPS URL must include hostname")

        return url

    def validate_message(self, message: str) -> str:
        """Validate commit message.

        Args:
            message: Commit message to validate

        Returns:
            Validated message string

        Raises:
            ValueError: If message is empty
        """
        if not message or not message.strip():
            raise ValueError("Commit message cannot be empty")

        return message
