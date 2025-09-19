#!/usr/bin/env bash
set -euo pipefail

# Nutrifit Backend Cockpit Script
# Uso: ./make.sh <target> [OPZIONI]
# Obiettivo: fornire un punto unico di ingresso per operazioni comuni (dev, qualità, docker, git, release).
# Tutte le operazioni falliscono con exit code != 0 se qualcosa va storto (fail-fast).

TARGET=${1:-help}; shift || true

PROJECT_NAME="nutrifit-backend"
IMAGE_NAME="nutrifit-backend:dev"
CONTAINER_NAME="nutrifit-backend-dev"
SERVER_PID_FILE=".server.pid"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VERSION_FILE="${SCRIPT_DIR}/pyproject.toml"
LOG_DIR="logs"
SERVER_LOG_FILE="${LOG_DIR}/server.log"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && git rev-parse --show-toplevel 2>/dev/null || echo "$SCRIPT_DIR/..")"

# Colori (disattivabili con NO_COLOR=1)
if [ "${NO_COLOR:-0}" = "1" ] || [ -n "${CI:-}" ]; then
  C_RESET=""; C_INFO=""; C_WARN=""; C_ERR=""; C_HEAD=""
else
  # Usare printf per evitare interpretazioni strane su bash 3.2
  C_RESET='\033[0m'
  C_INFO='\033[36m'    # Cyan
  C_WARN='\033[33m'    # Giallo
  C_ERR='\033[31m'     # Rosso
  C_HEAD='\033[35;1m'  # Magenta bold
fi

header(){ printf "\n${C_HEAD}=== %s ===${C_RESET}\n" "$1"; }
info(){ printf "${C_INFO}[INFO] %s${C_RESET}\n" "$1"; }
warn(){ printf "${C_WARN}[WARN] %s${C_RESET}\n" "$1"; }
err(){ printf "${C_ERR}[ERR ] %s${C_RESET}\n" "$1" >&2; }

assert_clean_worktree(){
  if ! git diff --quiet --ignore-submodules --cached; then err "Index con modifiche staged"; exit 1; fi
  if ! git diff --quiet --ignore-submodules; then err "Working tree con modifiche non committate"; exit 1; fi
}

pyproject_version(){ grep -m1 '^version[[:space:]]*=' "$VERSION_FILE" | sed -E 's/^[^=]+= *"([0-9]+\.[0-9]+\.[0-9]+)".*/\1/'; }

set_pyproject_version(){
  local newv="$1"
  local vf="$VERSION_FILE"
  awk -v v="$newv" 'BEGIN{done=0} {
    if(!done && $0 ~ /^version[[:space:]]*=/){
      sub(/version[[:space:]]*=.*/,"version = \"" v "\""); done=1
    }
    print
  }' "$vf" > "${vf}.tmp" && mv "${vf}.tmp" "$vf"
}

semver_bump(){
  local current MA MI PA level
  current="$(pyproject_version)" || { err "Versione non trovata"; exit 1; }
  echo "$current" | grep -Eq '^[0-9]+\.[0-9]+\.[0-9]+$' || { err "Formato versione non valido: $current"; exit 1; }
  level="$1"
  # Split manuale (compat bash 3.2)
  local OIFS="$IFS"; IFS='.'; set -- $current; IFS="$OIFS"
  MA="$1"; MI="$2"; PA="$3"
  if [ "$level" = "major" ]; then
    MA=`expr "$MA" + 1`; MI=0; PA=0
  elif [ "$level" = "minor" ]; then
    MI=`expr "$MI" + 1`; PA=0
  elif [ "$level" = "patch" ]; then
    PA=`expr "$PA" + 1`
  else
  err "Livello bump non valido: usa patch|minor|major"; exit 1
  fi
  echo "${MA}.${MI}.${PA}"
}

run_commitlint_range(){
  if command -v npx >/dev/null 2>&1; then
    npx commitlint --from=origin/main --to=HEAD --verbose || { err "Commitlint fallito"; exit 1; }
  else
    warn "npx non disponibile: salto commitlint";
  fi
}

server_running(){ [[ -f "$SERVER_PID_FILE" ]] && ps -p "$(cat $SERVER_PID_FILE)" >/dev/null 2>&1; }

docker_running(){ docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$" 2>/dev/null || return 1; }

case "$TARGET" in
  help)
    cat <<EOF
Targets disponibili:
  # Base / Dev
  setup             Sync dipendenze (uv)
  run               Avvia server (foreground, hot reload)
  run-bg            Avvia server in background
  stop              Stop server background
  logs              Tail log server locale
  status            Stato (versione, server, docker)

  # Qualità
  format            Black format
  lint              Flake8 + mypy
  typecheck         Solo mypy (type checking completo)
  test              Pytest
  schema-export     Esporta SDL GraphQL (aggiorna file versionato)
  schema-check      Verifica drift schema (fail se differente)
  preflight         format + lint + test + schema-check + commitlint
  changelog         Aggiorna CHANGELOG.md dai commit conventional (usa DRY=1 per anteprima)

  # Versioning / Release
  version-show      Mostra versione corrente
  version-verify    Verifica pyproject vs tag HEAD
  version-bump      Bump versione (LEVEL=patch|minor|major)
  release           preflight + changelog + bump + tag + push (auto include CHANGELOG)

  # Git helpers
  commit MSG="..."  Preflight + commit
                    (usa COMMIT_SCOPE=all per includere modifiche fuori da backend/)
  push              Preflight + push ramo

  # Docker
  check-docker      Verifica disponibilità demone Docker
  docker-build      Build immagine locale (${IMAGE_NAME})
  docker-run        Esegui container (porta 8080)
  docker-stop       Stop & remove container
  docker-logs       Segui log container
  docker-restart    Restart container
  docker-shell      Entra nel container con shell interattiva
  docker-test       Esegue test integrazione (curl health/version + GraphQL)

  # Utility
  clean             Rimuovi .venv, __pycache__, pid
  clean-dist        Rimuovi eventuale dist residua
  all               setup + lint + test
EOF
    ;;

  setup)
    header "Sync deps"
    uv sync --all-extras --dev
    ;;

  format)
    header "Format (black)"
    uv run black .
    ;;

  lint)
    header "Flake8"; uv run flake8 .
    header "Mypy"; uv run mypy .
    ;;

  test)
    header "Tests"; uv run pytest -q
    ;;

  run)
    header "Dev server (foreground)"
    mkdir -p "$LOG_DIR"
    echo "# $(date -Iseconds) START (fg)" >> "$SERVER_LOG_FILE"
    uv run uvicorn app:app --reload --port 8080 2>&1 | tee -a "$SERVER_LOG_FILE"
    ;;

  run-bg)
    header "Dev server (background)"
    if server_running; then warn "Server già in esecuzione (PID $(cat $SERVER_PID_FILE))"; exit 0; fi
    mkdir -p "$LOG_DIR"
    echo "# $(date -Iseconds) START (bg)" >> "$SERVER_LOG_FILE"
    (uv run uvicorn app:app --reload --port 8080 >>"$SERVER_LOG_FILE" 2>&1 & echo $! > "$SERVER_PID_FILE")
    sleep 1
    if server_running; then info "Server avviato PID $(cat $SERVER_PID_FILE)"; else err "Avvio server fallito"; exit 1; fi
    ;;

  stop)
    header "Stop server background"
    if server_running; then 
      kill "$(cat $SERVER_PID_FILE)" && echo "# $(date -Iseconds) STOP" >> "$SERVER_LOG_FILE" || true
      rm -f "$SERVER_PID_FILE" 
      info "Server stoppato" 
    else 
      warn "Nessun server attivo" 
    fi
    ;;

  docker-build)
    $0 check-docker
    header "Docker build ${IMAGE_NAME}"
    docker build -t "${IMAGE_NAME}" .
    ;;

  docker-run)
    $0 check-docker
    header "Docker run ${CONTAINER_NAME}"
    if docker_running; then warn "Container già attivo"; exit 0; fi
    docker run -d --rm -p 8080:8080 --name "${CONTAINER_NAME}" "${IMAGE_NAME}" uv run uvicorn app:app --host 0.0.0.0 --port 8080
    info "Container avviato"
    ;;

  docker-stop)
    $0 check-docker || true
    header "Docker stop ${CONTAINER_NAME}"
    if docker_running; then docker stop "${CONTAINER_NAME}" >/dev/null && info "Container stoppato"; else warn "Container non in esecuzione"; fi
    ;;

  docker-logs)
    $0 check-docker
    header "Docker logs ${CONTAINER_NAME} (Ctrl+C per uscire)"
    if docker_running; then docker logs -f "${CONTAINER_NAME}"; else err "Container non attivo"; exit 1; fi
    ;;

  docker-restart)
    $0 docker-stop || true
    $0 docker-run
    ;;

  docker-shell)
    $0 check-docker
    header "Docker shell ${CONTAINER_NAME}"
    if docker_running; then
      # Preferisci bash se presente, altrimenti sh
      docker exec -it "${CONTAINER_NAME}" bash >/dev/null 2>&1 && docker exec -it "${CONTAINER_NAME}" bash || docker exec -it "${CONTAINER_NAME}" sh
    else
      err "Container non attivo"; exit 1
    fi
    ;;

  docker-test)
    $0 check-docker
    header "Docker integration test"
    if ! docker_running; then err "Container non attivo: avvia prima docker-run"; exit 2; fi
    bash scripts/integration_test.sh
    info "Integration test OK (script)"
    ;;

  check-docker)
    header "Docker daemon check"
    if docker info >/dev/null 2>&1; then
      info "Docker disponibile"
      exit 0
    else
      err "Docker non disponibile (avvia Docker Desktop o 'colima start')"
      exit 1
    fi
    ;;

  preflight)
    header "Preflight"
  # Raccogli esiti singoli gates senza abort immediato (compat bash 3.2: niente associative arrays)
  set +e
  fmt_status="SKIP"; fmt_msg=""
  lint_status="SKIP"; lint_msg=""
  tests_status="SKIP"; tests_msg=""
  schema_status="SKIP"; schema_msg=""
  commitlint_status="SKIP"; commitlint_msg=""

    # Format (non blocking): se format modifica file, consideriamo PASS comunque
    header "Format (black)"
    uv run black . >/dev/null 2>&1
    blk_ec=$?
  if [ $blk_ec -eq 0 ]; then fmt_status=PASS; else fmt_status=FAIL; fmt_msg="black exit $blk_ec"; fi

    # Lint: flake8 + mypy (se uno dei due fallisce -> FAIL)
    header "Flake8"
    uv run flake8 . >/dev/null 2>&1; flake_ec=$?
    header "Mypy"
    uv run mypy . >/dev/null 2>&1; mypy_ec=$?
    if [ $flake_ec -eq 0 ] && [ $mypy_ec -eq 0 ]; then lint_status=PASS; else lint_status=FAIL; lint_msg="flake8=$flake_ec mypy=$mypy_ec"; fi

    # Tests
    header "Tests"
    uv run pytest -q >/dev/null 2>&1; test_ec=$?
  if [ $test_ec -eq 0 ]; then tests_status=PASS; else tests_status=FAIL; tests_msg="pytest exit $test_ec"; fi

    # Schema drift
    header "Schema drift check"
    tmpfile="$(mktemp -t schema_tmp_XXXX).graphql"
    uv run python scripts/export_schema.py --out "$tmpfile" >/dev/null 2>&1
    export_ec=$?
    if [ $export_ec -ne 0 ]; then
      schema_status=FAIL; schema_msg="export failed ($export_ec)"; rm -f "$tmpfile"
    else
      if diff -q graphql/schema.graphql "$tmpfile" >/dev/null 2>&1; then schema_status=PASS; else schema_status=FAIL; schema_msg="drift detected"; echo "---- SCHEMA DIFF ----"; diff -u graphql/schema.graphql "$tmpfile" || true; fi
      rm -f "$tmpfile"
    fi

    # Commitlint (soft)
    if command -v npx >/dev/null 2>&1; then
      if [ -f "package.json" ] || [ -f "../package.json" ]; then
        if [ -d "node_modules/@commitlint/config-conventional" ] || [ -d "../node_modules/@commitlint/config-conventional" ]; then
          npx commitlint --from=origin/main --to=HEAD --quiet >/dev/null 2>&1
          cl_ec=$?
          if [ $cl_ec -eq 0 ]; then commitlint_status=PASS; else commitlint_status=WARN; commitlint_msg="exit $cl_ec"; fi
        else
          commitlint_status=SKIP; commitlint_msg="deps mancanti"
        fi
      else
        commitlint_status=SKIP; commitlint_msg="no package.json"
      fi
    else
      commitlint_status=SKIP; commitlint_msg="npx assente"
    fi

    # Report finale
    echo
    header "Preflight Summary"
    printf "%-12s | %-6s | %s\n" "GATE" "ESITO" "NOTE"
    printf "%-12s-+-%-6s-+-%s\n" "------------" "------" "----------------------------"
    printf "%-12s | %-6s | %s\n" "format" "$fmt_status" "$fmt_msg"
    printf "%-12s | %-6s | %s\n" "lint" "$lint_status" "$lint_msg"
    printf "%-12s | %-6s | %s\n" "tests" "$tests_status" "$tests_msg"
    printf "%-12s | %-6s | %s\n" "schema" "$schema_status" "$schema_msg"
    printf "%-12s | %-6s | %s\n" "commitlint" "$commitlint_status" "$commitlint_msg"

    # Determina exit code: fallisce se uno dei gate critici FAIL
    CRIT_FAIL=0
    if [ "$lint_status" = FAIL ] || [ "$tests_status" = FAIL ] || [ "$schema_status" = FAIL ]; then CRIT_FAIL=1; fi
    if [ $CRIT_FAIL -eq 1 ]; then
      err "Preflight FAILED"
      set -e
      exit 1
    fi
    info "Preflight OK"
    set -e
    ;;

  commit)
    header "Commit helper"
    : "${MSG:?Devi passare il messaggio: MSG=\"type(scope): subject\"}" || true
    $0 preflight
    COMMIT_SCOPE=${COMMIT_SCOPE:-backend}
    if [ "$COMMIT_SCOPE" = "all" ]; then
      info "Commit scope: intero repository ($REPO_ROOT)"
      git add "$REPO_ROOT"
    else
      # Avvisa se esistono modifiche fuori da backend/ non incluse
      if git status --porcelain | awk '{print $2}' | grep -qv '^backend/'; then
        warn "Rilevate modifiche fuori da backend/ NON incluse (esegui COMMIT_SCOPE=all ./make.sh commit MSG=...)"
      fi
      git add .
    fi
    if git diff --cached --quiet; then
      err "Nessun cambiamento staged (probabilmente solo file fuori da backend/)."
      exit 1
    fi
    git commit -m "$MSG"
    info "Commit creato"
    ;;

  push)
    header "Push"
    $0 preflight
    git push
    info "Push eseguito"
    ;;

  version-bump)
    header "Version bump"
    LEVEL=${LEVEL:-patch}
    assert_clean_worktree
    current="$(pyproject_version)"; newv="$(semver_bump "$LEVEL")"
    info "Versione corrente: $current → nuova: $newv"
  read -r -p "Confermi bump ($LEVEL)? [y/N] " ans; ans_lc=$(printf '%s' "$ans" | tr '[:upper:]' '[:lower:]'); { [ "$ans_lc" = "y" ] || [ "$ans_lc" = "yes" ]; } || { warn "Abort"; exit 1; }
    set_pyproject_version "$newv"
    git add "$VERSION_FILE"
    git commit -m "chore(release): bump version to $newv"
    git tag "v$newv"
    info "Bump completato (commit + tag)"
    ;;

  version-show)
    header "Version corrente"
    echo "$(pyproject_version)"
    ;;

  version-verify)
    header "Verifica versione"
    current="$(pyproject_version)"
    tag=$(git describe --tags --exact-match 2>/dev/null || true)
    if [ -z "$tag" ]; then
      warn "Nessun tag HEAD: versione pyproject=$current (OK se non ancora rilasciato)"
      exit 0
    fi
    if [ "v$current" = "$tag" ]; then
      info "MATCH: pyproject $current == tag $tag"
      exit 0
    else
      err "MISMATCH: pyproject $current != tag $tag"; exit 2
    fi
    ;;

  release)
    header "Release pipeline"
    LEVEL=${LEVEL:-patch}
    $0 preflight
    current="$(pyproject_version)"; newv="$(semver_bump "$LEVEL")"
    info "Release: $current → $newv"
    # Prima di chiedere conferma mostra eventuale changelog che verrà finalizzato
    DRY=1 $0 changelog || true
  read -r -p "Procedere (finalize + bump)? [y/N] " ans; ans_lc=$(printf '%s' "$ans" | tr '[:upper:]' '[:lower:]'); { [ "$ans_lc" = "y" ] || [ "$ans_lc" = "yes" ]; } || { warn "Abort"; exit 1; }
    # Finalizza sezione Unreleased come nuova versione
    uv run python scripts/generate_changelog.py --finalize "v$newv"
    # Rigenera eventuali commit non ancora raccolti (in caso di finalize vuoto)
    $0 changelog || true
    set_pyproject_version "$newv"
    git add "$VERSION_FILE" CHANGELOG.md || true
    git commit -m "chore(release): bump version to $newv"
    git tag "v$newv"
    git push && git push --tags
    info "Release completata"
    ;;

  changelog)
    header "Generate changelog"
    if [ "${DRY:-0}" = "1" ]; then
      uv run python scripts/generate_changelog.py --dry
    else
      uv run python scripts/generate_changelog.py
      if git diff --quiet -- CHANGELOG.md; then
        info "Nessun aggiornamento changelog"
      else
        info "CHANGELOG aggiornato (non ancora committato)"
      fi
    fi
    ;;

  schema-export)
    header "Export GraphQL SDL"
    uv run python scripts/export_schema.py
    ;;

  schema-check)
    header "Schema drift check"
    tmpfile="$(mktemp -t schema_tmp_XXXX).graphql"
    uv run python scripts/export_schema.py --out "$tmpfile" >/dev/null 2>&1 || { err "Export schema fallito"; rm -f "$tmpfile"; exit 1; }
    if ! diff -u graphql/schema.graphql "$tmpfile" > /dev/null 2>&1; then
      echo "---- SCHEMA DIFF ----"
      diff -u graphql/schema.graphql "$tmpfile" || true
      rm -f "$tmpfile"
      err "Schema drift rilevato: eseguire ./make.sh schema-export e committare"
      exit 2
    fi
    rm -f "$tmpfile"
    info "Schema allineato"
    ;;

  status)
    header "Status"
    echo "Branch: $(git rev-parse --abbrev-ref HEAD)"
    echo "Version: $(pyproject_version)"
    if server_running; then echo "Server: RUNNING (PID $(cat $SERVER_PID_FILE))"; else echo "Server: stopped"; fi
    if docker_running; then echo "Docker: RUNNING ($CONTAINER_NAME)"; else echo "Docker: stopped"; fi
    echo "Untracked changes: $(git status --porcelain | wc -l | tr -d ' ')"
    [[ -f "$SERVER_LOG_FILE" ]] && echo "Log size: $(du -h \"$SERVER_LOG_FILE\" | cut -f1)" || true
    ;;

  clean)
    header "Cleanup"
    rm -rf .venv **/__pycache__ "$SERVER_PID_FILE" || true
    ;;

  logs)
    header "Tail server log (Ctrl+C per uscire)"
    [[ -f "$SERVER_LOG_FILE" ]] || { warn "Nessun log ancora. Avvia il server."; exit 0; }
    tail -f "$SERVER_LOG_FILE"
    ;;

  clean-dist)
    header "Clean dist"
    rm -rf dist || true
    ;;

  all)
    $0 setup
    $0 lint
    $0 test
    ;;

  typecheck)
    header "Type check (mypy)"
    uv run mypy .
    ;;

  *)
    # Default: mostra help
    cat "$0" | sed -n '/Targets disponibili:/,$p'
    exit 1
    ;;
esac
