# ============================================
# Multi-stage Dockerfile for Agent Service
# ============================================

# Stage 1: Builder
FROM python:3.12-slim AS builder

# Install system dependencies including Node.js
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    ca-certificates \
    gnupg \
    && mkdir -p /etc/apt/keyrings \
    && curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg \
    && echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_20.x nodistro main" | tee /etc/apt/sources.list.d/nodesource.list \
    && apt-get update \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Install uv
ADD https://astral.sh/uv/install.sh /tmp/uv-installer.sh
RUN sh /tmp/uv-installer.sh && rm /tmp/uv-installer.sh

ENV PATH="/root/.local/bin:${PATH}"

# Set working directory
WORKDIR /build

# Copy MCP servers (needed for subprocess execution)
# Exclude local .venv to avoid copying broken symlinks
COPY MCP/user-mcp /build/MCP/user-mcp
COPY MCP/meal-mcp /build/MCP/meal-mcp
COPY MCP/activity-mcp /build/MCP/activity-mcp
COPY MCP/nutritional-profile-mcp /build/MCP/nutritional-profile-mcp

# Install MCP dependencies in virtualenv using uv
# Create fresh venv in container (not copying local .venv with broken symlinks)
RUN uv venv /build/MCP/.venv && \
    cd /build/MCP/user-mcp && uv pip install --python /build/MCP/.venv/bin/python mcp httpx pydantic fastmcp && \
    cd /build/MCP/meal-mcp && uv pip install --python /build/MCP/.venv/bin/python mcp httpx pydantic fastmcp && \
    cd /build/MCP/activity-mcp && uv pip install --python /build/MCP/.venv/bin/python mcp httpx pydantic fastmcp && \
    cd /build/MCP/nutritional-profile-mcp && uv pip install --python /build/MCP/.venv/bin/python mcp httpx pydantic fastmcp

# Copy agent-service files
COPY agent-service/pyproject.toml ./
COPY agent-service/app.py ./
COPY agent-service/auth/ ./auth/
COPY agent-service/agents/ ./agents/
COPY agent-service/tools/ ./tools/

# Install agent-service dependencies using uv
RUN uv pip install --system -e .

# ============================================
# Stage 2: Runtime
# ============================================
FROM python:3.12-slim

# Install runtime dependencies including Node.js
RUN apt-get update && apt-get install -y \
    curl \
    ca-certificates \
    gnupg \
    && mkdir -p /etc/apt/keyrings \
    && curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg \
    && echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_20.x nodistro main" | tee /etc/apt/sources.list.d/nodesource.list \
    && apt-get update \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 appuser

# Set working directory
WORKDIR /app

# Copy MCP servers from builder
COPY --from=builder /build/MCP /app/MCP

# Copy Python packages from builder (system-wide installation)
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY --chown=appuser:appuser agent-service/app.py .
COPY --chown=appuser:appuser agent-service/auth/ ./auth/
COPY --chown=appuser:appuser agent-service/agents/ ./agents/
COPY --chown=appuser:appuser agent-service/tools/ ./tools/
COPY --chown=appuser:appuser agent-service/pyproject.toml .

# Set environment
ENV PATH="/usr/local/bin:${PATH}"
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run application
CMD ["python", "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
