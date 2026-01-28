FROM python:3.11-slim

WORKDIR /app

# Install git and curl (for health checks)
RUN apt-get update \
    && apt-get install -y --no-install-recommends git curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ /app/src/

ENV MCP_PORT=8000
ENV MCP_PATH=/mcp
ENV PORT=8000
ENV PYTHONPATH=/app/src
ENV GIT_WORKSPACE_ROOT=/app/workspace

# Create appuser and workspace directory
RUN useradd -m appuser \
    && mkdir -p /app/workspace \
    && chown -R appuser /app

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "tool_git_mcp.server:app", "--host", "0.0.0.0", "--port", "8000"]
