# ================================================
# NutriFit Calorie Balance Service - Dockerfile
# ================================================
# Multi-target build: development and production
# Python 3.11 + Poetry + FastAPI + Supabase Client

FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd --gid 1000 appuser \
    && useradd --uid 1000 --gid appuser --shell /bin/bash --create-home appuser

# Install Poetry version 1.6.1
ENV POETRY_VERSION=1.6.1
RUN pip install poetry==$POETRY_VERSION

# Configure Poetry
ENV POETRY_NO_INTERACTION=1 \
    POETRY_VENV_IN_PROJECT=0 \
    POETRY_VIRTUALENVS_CREATE=false

# Set working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml poetry.lock README.md ./

# Copy application code
COPY app/ ./app/

# Install dependencies globally (no virtual env needed in container)
RUN poetry install --only=main

# Change ownership of the app directory to appuser
RUN chown -R appuser:appuser /app

# ====================================
# Development Environment
# ====================================
FROM base as development

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8002

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8002/health || exit 1

# Development command with hot reload
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8002", "--reload"]

# ====================================
# Production Environment
# ====================================
FROM base as production

# Switch to non-root user
USER appuser

# Expose production port
EXPOSE 8000

# Health check for production
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Production command (no reload, multiple workers)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
