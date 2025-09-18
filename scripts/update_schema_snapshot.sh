#!/usr/bin/env bash
set -euo pipefail

SCHEMA_FILE="lib/graphql/schema_nutrition.graphql"
SNAPSHOT_FILE="lib/graphql/schema_nutrition.snapshot.graphql"

if [[ ! -f "$SCHEMA_FILE" ]]; then
  echo "Schema file not found: $SCHEMA_FILE" >&2
  exit 1
fi

cp "$SCHEMA_FILE" "$SNAPSHOT_FILE"

TAG_LINE="# Snapshot schema_nutrition.graphql @ $(date +%Y-%m-%dT%H:%M:%S%z)"
# Ensure first line comment replaced
sed -i '' "1s|.*|$TAG_LINE|" "$SNAPSHOT_FILE" || true

echo "Snapshot aggiornato: $SNAPSHOT_FILE"

git --no-pager diff --name-only "$SNAPSHOT_FILE" || true
