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
