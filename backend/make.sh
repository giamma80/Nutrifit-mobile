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
CHANGELOG_FILE="$REPO_ROOT/CHANGELOG.md"

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

# Esegue markdownlint/markdownlint-cli2 dal root repository.
# Variabile: MD_STRICT=1 per fallire preflight se esistono violazioni.
run_markdownlint(){
  local md_tmp_out md_ec summary_files strict mode file_list tmp_list include_untracked
  # Default ora strict (1) disattivabile esplicitamente con MD_STRICT=0
  strict=${MD_STRICT:-1}
  mode=${MD_MODE:-auto}  # auto|git|glob
  include_untracked=${MD_INCLUDE_UNTRACKED:-0}
  if ! command -v npx >/dev/null 2>&1; then
    echo "MD_STATUS=SKIP"; echo "MD_MSG=npx assente"; return 0
  fi
  if [ ! -f "$REPO_ROOT/.markdownlint.yml" ] && \
     [ ! -f "$REPO_ROOT/.markdownlint.yaml" ] && \
     [ ! -f "$REPO_ROOT/.markdownlint.json" ]; then
    echo "MD_STATUS=SKIP"; echo "MD_MSG=no config"; return 0
  fi
  # NOTE: MD013 (line length) è volutamente disabilitata ("MD013": false) in .markdownlint.json
  # per ridurre rumore e velocizzare il completamento del gating. Re-abilitare
  # rimuovendo la chiave o impostandola ad oggetto se in futuro si decide di
  # imporre wrapping coerente.
  md_tmp_out="$(mktemp -t md_lint_out_XXXX)"
  (
    cd "$REPO_ROOT" || exit 0
    # Determina se usare git ls-files
    if [ "$mode" = "git" ] || { [ "$mode" = "auto" ] && command -v git >/dev/null 2>&1; }; then
      tmp_list="$(mktemp -t md_file_list_XXXX)"
      # Tracciati
      git ls-files '*.md' > "$tmp_list" 2>/dev/null || true
      if [ "$include_untracked" = "1" ]; then
        # Aggiungi untracked (escludendo pattern noti)
        git ls-files -o --exclude-standard '*.md' | grep -v -E '(^|/)node_modules/|(^|/)\.venv/|(^|/).pytest_cache/' >> "$tmp_list" 2>/dev/null || true
      fi
      # Filtra esclusioni ancora una volta (robustezza)
      grep -v -E '(^|/)node_modules/|(^|/)\.venv/|(^|/).pytest_cache/|(^|/)build/|(^|/)dist/|dist-info/|(^|/)licenses/|LICENSE.md$' "$tmp_list" > "$tmp_list.clean" || true
      mv "$tmp_list.clean" "$tmp_list"
      if [ ! -s "$tmp_list" ]; then
        echo "[run_markdownlint] Lista file Markdown vuota" >&2
        exit 0
      fi
      if npx --yes markdownlint-cli2 --version >/dev/null 2>&1; then
        # Usa xargs per evitare arg list troppo lunga
        xargs -a "$tmp_list" npx --yes markdownlint-cli2 2>&1 | tee "$md_tmp_out" >/dev/null
      else
        xargs -a "$tmp_list" npx --yes markdownlint 2>&1 | tee "$md_tmp_out" >/dev/null
      fi
      rm -f "$tmp_list"
    else
      # Fallback glob
      if npx --yes markdownlint-cli2 --version >/dev/null 2>&1; then
        npx --yes markdownlint-cli2 \
          "**/*.md" \
          "!**/node_modules/**" \
          "!**/.venv/**" \
          "!**/.pytest_cache/**" \
          "!**/build/**" \
          "!**/dist/**" \
          "!**/*.dist-info/**" \
          "!**/licenses/**" \
          "!**/LICENSE.md" 2>&1 | tee "$md_tmp_out" >/dev/null
      else
        npx --yes markdownlint "**/*.md" 2>&1 | \
          grep -v '/node_modules/' | \
          grep -v '/.venv/' | \
          grep -v '/.pytest_cache/' | \
          grep -v '/build/' | \
          grep -v '/dist/' | \
          grep -v '.dist-info/' | \
          grep -v 'licenses/' | tee "$md_tmp_out" >/dev/null
      fi
    fi
  )
  md_ec=$?
  # Se exit code 0 → PASS
  if [ $md_ec -eq 0 ]; then
  echo "MD_STATUS='PASS'"; echo "MD_MSG=''"; rm -f "$md_tmp_out"; return 0
  fi
  # Se file vuoto ma exit code !=0 → trattiamo come PASS silenzioso (edge)
  if [ ! -s "$md_tmp_out" ]; then
  echo "MD_STATUS='PASS'"; echo "MD_MSG=''"; rm -f "$md_tmp_out"; return 0
  fi
  # Conta violazioni per file
  local total violations_top
  total=$(wc -l < "$md_tmp_out" | tr -d ' ' || echo 0)
  # Detect npm execution issue (could not determine executable) -> treat as SKIP
  if grep -q 'could not determine executable to run' "$md_tmp_out" 2>/dev/null; then
    echo "MD_STATUS='SKIP'"; echo "MD_MSG='markdownlint exec error (npm)'"; cp "$md_tmp_out" "$LOG_DIR/md_lint_latest.log" 2>/dev/null || true; return 0
  fi
  mkdir -p "$LOG_DIR"
  cp "$md_tmp_out" "$LOG_DIR/md_lint_latest.log" 2>/dev/null || true
  # Calcola violazioni critiche (strutturali) vs totali
  local critical_rules="MD010 MD022 MD024 MD029 MD031 MD032 MD040 MD041 MD058 MD051"
  local crit_count=0 line code
  while IFS= read -r line; do
    code=$(echo "$line" | awk -F: '{print $4}' | sed 's/ //g')
    for r in $critical_rules; do
      if [ "$code" = "$r" ]; then crit_count=$((crit_count+1)); break; fi
    done
  done < "$md_tmp_out"
  {
    echo "--- MARKDOWNLINT (summary) ---"
    awk -F: 'NF>3 {print $1}' "$md_tmp_out" | sort | uniq -c | sort -rn | head -6 | awk '{printf "%s\t%s\n", $2, $1}'
    echo "Totale: $total  Critiche: $crit_count"
    echo "Log completo: backend/logs/md_lint_latest.log"
    echo "Prime 3:"; head -3 "$md_tmp_out" || true
  } >&2
  if [ "$strict" = "1" ] && [ $crit_count -gt 0 ]; then
    echo "MD_STATUS='FAIL'"; echo "MD_MSG='critiche=$crit_count tot=$total'"; return 0
  else
    echo "MD_STATUS='WARN'"; echo "MD_MSG='critiche=$crit_count tot=$total'"; return 0
  fi
}

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
  schema-guard      Verifica presenza duplicati e sync canonico/mirror schema
  preflight         format + lint + test + schema-check + commitlint
                   (markdownlint STRICT di default; disattiva con MD_STRICT=0)
                   (usa SCHEMA_DRIFT_MODE=warn per non fallire su semplice drift)
  changelog         Aggiorna CHANGELOG.md dai commit conventional (usa DRY=1 per anteprima)

  # Versioning / Release
  version-show      Mostra versione corrente
  version-verify    Verifica pyproject vs tag HEAD
  version-bump      Bump versione (LEVEL=patch|minor|major)
  release           preflight + changelog + bump + tag + push (auto include CHANGELOG)
  release-continue  Se release interrotta dopo finalize/bump: commit/tag/push senza ri-finalizzare

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
  mkdir -p "$LOG_DIR"
  fmt_status="SKIP"; fmt_msg=""
  lint_status="SKIP"; lint_msg=""
  tests_status="SKIP"; tests_msg=""
  schema_status="SKIP"; schema_msg=""
  guard_status="SKIP"; guard_msg=""
  commitlint_status="SKIP"; commitlint_msg=""
  md_status="SKIP"; md_msg=""

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

  # Schema guard (prima di drift)
  header "Schema guard"
  # Usa percorso assoluto dal root per robustezza (evita working dir inconsistenti)
  uv run python "$REPO_ROOT/scripts/schema_guard.py" >/dev/null 2>&1; guard_ec=$?
  if [ $guard_ec -eq 0 ]; then guard_status=PASS; else guard_status=FAIL; guard_msg="exit $guard_ec"; fi

  # Schema drift
    header "Schema drift check"
    schema_drift_mode=${SCHEMA_DRIFT_MODE:-fail} # fail|warn
    tmpfile="$(mktemp -t schema_tmp_XXXX).graphql"
    uv run python scripts/export_schema.py --out "$tmpfile" >/dev/null 2>&1
    export_ec=$?
    if [ $export_ec -ne 0 ]; then
      schema_status=FAIL; schema_msg="export failed ($export_ec)"; rm -f "$tmpfile"
    else
      if diff -q graphql/schema.graphql "$tmpfile" >/dev/null 2>&1; then
        schema_status=PASS; schema_msg=""
      else
        echo "---- SCHEMA DIFF ----"
        diff -u graphql/schema.graphql "$tmpfile" || true
        if [ "$schema_drift_mode" = "warn" ]; then
          schema_status=WARN; schema_msg="drift (warn mode)"
        else
          schema_status=FAIL; schema_msg="drift detected"
        fi
      fi
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

    # Markdownlint (soft o strict a seconda di MD_STRICT)
    eval "$(run_markdownlint)"
    md_status=${MD_STATUS:-SKIP}; md_msg=${MD_MSG:-}

    # Report finale
    echo
    header "Preflight Summary"
    {
      printf "%-12s | %-6s | %s\n" "GATE" "ESITO" "NOTE"
      printf "%-12s-+-%-6s-+-%s\n" "------------" "------" "----------------------------"
      printf "%-12s | %-6s | %s\n" "format" "$fmt_status" "$fmt_msg"
      printf "%-12s | %-6s | %s\n" "lint" "$lint_status" "$lint_msg"
      printf "%-12s | %-6s | %s\n" "tests" "$tests_status" "$tests_msg"
      printf "%-12s | %-6s | %s\n" "guard" "$guard_status" "$guard_msg"
      printf "%-12s | %-6s | %s\n" "schema" "$schema_status" "$schema_msg"
      printf "%-12s | %-6s | %s\n" "commitlint" "$commitlint_status" "$commitlint_msg"
      printf "%-12s | %-6s | %s\n" "markdown" "$md_status" "$md_msg"
    } | tee "$LOG_DIR/preflight_summary.log"

    # Garantire esistenza log markdown anche in PASS per artifact CI
    if [ ! -f "$LOG_DIR/md_lint_latest.log" ]; then
      : > "$LOG_DIR/md_lint_latest.log"
    fi

    # Determina exit code: fallisce se uno dei gate critici FAIL
    CRIT_FAIL=0
  if [ "$lint_status" = FAIL ] || [ "$tests_status" = FAIL ] || [ "$schema_status" = FAIL ] || [ "$guard_status" = FAIL ]; then CRIT_FAIL=1; fi
  # Se strict e markdownlint FAIL lo includiamo
  if [ "$md_status" = FAIL ]; then CRIT_FAIL=1; fi
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
  uv run python scripts/generate_changelog.py --finalize "$newv"
    # Rigenera eventuali commit non ancora raccolti (in caso di finalize vuoto)
    $0 changelog || true
    set_pyproject_version "$newv"
  git add "$VERSION_FILE" "$CHANGELOG_FILE" || true
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
      if git diff --quiet -- "$CHANGELOG_FILE"; then
        info "Nessun aggiornamento changelog"
      else
        info "CHANGELOG aggiornato (non ancora committato)"
      fi
    fi
    ;;

  release-continue)
    header "Release continue"
    # Caso: pyproject già aggiornato (versione nuova) e changelog finalizzato, ma commit/tag falliti
    current="$(pyproject_version)"
    # Verifica se esiste già un tag per questa versione
    if git rev-parse -q --verify "refs/tags/v$current" >/dev/null; then
      warn "Tag v$current già esistente: nulla da fare"
      exit 0
    fi
    # Assicura che CHANGELOG abbia la sezione della versione corrente (grepping semplice)
  if ! grep -q "^## \[$current\]" "$CHANGELOG_FILE"; then
      warn "Sezione v$current non trovata in CHANGELOG: potenziale incompletezza"
    fi
    git add "$VERSION_FILE" "$CHANGELOG_FILE" || true
    if git diff --cached --quiet; then
      warn "Nessuna differenza da committare (forse commit già creato)"
    else
      git commit -m "chore(release): bump version to $current" || true
    fi
    git tag "v$current" || true
    git push || true
    git push --tags || true
    info "Release completata/recuperata per v$current"
    ;;

  schema-export)
    header "Export GraphQL SDL"
    uv run python scripts/export_schema.py
    ;;

  schema-sync)
    header "Schema sync"
    DRY_RUN=${DRY_RUN:-0}
    tmpfile="$(mktemp -t schema_export_XXXX).graphql"
    mkdir -p logs
    export_err_log="logs/schema_export_last.log"
    if ! uv run python scripts/export_schema.py --out "$tmpfile" > /dev/null 2>"$export_err_log"; then
      err "Export schema fallito"
      [ -s "$export_err_log" ] && head -n 20 "$export_err_log" >&2 || true
      rm -f "$tmpfile"
      exit 3
    fi
    backend_file="graphql/schema.graphql"
    mirror_file="$REPO_ROOT/graphql/schema.graphql"
    if [ ! -f "$backend_file" ]; then warn "File backend/schema mancante: verrà creato"; fi
    if [ ! -f "$mirror_file" ]; then warn "File mirror root mancante: verrà creato"; fi
    backend_hash_old=$(sha256sum "$backend_file" 2>/dev/null | awk '{print $1}' || echo "NONE")
    mirror_hash_old=$(sha256sum "$mirror_file" 2>/dev/null | awk '{print $1}' || echo "NONE")
    new_hash=$(sha256sum "$tmpfile" | awk '{print $1}')
    changed=0
    mirror_only_aligned=0
    if ! diff -q "$backend_file" "$tmpfile" >/dev/null 2>&1; then
      changed=1
      if [ "$DRY_RUN" = 0 ]; then
        cp "$tmpfile" "$backend_file"
        cp "$tmpfile" "$mirror_file"
      fi
    fi
    # Se backend già coincide con export ma mirror differisce, riallinea solo mirror
    if diff -q "$backend_file" "$tmpfile" >/dev/null 2>&1 && ! diff -q "$backend_file" "$mirror_file" >/dev/null 2>&1; then
      mirror_only_aligned=1
      changed=1
      if [ "$DRY_RUN" = 0 ]; then
        cp "$backend_file" "$mirror_file"
      fi
    fi
    rm -f "$tmpfile"
    backend_hash_new=$(sha256sum "$backend_file" 2>/dev/null | awk '{print $1}' || echo "NONE")
    mirror_hash_new=$(sha256sum "$mirror_file" 2>/dev/null | awk '{print $1}' || echo "NONE")
    status="unchanged"; [ $changed -eq 1 ] && status="updated"
    echo "{\"status\":\"$status\",\"backend_before\":\"$backend_hash_old\",\"backend_after\":\"$backend_hash_new\",\"mirror_before\":\"$mirror_hash_old\",\"mirror_after\":\"$mirror_hash_new\",\"hash_export\":\"$new_hash\",\"mirror_only_aligned\":$mirror_only_aligned,\"dry_run\":$DRY_RUN}" | tee logs/schema_sync_last.json
    [ $changed -eq 1 ] && info "Schema aggiornato ($status)" || info "Schema già allineato"
    ;;

  schema-check)
    header "Schema check (DRY)"
    DRY_RUN=1 $0 schema-sync >/dev/null || ec=$? || true
    ec=${ec:-0}
    if [ $ec -eq 3 ]; then err "Export fallito"; exit 1; fi
    sync_json="logs/schema_sync_last.json"
    drift=$(jq -r '.status' "$sync_json" 2>/dev/null || echo unknown)
    if [ "$drift" = "updated" ]; then
      err "Schema drift rilevato (usa: ./make.sh schema-sync)"
      jq '.' "$sync_json" 2>/dev/null || true
      exit 2
    fi
    info "Schema allineato"
    ;;

  schema-guard)
    header "Schema guard"
    uv run python "$REPO_ROOT/scripts/schema_guard.py" || exit $?
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
