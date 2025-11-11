#!/usr/bin/env bash
# Script per monitoraggio automatico delle dipendenze con uv

set -e

echo "🔍 Nutrifit Dependency Health Check"
echo "==================================="

# 1. Check vulnerabilità
echo "🔒 Controllo vulnerabilità..."
if uv run pip-audit --desc; then
    echo "✅ Nessuna vulnerabilità trovata"
else
    echo "⚠️  Vulnerabilità rilevate - controlla l'output sopra"
fi

echo ""

# 2. Check dipendenze obsolete
echo "📦 Controllo aggiornamenti disponibili..."
uv lock --upgrade --dry-run > /dev/null 2>&1 && echo "✅ Lockfile aggiornato" || echo "📦 Aggiornamenti disponibili"

echo ""

# 3. Tree delle dipendenze principali
echo "🌳 Dipendenze principali:"
uv tree --depth 1 | head -20

echo ""

# 4. Check dimensioni
echo "📊 Statistiche ambiente:"
echo "Pacchetti installati: $(uv pip list | wc -l)"
echo "Dimensione .venv: $(du -sh .venv 2>/dev/null || echo 'N/A')"

echo ""
echo "🚀 Per aggiornare tutto: uv lock --upgrade && uv sync"
echo "🛠️  Per aggiornare un pacchetto: uv lock --upgrade-package NOME"