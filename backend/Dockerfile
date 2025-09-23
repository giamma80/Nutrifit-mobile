###############################################
# NutriFit Backend (FastAPI + Strawberry)
# Build con uv (dipendenze + runtime)       
###############################################

FROM python:3.11-slim AS base

# Passare versione applicazione a build time (es: --build-arg VERSION=0.2.0)
ARG VERSION="0.1.2"
ENV APP_VERSION=${VERSION}

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_LINK_MODE=copy \
    PIP_NO_CACHE_DIR=1

# Dipendenze di sistema minime (aggiungere solo se servono build wheels native)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install uv (script ufficiale)
RUN curl -LsSf https://astral.sh/uv/install.sh | sh \
  && mv /root/.local/bin/uv /usr/local/bin/uv \
  && mv /root/.local/bin/uvx /usr/local/bin/uvx

# uv ora è globale in /usr/local/bin (nessuna dipendenza su /root)

# Copia solo il manifest principale (uv.lock non versionato al momento)
COPY pyproject.toml ./

# Sync dipendenze (solo prod per immagine runtime finale)
RUN uv sync --no-dev --all-extras

# Copia sorgenti
COPY app.py ./
COPY openfoodfacts ./openfoodfacts
COPY rules ./rules

# Utente non-root con home (necessario per cache uv)
RUN useradd -u 1000 -m appuser \
  && mkdir -p /home/appuser/.cache/uv \
  && chown -R appuser /home/appuser/.cache /app
ENV UV_CACHE_DIR=/home/appuser/.cache/uv
USER appuser

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD curl -fsS http://localhost:8080/health || exit 1

# Avvio
CMD ["uv", "run", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]
