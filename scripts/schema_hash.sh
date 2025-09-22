#!/usr/bin/env bash
set -euo pipefail
FILE="graphql/schema.graphql"
if [ ! -f "$FILE" ]; then
  echo "File non trovato: $FILE" >&2
  exit 1
fi
sha=$(shasum -a 256 "$FILE" | cut -c1-12)
echo "$sha"