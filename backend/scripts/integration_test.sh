#!/usr/bin/env bash
set -euo pipefail

# Simple integration test script
# - Waits for service http://localhost:8080 to respond
# - Checks /health, /version and GraphQL { health serverTime }
# - Executes mutation logMeal twice to probe (optional) idempotency
#   Set EXACT_LOGMEAL_IDEMPOTENCY=1 to fail if IDs differ, otherwise just warn.
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
  local health version gql meal1 meal2 meal_idempotent_payload
  health=$(curl -fsS "$BASE_URL/health") || { log "Health fallito"; return 2; }
  version=$(curl -fsS "$BASE_URL/version") || { log "Version fallito"; return 3; }
  gql=$(curl -fsS -H 'Content-Type: application/json' -d '{"query":"{ health serverTime }"}' "$BASE_URL/graphql") || { log "GraphQL fallito"; return 4; }

  echo "HEALTH: $health"
  echo "VERSION: $version"
  echo "GRAPHQL: $gql"

  echo "$health"  | grep -q '"status"' || { log "Campo status assente"; return 10; }
  echo "$version" | grep -q '"version"' || { log "Campo version assente"; return 11; }
  echo "$gql"     | grep -q '"health"' || { log "Campo health GraphQL assente"; return 12; }

  # Test mutation logMeal + idempotenza
  meal_idempotent_payload='{"query":"mutation($input: LogMealInput!){ logMeal(input:$input){ id name quantityG idempotencyKey calories } }","variables":{"input":{"name":"Apple","quantityG":100}}}'
  meal1=$(curl -fsS -H 'Content-Type: application/json' -d "$meal_idempotent_payload" "$BASE_URL/graphql") || { log "Mutation logMeal fallita"; return 20; }
  meal2=$(curl -fsS -H 'Content-Type: application/json' -d "$meal_idempotent_payload" "$BASE_URL/graphql") || { log "Seconda mutation logMeal fallita"; return 21; }
  echo "MEAL1: $meal1"
  echo "MEAL2: $meal2"
  # Estrazione ID robusta:
  # 1. Se jq disponibile usalo (più affidabile)
  # 2. Fallback sed con spazi opzionali
  if command -v jq >/dev/null 2>&1; then
    id1=$(echo "$meal1" | jq -r '.data.logMeal.id // empty') || true
    id2=$(echo "$meal2" | jq -r '.data.logMeal.id // empty') || true
  else
    id1=$(echo "$meal1" | sed -n 's/.*"id"[[:space:]]*:[[:space:]]*"\([0-9a-fA-F-]*\)".*/\1/p') || true
    id2=$(echo "$meal2" | sed -n 's/.*"id"[[:space:]]*:[[:space:]]*"\([0-9a-fA-F-]*\)".*/\1/p') || true
  fi
  if [ -z "$id1" ] || [ -z "$id2" ]; then
    log "IDs non estratti correttamente dalla risposta logMeal"; return 22
  fi
  # Idempotenza opzionale: per default WARN se differiscono (feature non ancora implementata);
  # se EXACT_LOGMEAL_IDEMPOTENCY=1 allora fallisce se non coincidono.
  if [ "$id1" != "$id2" ]; then
    if [ "${EXACT_LOGMEAL_IDEMPOTENCY:-0}" = "1" ]; then
  log "Idempotenza FALLITA (enforced): id diversi ($id1 vs $id2)"; return 23
    else
      log "WARNING: logMeal non idempotente (ids diversi) - test continua (EXACT_LOGMEAL_IDEMPOTENCY=1 per forzare fail)"
    fi
  else
    log "Idempotenza OK (stesso id)"
  fi
  log "SUCCESS: integrazione OK"
}

main(){
  wait_service
  run_tests
}

main "$@"
