"""Git operations with security validation.

Provides async wrappers around GitPython with structured error handling.
"""

import os
from pathlib import Path
from typing import Dict, List, Optional, Any
import git
from git import Repo, GitCommandError

from .security import SecurityManager


class GitOperations:
    """Manages Git operations with security validation."""

    def __init__(self, security_manager: SecurityManager):
        """Initialize Git operations manager.

        Args:
            security_manager: Security manager for validation
        """
        self.security = security_manager

    async def clone_repository(
        self,
        url: str,
        path: Optional[str] = None,
        branch: Optional[str] = None
    ) -> Dict[str, Any]:
        """Clone a repository into workspace.

        Args:
            url: Repository URL (https or git protocol)
            path: Optional subdirectory name (uses repo name if not provided)
            branch: Optional branch to checkout after cloning

        Returns:
            Dict with status, repo_path, and branch
        """
        try:
            # Validate URL
            validated_url = self.security.validate_url(url)

            # Determine repo path
            if path is None:
                # Extract repo name from URL
                repo_name = validated_url.rstrip('/').split('/')[-1]
                if repo_name.endswith('.git'):
                    repo_name = repo_name[:-4]
                path = repo_name

            # Validate repository path
            repo_path = self.security.validate_repo_path(path)

            # Check if path already exists
            if repo_path.exists():
                return {
                    "success": False,
                    "error": f"Path already exists: {path}"
                }

            # Validate branch if provided
            if branch:
                branch = self.security.validate_branch_name(branch)

            # Clone repository
            clone_kwargs = {"branch": branch} if branch else {}
            repo = Repo.clone_from(validated_url, repo_path, **clone_kwargs)

            return {
                "success": True,
                "repo_path": path,
                "branch": repo.active_branch.name,
                "commit": repo.head.commit.hexsha[:8]
            }

        except ValueError as e:
            return {"success": False, "error": f"Validation error: {e}"}
        except GitCommandError as e:
            return {"success": False, "error": f"Git error: {e.stderr}"}
        except Exception as e:
            return {"success": False, "error": f"Unexpected error: {e}"}

    async def read_file(self, repo_path: str, file_path: str) -> Dict[str, Any]:
        """Read file from repository.

        Args:
            repo_path: Path to repository within workspace
            file_path: Path to file within repository

        Returns:
            Dict with content or error
        """
        try:
            # Validate paths
            validated_repo = self.security.validate_repo_path(repo_path)
            validated_file = self.security.validate_file_path(validated_repo, file_path)

            # Check file exists
            if not validated_file.exists():
                return {
                    "success": False,
                    "error": f"File not found: {file_path}"
                }

            if not validated_file.is_file():
                return {
                    "success": False,
                    "error": f"Not a file: {file_path}"
                }

            # Read file content
            content = validated_file.read_text(encoding='utf-8')

            return {
                "success": True,
                "content": content,
                "path": file_path
            }

        except ValueError as e:
            return {"success": False, "error": f"Validation error: {e}"}
        except UnicodeDecodeError:
            return {"success": False, "error": "Binary file not supported"}
        except Exception as e:
            return {"success": False, "error": f"Error reading file: {e}"}

    async def write_file(
        self,
        repo_path: str,
        file_path: str,
        content: str
    ) -> Dict[str, Any]:
        """Write content to file in repository.

        Args:
            repo_path: Path to repository within workspace
            file_path: Path to file within repository
            content: File content to write

        Returns:
            Dict with success status
        """
        try:
            # Validate paths
            validated_repo = self.security.validate_repo_path(repo_path)
            validated_file = self.security.validate_file_path(validated_repo, file_path)

            # Create parent directories if needed
            validated_file.parent.mkdir(parents=True, exist_ok=True)

            # Write file content
            validated_file.write_text(content, encoding='utf-8')

            return {
                "success": True,
                "path": file_path,
                "bytes": len(content.encode('utf-8'))
            }

        except ValueError as e:
            return {"success": False, "error": f"Validation error: {e}"}
        except Exception as e:
            return {"success": False, "error": f"Error writing file: {e}"}

    async def list_files(
        self,
        repo_path: str,
        path: Optional[str] = None,
        recursive: bool = False
    ) -> Dict[str, Any]:
        """List files in repository directory.

        Args:
            repo_path: Path to repository within workspace
            path: Optional subdirectory within repository
            recursive: Whether to list recursively

        Returns:
            Dict with file listing
        """
        try:
            # Validate repository path
            validated_repo = self.security.validate_repo_path(repo_path)

            # Validate subdirectory if provided
            if path:
                list_path = self.security.validate_file_path(validated_repo, path)
            else:
                list_path = validated_repo

            # Check path exists
            if not list_path.exists():
                return {
                    "success": False,
                    "error": f"Path not found: {path or '.'}"
                }

            # List files
            files = []
            if recursive:
                for item in list_path.rglob('*'):
                    rel_path = item.relative_to(validated_repo)
                    files.append({
                        "path": str(rel_path),
                        "type": "directory" if item.is_dir() else "file"
                    })
            else:
                for item in list_path.iterdir():
                    rel_path = item.relative_to(validated_repo)
                    files.append({
                        "path": str(rel_path),
                        "type": "directory" if item.is_dir() else "file"
                    })

            # Sort by path
            files.sort(key=lambda x: x["path"])

            return {
                "success": True,
                "files": files,
                "count": len(files)
            }

        except ValueError as e:
            return {"success": False, "error": f"Validation error: {e}"}
        except Exception as e:
            return {"success": False, "error": f"Error listing files: {e}"}

    async def git_status(self, repo_path: str) -> Dict[str, Any]:
        """Get working tree status.

        Args:
            repo_path: Path to repository within workspace

        Returns:
            Dict with status information
        """
        try:
            # Validate path
            validated_repo = self.security.validate_repo_path(repo_path)

            # Open repository
            repo = Repo(validated_repo)

            # Get status
            status = {
                "success": True,
                "branch": repo.active_branch.name,
                "commit": repo.head.commit.hexsha[:8],
                "modified": [item.a_path for item in repo.index.diff(None)],
                "staged": [item.a_path for item in repo.index.diff('HEAD')],
                "untracked": repo.untracked_files
            }

            return status

        except ValueError as e:
            return {"success": False, "error": f"Validation error: {e}"}
        except git.exc.InvalidGitRepositoryError:
            return {"success": False, "error": "Not a git repository"}
        except Exception as e:
            return {"success": False, "error": f"Error getting status: {e}"}

    async def git_diff_unstaged(
        self,
        repo_path: str,
        context_lines: int = 3
    ) -> Dict[str, Any]:
        """Get unstaged changes.

        Args:
            repo_path: Path to repository within workspace
            context_lines: Number of context lines in diff

        Returns:
            Dict with diff content
        """
        try:
            # Validate path
            validated_repo = self.security.validate_repo_path(repo_path)

            # Open repository
            repo = Repo(validated_repo)

            # Get diff
            diff = repo.git.diff(unified=context_lines)

            return {
                "success": True,
                "diff": diff,
                "has_changes": bool(diff)
            }

        except ValueError as e:
            return {"success": False, "error": f"Validation error: {e}"}
        except git.exc.InvalidGitRepositoryError:
            return {"success": False, "error": "Not a git repository"}
        except Exception as e:
            return {"success": False, "error": f"Error getting diff: {e}"}

    async def git_diff_staged(
        self,
        repo_path: str,
        context_lines: int = 3
    ) -> Dict[str, Any]:
        """Get staged changes.

        Args:
            repo_path: Path to repository within workspace
            context_lines: Number of context lines in diff

        Returns:
            Dict with diff content
        """
        try:
            # Validate path
            validated_repo = self.security.validate_repo_path(repo_path)

            # Open repository
            repo = Repo(validated_repo)

            # Get diff
            diff = repo.git.diff('--cached', unified=context_lines)

            return {
                "success": True,
                "diff": diff,
                "has_changes": bool(diff)
            }

        except ValueError as e:
            return {"success": False, "error": f"Validation error: {e}"}
        except git.exc.InvalidGitRepositoryError:
            return {"success": False, "error": "Not a git repository"}
        except Exception as e:
            return {"success": False, "error": f"Error getting diff: {e}"}

    async def git_log(
        self,
        repo_path: str,
        max_count: int = 10,
        branch: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get commit history.

        Args:
            repo_path: Path to repository within workspace
            max_count: Maximum number of commits to return
            branch: Optional branch name (uses current if not provided)

        Returns:
            Dict with commit history
        """
        try:
            # Validate path
            validated_repo = self.security.validate_repo_path(repo_path)

            # Validate branch if provided
            if branch:
                branch = self.security.validate_branch_name(branch)

            # Open repository
            repo = Repo(validated_repo)

            # Get commits
            ref = branch if branch else repo.active_branch
            commits = []
            for commit in repo.iter_commits(ref, max_count=max_count):
                commits.append({
                    "hash": commit.hexsha[:8],
                    "author": str(commit.author),
                    "date": commit.committed_datetime.isoformat(),
                    "message": commit.message.strip()
                })

            return {
                "success": True,
                "commits": commits,
                "count": len(commits)
            }

        except ValueError as e:
            return {"success": False, "error": f"Validation error: {e}"}
        except git.exc.InvalidGitRepositoryError:
            return {"success": False, "error": "Not a git repository"}
        except Exception as e:
            return {"success": False, "error": f"Error getting log: {e}"}

    async def git_add(self, repo_path: str, files: List[str]) -> Dict[str, Any]:
        """Stage files for commit.

        Args:
            repo_path: Path to repository within workspace
            files: List of file paths to stage

        Returns:
            Dict with success status
        """
        try:
            # Validate paths
            validated_repo = self.security.validate_repo_path(repo_path)

            # Validate file paths
            for file_path in files:
                self.security.validate_file_path(validated_repo, file_path)

            # Open repository
            repo = Repo(validated_repo)

            # Stage files
            repo.index.add(files)

            return {
                "success": True,
                "staged": files,
                "count": len(files)
            }

        except ValueError as e:
            return {"success": False, "error": f"Validation error: {e}"}
        except git.exc.InvalidGitRepositoryError:
            return {"success": False, "error": "Not a git repository"}
        except Exception as e:
            return {"success": False, "error": f"Error staging files: {e}"}

    async def create_branch(
        self,
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
            Dict with success status
        """
        try:
            # Validate paths and names
            validated_repo = self.security.validate_repo_path(repo_path)
            validated_branch = self.security.validate_branch_name(branch_name)

            if base_branch:
                base_branch = self.security.validate_branch_name(base_branch)

            # Open repository
            repo = Repo(validated_repo)

            # Create branch
            if base_branch:
                base_ref = repo.heads[base_branch]
                new_branch = repo.create_head(validated_branch, base_ref)
            else:
                new_branch = repo.create_head(validated_branch)

            return {
                "success": True,
                "branch": validated_branch,
                "commit": new_branch.commit.hexsha[:8]
            }

        except ValueError as e:
            return {"success": False, "error": f"Validation error: {e}"}
        except git.exc.InvalidGitRepositoryError:
            return {"success": False, "error": "Not a git repository"}
        except Exception as e:
            return {"success": False, "error": f"Error creating branch: {e}"}

    async def commit_changes(
        self,
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
        try:
            # Validate paths and message
            validated_repo = self.security.validate_repo_path(repo_path)
            validated_message = self.security.validate_message(message)

            # Open repository
            repo = Repo(validated_repo)

            # Stage files
            if files:
                # Validate file paths
                for file_path in files:
                    self.security.validate_file_path(validated_repo, file_path)
                repo.index.add(files)
            else:
                # Stage all changes
                repo.git.add(A=True)

            # Commit
            commit = repo.index.commit(validated_message)

            return {
                "success": True,
                "commit": commit.hexsha[:8],
                "message": validated_message,
                "branch": repo.active_branch.name
            }

        except ValueError as e:
            return {"success": False, "error": f"Validation error: {e}"}
        except git.exc.InvalidGitRepositoryError:
            return {"success": False, "error": "Not a git repository"}
        except Exception as e:
            return {"success": False, "error": f"Error committing: {e}"}

    async def git_checkout(self, repo_path: str, branch_name: str) -> Dict[str, Any]:
        """Switch to branch.

        Args:
            repo_path: Path to repository within workspace
            branch_name: Branch name to checkout

        Returns:
            Dict with success status
        """
        try:
            # Validate paths and names
            validated_repo = self.security.validate_repo_path(repo_path)
            validated_branch = self.security.validate_branch_name(branch_name)

            # Open repository
            repo = Repo(validated_repo)

            # Checkout branch
            repo.git.checkout(validated_branch)

            return {
                "success": True,
                "branch": validated_branch,
                "commit": repo.head.commit.hexsha[:8]
            }

        except ValueError as e:
            return {"success": False, "error": f"Validation error: {e}"}
        except git.exc.InvalidGitRepositoryError:
            return {"success": False, "error": "Not a git repository"}
        except GitCommandError as e:
            return {"success": False, "error": f"Git error: {e.stderr}"}
        except Exception as e:
            return {"success": False, "error": f"Error checking out: {e}"}

    async def push_changes(
        self,
        repo_path: str,
        remote: str = "origin",
        branch: Optional[str] = None
    ) -> Dict[str, Any]:
        """Push changes to remote.

        Args:
            repo_path: Path to repository within workspace
            remote: Remote name (default: origin)
            branch: Optional branch name (uses current if not provided)

        Returns:
            Dict with success status
        """
        try:
            # Validate paths and names
            validated_repo = self.security.validate_repo_path(repo_path)
            validated_remote = self.security.validate_git_ref(remote)

            if branch:
                branch = self.security.validate_branch_name(branch)

            # Open repository
            repo = Repo(validated_repo)

            # Get branch
            push_branch = branch if branch else repo.active_branch.name

            # Push
            repo.git.push(validated_remote, push_branch)

            return {
                "success": True,
                "remote": validated_remote,
                "branch": push_branch
            }

        except ValueError as e:
            return {"success": False, "error": f"Validation error: {e}"}
        except git.exc.InvalidGitRepositoryError:
            return {"success": False, "error": "Not a git repository"}
        except GitCommandError as e:
            return {"success": False, "error": f"Git error: {e.stderr}"}
        except Exception as e:
            return {"success": False, "error": f"Error pushing: {e}"}
