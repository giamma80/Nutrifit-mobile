#!/usr/bin/env bash
set -euo pipefail
# Simple markdown auto-fix utility.
# Heuristics:
#  - Trim trailing spaces (excluding lines ending with two spaces used for <br>)
#  - Collapse >1 blank line to max 1 (outside of fenced code blocks)
#  - Ensure file ends with single newline
#  - Convert tabs to 4 spaces (outside fenced code blocks)
#  - Normalize heading spacing: '#Heading' -> '# Heading'
# Limitations: non idempotent for exotic edge cases; run before commit.

ROOT="${1:-.}"
# Nota: niente 'shopt -s globstar' per compatibilità con bash 3.2 (macOS).

tempfile() { mktemp -t md_fix_XXXX; }

process_file(){
  local f="$1" tmp fence=0
  tmp="$(tempfile)"
  awk 'BEGIN{fence=0} {
    line=$0
    if(match(line,/^```/)){fence = 1 - fence; print line; next}
    if(fence==1){print line; next}
    # tabs -> 4 spaces
    gsub(/\t/,"    ",line)
    # normalize heading space
    if(match(line,/^#+[^#\s]/)){ sub(/^#+/ , substr(line,1,RLENGTH)); sub(/^#+/ , "& ", line)}
    # trim trailing spaces (keep if exactly two for markdown line break)
    if(match(line,/  $/)==0){ sub(/[ \t]+$/ ,"", line) }
    print line
  }' "$f" > "$tmp.stage1"
  # Collapse multiple blank lines (outside code fences already handled)
  awk 'BEGIN{prev_blank=0} {
    if($0 ~ /^$/){ if(prev_blank==1) next; prev_blank=1; print; next } else { prev_blank=0; print }
  }' "$tmp.stage1" > "$tmp.final"
  # Ensure newline at EOF
  printf '%s\n' "$(cat "$tmp.final")" > "$f"
  rm -f "$tmp.stage1" "$tmp.final"
}

exclude_pattern='/(node_modules|\.venv|\.pytest_cache|build|dist|licenses)/'
find "$ROOT" -type f -name '*.md' -print0 | while IFS= read -r -d '' f; do
  # Skip excluded directories
  if echo "$f" | grep -qE "$exclude_pattern"; then
    echo "[fix_markdown] Skipped $f"; continue
  fi
  process_file "$f"
  echo "[fix_markdown] Processed $f"
done

echo "Done."