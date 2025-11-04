###############################################
# MongoDB Container per Nutrifit
# Base: mongo:7.0 official image
###############################################

FROM mongo:7.0

# Labels OCI
LABEL org.opencontainers.image.title="Nutrifit MongoDB" \
      org.opencontainers.image.source="https://github.com/giamma80/Nutrifit-mobile" \
      org.opencontainers.image.licenses="Proprietary"

# Copia script di inizializzazione (opzionale)
# Questi script vengono eseguiti automaticamente al primo avvio
COPY init-mongo.js /docker-entrypoint-initdb.d/

# Espone porta MongoDB
EXPOSE 27017

# Healthcheck
HEALTHCHECK --interval=10s --timeout=5s --retries=5 --start-period=10s \
  CMD mongosh --eval "db.adminCommand('ping')" || exit 1

# Il container usa le env vars da .env per configurazione
# Vedi: mongodb/.env
