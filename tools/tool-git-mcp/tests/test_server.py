"""Tests for FastMCP server."""

import pytest
from starlette.testclient import TestClient
from tool_git_mcp.server import app, mcp


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


class TestHealthCheck:
    """Tests for health check endpoint."""

    def test_health_endpoint(self, client):
        """Health endpoint returns 200."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "workspace" in data
        assert "git_available" in data


class TestToolRegistration:
    """Tests for MCP tool registration."""

    def test_all_tools_registered(self):
        """All 13 tools are registered."""
        # Get tool names from MCP server
        tool_names = [tool.name for tool in mcp.list_tools()]

        # Expected tool names
        expected_tools = [
            # File operations
            "clone_repository",
            "read_file",
            "write_file",
            "list_files",
            # Status & inspection
            "git_status",
            "git_diff_unstaged",
            "git_diff_staged",
            "git_log",
            # Write operations
            "git_add",
            "create_branch",
            "commit_changes",
            "git_checkout",
            "push_changes",
        ]

        for tool_name in expected_tools:
            assert tool_name in tool_names, f"Tool {tool_name} not registered"

    def test_tool_count(self):
        """Exactly 13 tools registered."""
        tools = mcp.list_tools()
        assert len(tools) == 13

    def test_tool_descriptions(self):
        """All tools have descriptions."""
        tools = mcp.list_tools()
        for tool in tools:
            assert tool.description, f"Tool {tool.name} missing description"
            assert len(tool.description) > 10, f"Tool {tool.name} has short description"
