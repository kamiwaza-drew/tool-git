"""Tests for security validation."""

import pytest
from pathlib import Path
from tool_git_mcp.security import SecurityManager


@pytest.fixture
def security_manager(tmp_path):
    """Create security manager with temporary workspace."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    return SecurityManager(str(workspace))


class TestRepoPathValidation:
    """Tests for repository path validation."""

    def test_valid_simple_path(self, security_manager):
        """Valid simple repository path."""
        result = security_manager.validate_repo_path("my-repo")
        assert result.name == "my-repo"
        assert str(result).startswith(str(security_manager.workspace_root))

    def test_valid_nested_path(self, security_manager):
        """Valid nested repository path."""
        result = security_manager.validate_repo_path("org/my-repo")
        assert result.name == "my-repo"
        assert "org" in result.parts

    def test_reject_parent_traversal(self, security_manager):
        """Reject path traversal with .."""
        with pytest.raises(ValueError, match="Path traversal detected"):
            security_manager.validate_repo_path("../etc")

    def test_reject_nested_traversal(self, security_manager):
        """Reject nested path traversal."""
        with pytest.raises(ValueError, match="Path traversal detected"):
            security_manager.validate_repo_path("foo/../../etc")

    def test_reject_empty_path(self, security_manager):
        """Reject empty repository path."""
        with pytest.raises(ValueError, match="cannot be empty"):
            security_manager.validate_repo_path("")

    def test_reject_shell_metacharacters(self, security_manager):
        """Reject shell metacharacters in path."""
        dangerous_chars = [';', '&', '|', '`', '$', '(', ')', '{', '}', '[', ']', '<', '>']
        for char in dangerous_chars:
            with pytest.raises(ValueError, match="Invalid characters"):
                security_manager.validate_repo_path(f"repo{char}name")


class TestFilePathValidation:
    """Tests for file path validation."""

    def test_valid_file_path(self, security_manager):
        """Valid file path within repository."""
        repo_path = security_manager.validate_repo_path("my-repo")
        result = security_manager.validate_file_path(repo_path, "README.md")
        assert result.name == "README.md"

    def test_valid_nested_file(self, security_manager):
        """Valid nested file path."""
        repo_path = security_manager.validate_repo_path("my-repo")
        result = security_manager.validate_file_path(repo_path, "src/main.py")
        assert result.name == "main.py"
        assert "src" in result.parts

    def test_reject_file_traversal(self, security_manager):
        """Reject file path traversal out of repo."""
        repo_path = security_manager.validate_repo_path("my-repo")
        with pytest.raises(ValueError, match="Path traversal detected"):
            security_manager.validate_file_path(repo_path, "../../../etc/passwd")

    def test_reject_empty_file_path(self, security_manager):
        """Reject empty file path."""
        repo_path = security_manager.validate_repo_path("my-repo")
        with pytest.raises(ValueError, match="cannot be empty"):
            security_manager.validate_file_path(repo_path, "")

    def test_reject_shell_chars_in_file(self, security_manager):
        """Reject shell metacharacters in file path."""
        repo_path = security_manager.validate_repo_path("my-repo")
        with pytest.raises(ValueError, match="Invalid characters"):
            security_manager.validate_file_path(repo_path, "file;rm -rf /")


class TestGitRefValidation:
    """Tests for git reference validation."""

    def test_valid_branch_name(self, security_manager):
        """Valid branch name."""
        assert security_manager.validate_git_ref("main") == "main"
        assert security_manager.validate_git_ref("feature-123") == "feature-123"
        assert security_manager.validate_git_ref("dev/test") == "dev/test"

    def test_valid_commit_hash(self, security_manager):
        """Valid commit hash."""
        hash_val = "a1b2c3d4e5f6"
        assert security_manager.validate_git_ref(hash_val) == hash_val

    def test_reject_shell_injection(self, security_manager):
        """Reject shell command injection attempts."""
        with pytest.raises(ValueError, match="Shell metacharacters"):
            security_manager.validate_git_ref("main; rm -rf /")

    def test_reject_command_substitution(self, security_manager):
        """Reject command substitution."""
        with pytest.raises(ValueError, match="Invalid git reference"):
            security_manager.validate_git_ref("$(rm -rf /)")

    def test_reject_pipe(self, security_manager):
        """Reject pipe character."""
        with pytest.raises(ValueError, match="Shell metacharacters"):
            security_manager.validate_git_ref("main|cat")

    def test_reject_empty_ref(self, security_manager):
        """Reject empty reference."""
        with pytest.raises(ValueError, match="cannot be empty"):
            security_manager.validate_git_ref("")


class TestBranchNameValidation:
    """Tests for branch name validation."""

    def test_valid_branch_names(self, security_manager):
        """Valid branch names."""
        valid_names = ["main", "develop", "feature/xyz", "bugfix-123", "release_1.0"]
        for name in valid_names:
            assert security_manager.validate_branch_name(name) == name

    def test_reject_hyphen_start(self, security_manager):
        """Reject branch starting with hyphen."""
        with pytest.raises(ValueError, match="cannot start with hyphen"):
            security_manager.validate_branch_name("-invalid")

    def test_reject_lock_suffix(self, security_manager):
        """Reject branch ending with .lock."""
        with pytest.raises(ValueError, match="cannot end with .lock"):
            security_manager.validate_branch_name("branch.lock")

    def test_reject_consecutive_slashes(self, security_manager):
        """Reject consecutive slashes."""
        with pytest.raises(ValueError, match="consecutive slashes"):
            security_manager.validate_branch_name("feature//bug")

    def test_reject_leading_slash(self, security_manager):
        """Reject leading slash."""
        with pytest.raises(ValueError, match="cannot start or end with slash"):
            security_manager.validate_branch_name("/feature")

    def test_reject_trailing_slash(self, security_manager):
        """Reject trailing slash."""
        with pytest.raises(ValueError, match="cannot start or end with slash"):
            security_manager.validate_branch_name("feature/")


class TestUrlValidation:
    """Tests for URL validation."""

    def test_valid_https_url(self, security_manager):
        """Valid HTTPS URL."""
        url = "https://github.com/user/repo.git"
        assert security_manager.validate_url(url) == url

    def test_valid_git_protocol(self, security_manager):
        """Valid git protocol URL."""
        url = "git://github.com/user/repo.git"
        assert security_manager.validate_url(url) == url

    def test_reject_http_protocol(self, security_manager):
        """Reject HTTP (insecure) protocol."""
        with pytest.raises(ValueError, match="Protocol 'http' not allowed"):
            security_manager.validate_url("http://github.com/user/repo.git")

    def test_reject_file_protocol(self, security_manager):
        """Reject file protocol."""
        with pytest.raises(ValueError, match="Protocol 'file' not allowed"):
            security_manager.validate_url("file:///etc/passwd")

    def test_reject_ssh_protocol(self, security_manager):
        """Reject SSH protocol (not supported in MVP)."""
        with pytest.raises(ValueError, match="not allowed"):
            security_manager.validate_url("ssh://git@github.com/user/repo.git")

    def test_reject_empty_url(self, security_manager):
        """Reject empty URL."""
        with pytest.raises(ValueError, match="cannot be empty"):
            security_manager.validate_url("")

    def test_reject_https_without_host(self, security_manager):
        """Reject HTTPS URL without hostname."""
        with pytest.raises(ValueError, match="must include hostname"):
            security_manager.validate_url("https:///path")


class TestMessageValidation:
    """Tests for commit message validation."""

    def test_valid_message(self, security_manager):
        """Valid commit message."""
        msg = "Fix bug in authentication"
        assert security_manager.validate_message(msg) == msg

    def test_valid_multiline_message(self, security_manager):
        """Valid multiline commit message."""
        msg = "Fix authentication bug\n\nAdded validation for tokens"
        assert security_manager.validate_message(msg) == msg

    def test_reject_empty_message(self, security_manager):
        """Reject empty commit message."""
        with pytest.raises(ValueError, match="cannot be empty"):
            security_manager.validate_message("")

    def test_reject_whitespace_only(self, security_manager):
        """Reject whitespace-only message."""
        with pytest.raises(ValueError, match="cannot be empty"):
            security_manager.validate_message("   \n  ")
