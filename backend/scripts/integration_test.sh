#!/usr/bin/env bash
set -euo pipefail

# Simple integration test script
# - Waits for service http://localhost:8080 to respond
# - Checks /health, /version and GraphQL { health serverTime }
# Retries configurable with INTEG_RETRIES (default 20) and INTEG_SLEEP (default 1)

RETRIES=${INTEG_RETRIES:-20}
SLEEP=${INTEG_SLEEP:-1}
BASE_URL=${BASE_URL:-http://localhost:8080}

log(){ echo "[integ] $*"; }

wait_service(){
  local i=0
  while [ $i -lt $RETRIES ]; do
    if curl -fsS "$BASE_URL/health" >/dev/null 2>&1; then
      return 0
    fi
    i=$((i+1))
    sleep "$SLEEP"
  done
  log "Service non raggiungibile dopo $RETRIES tentativi" >&2
  return 1
}

run_tests(){
  local health version gql
  health=$(curl -fsS "$BASE_URL/health") || { log "Health fallito"; return 2; }
  version=$(curl -fsS "$BASE_URL/version") || { log "Version fallito"; return 3; }
  gql=$(curl -fsS -H 'Content-Type: application/json' -d '{"query":"{ health serverTime }"}' "$BASE_URL/graphql") || { log "GraphQL fallito"; return 4; }

  echo "HEALTH: $health"
  echo "VERSION: $version"
  echo "GRAPHQL: $gql"

  echo "$health"  | grep -q '"status"' || { log "Campo status assente"; return 10; }
  echo "$version" | grep -q '"version"' || { log "Campo version assente"; return 11; }
  echo "$gql"     | grep -q '"health"' || { log "Campo health GraphQL assente"; return 12; }

  log "SUCCESS: integrazione OK"
}

main(){
  wait_service
  run_tests
}

main "$@"
