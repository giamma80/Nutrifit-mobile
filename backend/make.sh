#!/usr/bin/env bash
set -euo pipefail

# Simple helper script for local dev tasks.
# Usage: ./make.sh <target>
# Targets:
#   setup    -> uv sync (prod+dev)
#   run      -> start API dev server
#   test     -> run pytest
#   lint     -> flake8 + mypy
#   docker   -> build docker image nutrifit-backend:dev
#   clean    -> remove .venv and __pycache__
#   format   -> black .
#   all      -> setup + lint + test

TARGET=${1:-help}

function header(){ echo -e "\n=== $1 ==="; }

case "$TARGET" in
  setup)
    header "Sync deps"
    uv sync --all-extras --dev
    ;;
  run)
    header "Dev server"
    uv run uvicorn app:app --reload --port 8080
    ;;
  test)
    header "Tests"
    uv run pytest -q
    ;;
  lint)
    header "Flake8"
    uv run flake8 .
    header "Mypy"
    uv run mypy .
    ;;
  format)
    header "Format (black)"
    uv run black .
    ;;
  docker)
    header "Docker build"
    docker build -t nutrifit-backend:dev .
    ;;
  clean)
    header "Cleanup"
    rm -rf .venv **/__pycache__ || true
    ;;
  all)
    $0 setup
    $0 lint
    $0 test
    ;;
  *)
    echo "Available targets: setup | run | test | lint | format | docker | clean | all" >&2
    exit 1
    ;;
 esac
