#!/usr/bin/env bash
# Script per ottimizzazione automatica delle dipendenze con uv

set -e

echo "🚀 Nutrifit Dependencies Optimizer"
echo "=================================="

# 1. Backup del pyproject.toml corrente
cp pyproject.toml pyproject.toml.backup
echo "📋 Backup creato: pyproject.toml.backup"

# 2. Analisi dipendenze non utilizzate (se deptry disponibile)
echo ""
echo "🔍 Ricerca dipendenze non utilizzate..."
if uv run --with deptry deptry . --json > deps_analysis.json 2>/dev/null; then
    if [ -s deps_analysis.json ] && [ "$(cat deps_analysis.json)" != "{}" ]; then
        echo "⚠️  Dipendenze non utilizzate rilevate:"
        cat deps_analysis.json | jq -r '.unused[]?' 2>/dev/null || cat deps_analysis.json
    else
        echo "✅ Nessuna dipendenza inutilizzata"
    fi
else
    echo "⚠️  deptry non disponibile - salto analisi utilizzo"
fi

# 3. Check vulnerabilità
echo ""
echo "🔒 Controllo vulnerabilità..."
if uv run pip-audit --desc --format=json > security_report.json 2>/dev/null; then
    vuln_count=$(cat security_report.json | jq '. | length' 2>/dev/null || echo 0)
    if [ "$vuln_count" -gt 0 ]; then
        echo "⚠️  $vuln_count vulnerabilità trovate"
        cat security_report.json | jq -r '.[] | "- \(.name) \(.version): \(.id)"' 2>/dev/null || true
    else
        echo "✅ Nessuna vulnerabilità"
    fi
else
    echo "⚠️  Controllo vulnerabilità fallito"
fi

# 4. Analisi aggiornamenti
echo ""
echo "📦 Controllo aggiornamenti..."
if uv lock --upgrade --dry-run > upgrade_log.txt 2>&1; then
    if grep -q "Updated" upgrade_log.txt; then
        echo "📈 Aggiornamenti disponibili:"
        grep "Updated" upgrade_log.txt | head -10
        echo ""
        echo "🚀 Per applicare: uv lock --upgrade && uv sync"
    else
        echo "✅ Tutte le dipendenze aggiornate"
    fi
else
    echo "⚠️  Controllo aggiornamenti fallito"
fi

# 5. Analisi dimensioni
echo ""
echo "📊 Statistiche finali:"
echo "Pacchetti installati: $(uv pip list | wc -l)"
echo "Dimensione .venv: $(du -sh .venv 2>/dev/null | cut -f1 || echo 'N/A')"

# 6. Pulizia file temporanei
rm -f deps_analysis.json security_report.json upgrade_log.txt

echo ""
echo "✨ Ottimizzazione completata!"
echo "🔄 Per ripristinare: mv pyproject.toml.backup pyproject.toml && uv sync"