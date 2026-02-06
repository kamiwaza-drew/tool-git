"""Tests for Git operations."""

import pytest
from pathlib import Path
from tool_git_mcp.security import SecurityManager
from tool_git_mcp.git_operations import GitOperations
import git


@pytest.fixture
def workspace(tmp_path):
    """Create temporary workspace."""
    workspace_dir = tmp_path / "workspace"
    workspace_dir.mkdir()
    return workspace_dir


@pytest.fixture
def git_ops(workspace):
    """Create GitOperations instance."""
    security = SecurityManager(str(workspace))
    return GitOperations(security)


@pytest.fixture
def test_repo(workspace):
    """Create test Git repository."""
    repo_path = workspace / "test-repo"
    repo_path.mkdir()
    repo = git.Repo.init(repo_path)

    # Configure git
    with repo.config_writer() as config:
        config.set_value("user", "name", "Test User")
        config.set_value("user", "email", "test@example.com")

    # Create initial commit
    readme = repo_path / "README.md"
    readme.write_text("# Test Repository")
    repo.index.add(["README.md"])
    repo.index.commit("Initial commit")

    return "test-repo"


class TestFileOperations:
    """Tests for file operations."""

    @pytest.mark.asyncio
    async def test_read_file(self, git_ops, test_repo):
        """Read existing file."""
        result = await git_ops.read_file(test_repo, "README.md")
        assert result["success"] is True
        assert "Test Repository" in result["content"]

    @pytest.mark.asyncio
    async def test_read_nonexistent_file(self, git_ops, test_repo):
        """Read nonexistent file."""
        result = await git_ops.read_file(test_repo, "missing.txt")
        assert result["success"] is False
        assert "not found" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_write_file(self, git_ops, test_repo):
        """Write new file."""
        content = "Hello, World!"
        result = await git_ops.write_file(test_repo, "hello.txt", content)
        assert result["success"] is True
        assert result["path"] == "hello.txt"

        # Verify file was written
        read_result = await git_ops.read_file(test_repo, "hello.txt")
        assert read_result["content"] == content

    @pytest.mark.asyncio
    async def test_write_nested_file(self, git_ops, test_repo):
        """Write file in nested directory."""
        result = await git_ops.write_file(test_repo, "src/main.py", "print('Hello')")
        assert result["success"] is True

        # Verify file was written
        read_result = await git_ops.read_file(test_repo, "src/main.py")
        assert "Hello" in read_result["content"]

    @pytest.mark.asyncio
    async def test_list_files(self, git_ops, test_repo, workspace):
        """List files in repository."""
        # Create some files
        repo_path = workspace / test_repo
        (repo_path / "file1.txt").write_text("content1")
        (repo_path / "file2.txt").write_text("content2")
        (repo_path / "subdir").mkdir()
        (repo_path / "subdir" / "file3.txt").write_text("content3")

        result = await git_ops.list_files(test_repo)
        assert result["success"] is True
        assert result["count"] >= 3

        # Check file names in results
        paths = [f["path"] for f in result["files"]]
        assert "file1.txt" in paths
        assert "file2.txt" in paths

    @pytest.mark.asyncio
    async def test_list_files_recursive(self, git_ops, test_repo, workspace):
        """List files recursively."""
        # Create nested structure
        repo_path = workspace / test_repo
        (repo_path / "dir1").mkdir()
        (repo_path / "dir1" / "file.txt").write_text("content")

        result = await git_ops.list_files(test_repo, recursive=True)
        assert result["success"] is True

        paths = [f["path"] for f in result["files"]]
        assert any("dir1" in p for p in paths)


class TestGitStatus:
    """Tests for git status operations."""

    @pytest.mark.asyncio
    async def test_git_status_clean(self, git_ops, test_repo):
        """Status of clean repository."""
        result = await git_ops.git_status(test_repo)
        assert result["success"] is True
        assert result["branch"] in ["main", "master"]
        assert len(result["modified"]) == 0
        assert len(result["untracked"]) == 0

    @pytest.mark.asyncio
    async def test_git_status_with_changes(self, git_ops, test_repo, workspace):
        """Status with unstaged changes."""
        # Modify file
        repo_path = workspace / test_repo
        readme = repo_path / "README.md"
        readme.write_text("# Modified")

        result = await git_ops.git_status(test_repo)
        assert result["success"] is True
        assert "README.md" in result["modified"]

    @pytest.mark.asyncio
    async def test_git_status_untracked(self, git_ops, test_repo, workspace):
        """Status with untracked files."""
        # Create untracked file
        repo_path = workspace / test_repo
        new_file = repo_path / "new.txt"
        new_file.write_text("New file")

        result = await git_ops.git_status(test_repo)
        assert result["success"] is True
        assert "new.txt" in result["untracked"]

    @pytest.mark.asyncio
    async def test_git_status_invalid_repo(self, git_ops, workspace):
        """Status of non-git directory."""
        non_repo = workspace / "not-a-repo"
        non_repo.mkdir()

        result = await git_ops.git_status("not-a-repo")
        assert result["success"] is False
        assert "not a git repository" in result["error"].lower()


class TestGitDiff:
    """Tests for git diff operations."""

    @pytest.mark.asyncio
    async def test_diff_unstaged_no_changes(self, git_ops, test_repo):
        """Diff with no unstaged changes."""
        result = await git_ops.git_diff_unstaged(test_repo)
        assert result["success"] is True
        assert result["has_changes"] is False

    @pytest.mark.asyncio
    async def test_diff_unstaged_with_changes(self, git_ops, test_repo, workspace):
        """Diff with unstaged changes."""
        # Modify file
        repo_path = workspace / test_repo
        readme = repo_path / "README.md"
        readme.write_text("# Modified Content")

        result = await git_ops.git_diff_unstaged(test_repo)
        assert result["success"] is True
        assert result["has_changes"] is True
        assert "Modified Content" in result["diff"]

    @pytest.mark.asyncio
    async def test_diff_staged_no_changes(self, git_ops, test_repo):
        """Diff with no staged changes."""
        result = await git_ops.git_diff_staged(test_repo)
        assert result["success"] is True
        assert result["has_changes"] is False


class TestGitLog:
    """Tests for git log operations."""

    @pytest.mark.asyncio
    async def test_git_log(self, git_ops, test_repo):
        """Get commit history."""
        result = await git_ops.git_log(test_repo)
        assert result["success"] is True
        assert result["count"] >= 1
        assert len(result["commits"]) >= 1

        commit = result["commits"][0]
        assert "hash" in commit
        assert "author" in commit
        assert "message" in commit
        assert "Initial commit" in commit["message"]

    @pytest.mark.asyncio
    async def test_git_log_max_count(self, git_ops, test_repo, workspace):
        """Get limited commit history."""
        # Create multiple commits
        repo_path = workspace / test_repo
        repo = git.Repo(repo_path)

        for i in range(5):
            file_path = repo_path / f"file{i}.txt"
            file_path.write_text(f"content {i}")
            repo.index.add([f"file{i}.txt"])
            repo.index.commit(f"Commit {i}")

        result = await git_ops.git_log(test_repo, max_count=3)
        assert result["success"] is True
        assert result["count"] == 3


class TestGitAdd:
    """Tests for git add operations."""

    @pytest.mark.asyncio
    async def test_git_add_single_file(self, git_ops, test_repo, workspace):
        """Stage single file."""
        # Create file
        repo_path = workspace / test_repo
        new_file = repo_path / "new.txt"
        new_file.write_text("New content")

        result = await git_ops.git_add(test_repo, ["new.txt"])
        assert result["success"] is True
        assert "new.txt" in result["staged"]

    @pytest.mark.asyncio
    async def test_git_add_multiple_files(self, git_ops, test_repo, workspace):
        """Stage multiple files."""
        # Create files
        repo_path = workspace / test_repo
        (repo_path / "file1.txt").write_text("content1")
        (repo_path / "file2.txt").write_text("content2")

        result = await git_ops.git_add(test_repo, ["file1.txt", "file2.txt"])
        assert result["success"] is True
        assert result["count"] == 2


class TestBranchOperations:
    """Tests for branch operations."""

    @pytest.mark.asyncio
    async def test_create_branch(self, git_ops, test_repo):
        """Create new branch."""
        result = await git_ops.create_branch(test_repo, "feature-branch")
        assert result["success"] is True
        assert result["branch"] == "feature-branch"

    @pytest.mark.asyncio
    async def test_git_checkout(self, git_ops, test_repo):
        """Checkout branch."""
        # Create branch first
        await git_ops.create_branch(test_repo, "test-branch")

        result = await git_ops.git_checkout(test_repo, "test-branch")
        assert result["success"] is True
        assert result["branch"] == "test-branch"

        # Verify we're on the branch
        status = await git_ops.git_status(test_repo)
        assert status["branch"] == "test-branch"


class TestCommitOperations:
    """Tests for commit operations."""

    @pytest.mark.asyncio
    async def test_commit_changes_specific_files(self, git_ops, test_repo, workspace):
        """Commit specific files."""
        # Create files
        repo_path = workspace / test_repo
        (repo_path / "file1.txt").write_text("content1")
        (repo_path / "file2.txt").write_text("content2")

        result = await git_ops.commit_changes(
            test_repo,
            "Add files",
            files=["file1.txt", "file2.txt"]
        )
        assert result["success"] is True
        assert "Add files" in result["message"]
        assert len(result["commit"]) == 8

    @pytest.mark.asyncio
    async def test_commit_changes_all_files(self, git_ops, test_repo, workspace):
        """Commit all changes."""
        # Create file
        repo_path = workspace / test_repo
        (repo_path / "new.txt").write_text("content")

        result = await git_ops.commit_changes(test_repo, "Add all files")
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_commit_empty_message(self, git_ops, test_repo):
        """Reject empty commit message."""
        result = await git_ops.commit_changes(test_repo, "")
        assert result["success"] is False
        assert "validation error" in result["error"].lower()


class TestSecurityValidation:
    """Tests for security validation in operations."""

    @pytest.mark.asyncio
    async def test_reject_path_traversal_in_read(self, git_ops, test_repo):
        """Reject path traversal in read_file."""
        result = await git_ops.read_file(test_repo, "../../../etc/passwd")
        assert result["success"] is False
        assert "validation error" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_reject_invalid_branch_name(self, git_ops, test_repo):
        """Reject invalid branch name."""
        result = await git_ops.create_branch(test_repo, "branch; rm -rf /")
        assert result["success"] is False
        assert "validation error" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_reject_shell_injection_in_checkout(self, git_ops, test_repo):
        """Reject shell injection in checkout."""
        result = await git_ops.git_checkout(test_repo, "main && rm -rf /")
        assert result["success"] is False
        assert "validation error" in result["error"].lower()
