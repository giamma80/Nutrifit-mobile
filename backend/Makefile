.PHONY: help

# Proxy Makefile per sviluppatori abituati a `make`.
# Reindirizza ai target dello script bash `make.sh` (compatibile macOS Bash 3.2).
# Uso:
#   make help            -> mostra elenco target
#   make run             -> equivalente a ./make.sh run
#   make schema-check    -> equivalente a ./make.sh schema-check
# Passaggio variabili:
#   make version-bump LEVEL=minor
#   make commit MSG="feat(core): add xyz"
# Tutti i target invocano ./make.sh mantenendo la logica centralizzata lì.

SCRIPT=./make.sh

help:
	@$(SCRIPT) help

%:
	@$(SCRIPT) $@ $(MAKEFLAGS)

# Target espliciti per discoverability
schema-export:
	@$(SCRIPT) schema-export

schema-check:
	@$(SCRIPT) schema-check

# Dependencies Analysis (essentials only)
deps-check:
	@$(SCRIPT) deps-check

deps-health:
	@$(SCRIPT) deps-health

deps-update:
	@$(SCRIPT) deps-update

deps-outdated:
	@$(SCRIPT) deps-outdated

# Configuration
preflight-config:
	@$(SCRIPT) preflight-config

# Docker Compose shortcuts
docker-up:
	@$(SCRIPT) docker-up

docker-down:
	@$(SCRIPT) docker-down

docker-ps:
	@$(SCRIPT) docker-ps

docker-logs:
	@$(SCRIPT) docker-logs-all
