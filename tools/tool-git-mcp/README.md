# Git MCP Assistant Tool

A production-ready Git MCP tool for Kamiwaza that exposes Git operations through FastMCP/HTTP transport. Enables AI models to perform comprehensive Git repository management including cloning, file operations, branching, committing, and pushing changes.

## Features

### File Operations (4 tools)
- **clone_repository** - Clone repositories into isolated workspace
- **read_file** - Read file contents from repository
- **write_file** - Write content to files with automatic directory creation
- **list_files** - List files and directories (with recursive option)

### Git Status & Inspection (4 tools)
- **git_status** - Get working tree status (branch, modified, staged, untracked)
- **git_diff_unstaged** - View unstaged changes with context
- **git_diff_staged** - View staged changes with context
- **git_log** - Get commit history with configurable depth

### Git Write Operations (5 tools)
- **git_add** - Stage specific files for commit
- **create_branch** - Create new branches from base branch
- **commit_changes** - Stage and commit changes with message
- **git_checkout** - Switch between branches
- **push_changes** - Push commits to remote repositories

## Security Model

### Workspace Isolation
- All operations scoped to `/app/workspace` container directory
- Path traversal prevention with multiple validation layers
- No access to files outside workspace boundaries

### Input Validation
- **URLs**: Only `https://` and `git://` protocols allowed
- **Git References**: Alphanumeric, dots, underscores, slashes, hyphens only
- **Branch Names**: Additional validation (no leading hyphen, no `.lock` suffix)
- **File Paths**: Relative paths within repository, no `../` allowed
- **Shell Safety**: Blocks all shell metacharacters (`;&|` \`$(){}[]<>`)

### Container Security
- Runs as non-root user (`appuser`)
- Named volume (no host bind mounts)
- Resource limits: 2 CPU, 2G memory
- Health checks every 30 seconds

## Installation

### Prerequisites
- Docker and Docker Compose
- Git (installed in container)
- Python 3.11+ (for development)

### Build and Run

```bash
# Build the Docker image
cd tools/tool-git-mcp
docker-compose build

# Start the service
docker-compose up -d

# Check health
curl http://localhost:8000/health
```

### Using Kamiwaza Build System

```bash
# Build using Kamiwaza tooling
make build TYPE=tool NAME=tool-git-mcp

# Sync App Garden compose files
make sync-compose

# Validate configuration
make validate

# Run tests
make test TYPE=tool NAME=tool-git-mcp
```

## Configuration

### Environment Variables

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `GIT_WORKSPACE_ROOT` | `/app/workspace` | No | Workspace directory for repositories |
| `GIT_AUTHOR_NAME` | `Kamiwaza Bot` | No | Default author name for commits |
| `GIT_AUTHOR_EMAIL` | `bot@kamiwaza.ai` | No | Default author email for commits |
| `GIT_COMMITTER_NAME` | `Kamiwaza Bot` | No | Default committer name |
| `GIT_COMMITTER_EMAIL` | `bot@kamiwaza.ai` | No | Default committer email |
| `PORT` | `8000` | No | HTTP server port |
| `MCP_PORT` | `8000` | No | MCP endpoint port |
| `MCP_PATH` | `/mcp` | No | MCP endpoint path |

### Custom Configuration

Create a `.env` file:

```bash
GIT_AUTHOR_NAME=Your Name
GIT_AUTHOR_EMAIL=your.email@example.com
```

## Usage Examples

### Clone Repository

```json
{
  "tool": "clone_repository",
  "arguments": {
    "url": "https://github.com/username/repo.git",
    "path": "my-repo",
    "branch": "main"
  }
}
```

Response:
```json
{
  "success": true,
  "repo_path": "my-repo",
  "branch": "main",
  "commit": "a1b2c3d4"
}
```

### Read File

```json
{
  "tool": "read_file",
  "arguments": {
    "repo_path": "my-repo",
    "file_path": "README.md"
  }
}
```

Response:
```json
{
  "success": true,
  "content": "# Project Title\n...",
  "path": "README.md"
}
```

### Write File

```json
{
  "tool": "write_file",
  "arguments": {
    "repo_path": "my-repo",
    "file_path": "src/main.py",
    "content": "print('Hello, World!')"
  }
}
```

Response:
```json
{
  "success": true,
  "path": "src/main.py",
  "bytes": 22
}
```

### Check Status

```json
{
  "tool": "git_status",
  "arguments": {
    "repo_path": "my-repo"
  }
}
```

Response:
```json
{
  "success": true,
  "branch": "main",
  "commit": "a1b2c3d4",
  "modified": ["src/main.py"],
  "staged": [],
  "untracked": ["new-file.txt"]
}
```

### Create Branch

```json
{
  "tool": "create_branch",
  "arguments": {
    "repo_path": "my-repo",
    "branch_name": "feature-xyz",
    "base_branch": "main"
  }
}
```

### Commit Changes

```json
{
  "tool": "commit_changes",
  "arguments": {
    "repo_path": "my-repo",
    "message": "Add new feature",
    "files": ["src/main.py", "src/utils.py"]
  }
}
```

Response:
```json
{
  "success": true,
  "commit": "b2c3d4e5",
  "message": "Add new feature",
  "branch": "feature-xyz"
}
```

### Push Changes

```json
{
  "tool": "push_changes",
  "arguments": {
    "repo_path": "my-repo",
    "remote": "origin",
    "branch": "feature-xyz"
  }
}
```

## MCP Protocol

### Endpoint
- **Base URL**: `http://localhost:8000`
- **MCP Path**: `/mcp`
- **Health Check**: `/health`

### Request Format

```http
POST /mcp HTTP/1.1
Content-Type: application/json

{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "clone_repository",
    "arguments": {
      "url": "https://github.com/example/repo.git"
    }
  }
}
```

### Response Format

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "success": true,
    "repo_path": "repo",
    "branch": "main",
    "commit": "a1b2c3d4"
  }
}
```

## Testing

### Run Tests

```bash
# Install dependencies
pip install -r requirements.txt

# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_security.py -v

# Run with coverage
pytest tests/ --cov=src/tool_git_mcp --cov-report=html
```

### Test Categories

- **Security Tests** (`tests/test_security.py`) - Path traversal, injection prevention
- **Git Operations Tests** (`tests/test_git_operations.py`) - All 13 Git operations
- **Server Tests** (`tests/test_server.py`) - Health check, tool registration

## Known Limitations

1. **No SSH Authentication** - Only HTTPS cloning supported (SSH planned for future)
2. **Single Workspace** - One workspace per container instance
3. **No Concurrent Operations** - No locking for parallel Git operations
4. **ASCII/UTF-8 Files Only** - Binary files not supported for read/write operations
5. **No Interactive Operations** - No merge conflict resolution or interactive rebases
6. **No Git Hooks** - Hooks are not executed (security feature)

## Architecture

```
tool-git-mcp/
├── src/tool_git_mcp/
│   ├── __init__.py          # Package initialization
│   ├── server.py            # FastMCP server with 13 tools
│   ├── security.py          # SecurityManager for validation
│   └── git_operations.py    # GitOperations wrapper
├── tests/
│   ├── test_server.py       # Server and registration tests
│   ├── test_security.py     # Security validation tests
│   └── test_git_operations.py  # Git operation tests
├── Dockerfile               # Container with git + Python
├── docker-compose.yml       # Local development setup
├── requirements.txt         # Python dependencies
├── kamiwaza.json           # Tool metadata
└── README.md               # This file
```

## Security Guarantees

1. ✅ **Workspace Isolation** - All operations within `/app/workspace`
2. ✅ **Path Traversal Prevention** - Multiple validation layers
3. ✅ **Command Injection Prevention** - Regex validation + GitPython parameterization
4. ✅ **Protocol Whitelist** - Only HTTPS and git:// allowed
5. ✅ **Non-Root Container** - Runs as `appuser`
6. ✅ **Structured Errors** - No sensitive path leakage

## Troubleshooting

### Container Won't Start

```bash
# Check logs
docker-compose logs tool-git-mcp

# Verify health check
docker-compose ps
```

### Tool Registration Issues

```bash
# Access MCP endpoint directly
curl http://localhost:8000/mcp

# Check tool list
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
```

### Permission Errors

Ensure the workspace volume has correct permissions:

```bash
docker-compose exec tool-git-mcp ls -la /app/workspace
```

### Git Authentication

For private repositories, use HTTPS URLs with tokens:

```
https://username:token@github.com/owner/repo.git
```

## Contributing

1. Follow the security model strictly
2. Add tests for all new operations
3. Validate against the security test suite
4. Update documentation for new features

## License

MIT License - See LICENSE file for details

## Support

For issues and questions:
- GitHub Issues: [kamiwaza-extensions](https://github.com/kamiwazaai/kamiwaza-extensions)
- Documentation: [Kamiwaza Docs](https://docs.kamiwaza.ai)
