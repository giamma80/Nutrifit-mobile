#!/usr/bin/env bash
# Configurazione controlli dipendenze per Nutrifit Backend

# Modalità controllo dipendenze in preflight:
# - fail: fallisce se vulnerabilità (default)
# - warn: warning ma non blocca
# - skip: salta completamente
export DEPS_CHECK_MODE="${DEPS_CHECK_MODE:-fail}"

# Configurazioni markdownlint
export MD_STRICT="${MD_STRICT:-1}"

# Configurazioni schema drift
export SCHEMA_DRIFT_MODE="${SCHEMA_DRIFT_MODE:-fail}"

echo "🔧 Configurazione preflight:"
echo "   Deps check: $DEPS_CHECK_MODE"
echo "   Markdown strict: $MD_STRICT"  
echo "   Schema drift: $SCHEMA_DRIFT_MODE"
echo ""
echo "💡 Per personalizzare:"
echo "   DEPS_CHECK_MODE=warn make preflight    # warning per vulnerabilità"
echo "   DEPS_CHECK_MODE=skip make preflight    # salta controllo deps"
echo "   MD_STRICT=0 make preflight             # markdown non bloccante"
echo "   SCHEMA_DRIFT_MODE=warn make preflight  # schema drift warning"