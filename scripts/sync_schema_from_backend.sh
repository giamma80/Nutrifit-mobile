#!/usr/bin/env bash
set -euo pipefail

# Placeholder script per sincronizzare lo schema GraphQL dal backend.
# Scenario: backend locale in esecuzione su http://localhost:8080 oppure uso del file esportato.
# FUTURO: sostituire con chiamata introspection + generazione SDL pulita oppure download da artifact CI.

BACKEND_URL="${BACKEND_URL:-http://localhost:8080/graphql}"
TARGET_MIRROR="graphql/schema.graphql"
TMP_JSON="/tmp/schema_introspection.json"
TMP_SDL="/tmp/schema.graphql"

cat >&2 <<EOF
[INFO] Sync schema
  Backend: $BACKEND_URL
  Mirror : $TARGET_MIRROR
EOF

# Verifica dipendenze basilari
command -v curl >/dev/null || { echo "[ERRORE] curl non trovato" >&2; exit 1; }

# Introspection query minimale (può essere estesa / sostituita da tooling dedicato)
INTROSPECTION_QUERY='{"query":"query IntrospectionQuery { __schema { types { name } } }"}'

curl -s -H 'Content-Type: application/json' -d "$INTROSPECTION_QUERY" "$BACKEND_URL" > "$TMP_JSON" || {
  echo "[ERRORE] Introspection fallita" >&2; exit 1;
}

# Placeholder conversione: al momento NON rigeneriamo SDL dall'introspection (non banale senza tool). 
# Copiamo il file dal backend se esiste.
if [ -f backend/graphql/schema.graphql ]; then
  cp backend/graphql/schema.graphql "$TARGET_MIRROR"
  echo "[INFO] Copiato schema backend → $TARGET_MIRROR" >&2
else
  echo "[WARN] backend/graphql/schema.graphql assente: mantenuto mirror esistente" >&2
fi

echo "[DONE] Schema sync completata." >&2
