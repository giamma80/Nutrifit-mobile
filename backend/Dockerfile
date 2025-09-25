###############################################
# NutriFit Backend (FastAPI + Strawberry)
# Build con uv (dipendenze + runtime)       
###############################################

FROM python:3.11-slim AS base

# Versione applicazione (passare con --build-arg APP_VERSION=0.2.x)
ARG APP_VERSION="0.0.0-dev"
ENV APP_VERSION=${APP_VERSION}

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
# Copia codice applicativo principale (incluso cache.py richiesto da app.py)
COPY app.py cache.py nutrients.py ./
COPY openfoodfacts ./openfoodfacts
COPY rules ./rules
# NUOVO: repository (in-memory meal repo) e schema GraphQL
COPY repository ./repository
COPY graphql ./graphql

# Utente non-root con home (necessario per cache uv)
RUN useradd -u 1000 -m appuser \
  && mkdir -p /home/appuser/.cache/uv \
  && chown -R appuser /home/appuser/.cache /app
ENV UV_CACHE_DIR=/home/appuser/.cache/uv
USER appuser

EXPOSE 8000

# Labels OCI per tracciabilità
LABEL org.opencontainers.image.title="NutriFit Backend API" \
  org.opencontainers.image.source="https://github.com/giamma80/Nutrifit-mobile" \
  org.opencontainers.image.version="${APP_VERSION}" \
  org.opencontainers.image.licenses="Proprietary"

HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD curl -fsS http://localhost:8000/health || exit 1

# Avvio (PORT overridable runtime, default 8000)
ENV PORT=8000
CMD ["sh", "-c", "uv run uvicorn app:app --host 0.0.0.0 --port ${PORT}"]
