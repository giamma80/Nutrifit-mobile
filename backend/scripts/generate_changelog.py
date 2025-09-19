#!/usr/bin/env python
"""Generate or augment CHANGELOG.md from conventional commits since last tag.

Usage:
    uv run python scripts/generate_changelog.py [--dry]

Logic:
 1. Find last tag (fallback: none -> use initial range).
 2. Collect commits after tag (git log <tag>..HEAD).
 3. Parse "type(scope): subject" lines.
 4. Group by type: feat, fix, docs, chore, refactor, test, perf, build, ci.
 5. Insert under [Unreleased] grouping sections (Added, Fixed, Changed, etc.).

Idempotent: existing identical bullet lines are not duplicated.
"""
from __future__ import annotations

import pathlib
import re
import subprocess
import sys
from collections import defaultdict

ROOT = pathlib.Path(__file__).resolve().parents[2]
CHANGELOG = ROOT / "CHANGELOG.md"
DRY = "--dry" in sys.argv

TYPES_MAP = {
    "feat": "Added",
    "fix": "Fixed",
    "docs": "Docs",
    "chore": "Chore",
    "refactor": "Changed",
    "perf": "Performance",
    "test": "Tests",
    "build": "Build",
    "ci": "CI",
}

COMMIT_RE = re.compile(r"^(?P<type>[a-z]+)(?:\([^)]*\))?!?: (?P<subject>.+)$")


def run(cmd: list[str]) -> str:
    """Execute a command returning stripped stdout."""
    return subprocess.check_output(cmd, text=True).strip()


def last_tag() -> str | None:
    """Return the most recent tag or None if none exist."""
    try:
        return run(["git", "describe", "--tags", "--abbrev=0"])
    except subprocess.CalledProcessError:
        return None


def collect_commits(since: str | None) -> list[str]:
    """Return commit subject lines after the given tag (or all if None)."""
    rev_range = f"{since}..HEAD" if since else "HEAD"
    try:
        out = run(["git", "log", "--pretty=format:%s", rev_range])
    except subprocess.CalledProcessError:
        return []
    return [line for line in out.splitlines() if line]


def parse_commit(line: str):
    """Parse a conventional commit line into (type, subject) or None."""
    match = COMMIT_RE.match(line)
    if not match:
        return None
    return match.group("type"), match.group("subject")


def load_changelog() -> list[str]:
    """Load existing changelog or return a minimal skeleton."""
    if CHANGELOG.exists():
        return CHANGELOG.read_text(encoding="utf-8").splitlines()
    return ["# Changelog", "", "## [Unreleased]", ""]


def ensure_unreleased(lines: list[str]) -> int:
    """Ensure an [Unreleased] section exists and return its index line."""
    for i, content in enumerate(lines):
        if content.startswith("## [Unreleased]"):
            return i
    lines.extend(["", "## [Unreleased]", ""])
    return len(lines) - 2


def insert_entries(lines: list[str], grouped: dict[str, set[str]]):
    """Insert grouped commit messages under the Unreleased section."""
    idx = ensure_unreleased(lines)
    # Find next section boundary
    insert_pos = idx + 1
    while insert_pos < len(lines) and not lines[insert_pos].startswith("## ["):
        insert_pos += 1
    block: list[str] = []
    order = [
        "Added",
        "Fixed",
        "Changed",
        "Performance",
        "Docs",
        "Tests",
        "CI",
        "Build",
        "Chore",
        "Other",
    ]
    for section in order:
        items = sorted(grouped.get(section, set()))
        if not items:
            continue
        block.append(f"### {section}")
        for it in items:
            block.append(f"- {it}")
        block.append("")
    if not block:
        return lines
    # Insert block at insert_pos
    new_lines = lines[:insert_pos] + block + lines[insert_pos:]
    return new_lines


def main():
    """Entry point for changelog generation."""
    since = last_tag()
    commits = collect_commits(since)
    grouped: dict[str, set[str]] = defaultdict(set)
    for commit_line in commits:
        parsed = parse_commit(commit_line)
        if not parsed:
            continue
        typ, subject = parsed
        section = TYPES_MAP.get(typ, "Other")
        grouped[section].add(subject)
    if not any(grouped.values()):
        print("[INFO] No conventional commits to add.")
        return
    lines = load_changelog()
    new_lines = insert_entries(lines, grouped)
    if lines == new_lines:
        print("[INFO] Changelog already up to date.")
        return
    if DRY:
        print("\n".join(new_lines))
    else:
        CHANGELOG.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
        print("[INFO] CHANGELOG updated.")


if __name__ == "__main__":  # pragma: no cover
    main()
