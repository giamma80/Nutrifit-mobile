#!/usr/bin/env python3
"""Smart dependency update script.

Analizza i vincoli di dipendenze e propone aggiornamenti sicuri,
evitando conflitti come Starlette/FastAPI.

Usage:
    python scripts/smart_update.py [--apply] [--category patch|minor|major]
"""

import subprocess
import json
from typing import Dict, List, Tuple, Any
from pathlib import Path
import shutil


def run_command(cmd: List[str], capture_output: bool = True) -> subprocess.CompletedProcess[str]:
    """Run command and return result."""
    try:
        return subprocess.run(cmd, capture_output=capture_output, text=True, check=True)
    except subprocess.CalledProcessError as e:
        if capture_output:
            print(f"❌ Command failed: {' '.join(cmd)}")
            print(f"Error: {e.stderr}")
        raise


def get_outdated_packages() -> List[Dict[str, Any]]:
    """Get list of outdated packages using uv."""
    try:
        result = run_command(["uv", "pip", "list", "--outdated", "--format", "json"])
        packages: List[Dict[str, Any]] = json.loads(result.stdout)
        return packages
    except (subprocess.CalledProcessError, json.JSONDecodeError):
        print("⚠️  Fallback to uv pip list outdated")
        result = run_command(["uv", "pip", "list", "--outdated"])
        return parse_pip_list_output(result.stdout)


def parse_pip_list_output(output: str) -> List[Dict[str, str]]:
    """Parse pip list output into structured data."""
    packages = []
    lines = output.strip().split("\n")[2:]  # Skip headers

    for line in lines:
        parts = line.split()
        if len(parts) >= 3:
            packages.append({"name": parts[0], "version": parts[1], "latest_version": parts[2]})

    return packages


def categorize_update(current: str, latest: str) -> str:
    """Categorize update type: patch, minor, major."""
    try:
        current_parts = [int(x) for x in current.split(".")]
        latest_parts = [int(x) for x in latest.split(".")]

        # Pad to same length
        max_len = max(len(current_parts), len(latest_parts))
        current_parts.extend([0] * (max_len - len(current_parts)))
        latest_parts.extend([0] * (max_len - len(latest_parts)))

        if latest_parts[0] > current_parts[0]:
            return "major"
        elif latest_parts[1] > current_parts[1]:
            return "minor"
        else:
            return "patch"
    except (ValueError, IndexError):
        return "unknown"


def check_update_compatibility(package: str, new_version: str) -> Tuple[bool, str]:
    """Check if package update is compatible using uv dry-run."""

    # Create temporary pyproject.toml backup
    pyproject_path = Path("pyproject.toml")
    backup_path = Path("pyproject.toml.temp_backup")

    try:
        # Backup original
        shutil.copy2(pyproject_path, backup_path)

        # Try to update package
        result = subprocess.run(
            ["uv", "add", f"{package}=={new_version}"], capture_output=True, text=True
        )

        if result.returncode == 0:
            # Restore backup and return success
            shutil.move(backup_path, pyproject_path)
            run_command(["uv", "sync", "--extra", "dev", "--quiet"])
            return True, "✅ Compatible"
        else:
            # Parse error message for insights
            error_msg = result.stderr
            if "No solution found" in error_msg:
                if "depends on" in error_msg:
                    # Extract dependency conflict info
                    conflict_info = extract_conflict_info(error_msg)
                    return False, f"❌ Conflict: {conflict_info}"
                else:
                    return False, "❌ Dependency conflict"
            else:
                return False, f"❌ Update failed: {error_msg[:100]}..."

    except Exception as e:
        return False, f"❌ Error testing: {str(e)}"

    finally:
        # Always restore backup if it exists
        if backup_path.exists():
            shutil.move(backup_path, pyproject_path)
            run_command(["uv", "sync", "--extra", "dev", "--quiet"])


def extract_conflict_info(error_msg: str) -> str:
    """Extract useful conflict information from uv error message."""
    lines = error_msg.split("\n")

    for line in lines:
        if "depends on" in line and "<" in line:
            # Extract constraint info
            return line.strip()

    return "dependency version conflict"


def main() -> None:
    """Main function."""
    import argparse

    parser = argparse.ArgumentParser(description="Smart dependency updater")
    parser.add_argument(
        "--apply", action="store_true", help="Apply safe updates (default: dry-run)"
    )
    parser.add_argument(
        "--category",
        choices=["patch", "minor", "major"],
        default="patch",
        help="Update category to consider",
    )
    parser.add_argument("--include-dev", action="store_true", help="Include dev dependencies")

    args = parser.parse_args()

    print("🔍 Smart Dependency Update Analysis")
    print("=" * 50)

    # Get outdated packages
    print("📦 Fetching outdated packages...")
    outdated = get_outdated_packages()

    if not outdated:
        print("✅ All packages are up to date!")
        return

    # Categorize and filter updates
    safe_updates = []
    blocked_updates = []

    print(f"📊 Found {len(outdated)} outdated packages")
    print(f"🎯 Analyzing {args.category} updates...")
    print()

    for pkg in outdated:
        name = pkg["name"]
        current = pkg["version"]
        latest = pkg["latest_version"]

        update_type = categorize_update(current, latest)

        # Filter by requested category
        if args.category == "patch" and update_type not in ["patch"]:
            continue
        elif args.category == "minor" and update_type not in ["patch", "minor"]:
            continue
        # major includes all

        print(f"🧪 Testing {name}: {current} → {latest} ({update_type})")

        # Test compatibility
        compatible, reason = check_update_compatibility(name, latest)

        if compatible:
            safe_updates.append((name, current, latest, update_type))
            print(f"   {reason}")
        else:
            blocked_updates.append((name, current, latest, update_type, reason))
            print(f"   {reason}")
        print()

    # Summary
    print("📋 UPDATE SUMMARY")
    print("=" * 50)

    if safe_updates:
        print(f"✅ Safe updates ({len(safe_updates)}):")
        for name, current, latest, update_type in safe_updates:
            print(f"   • {name}: {current} → {latest} ({update_type})")
        print()

    if blocked_updates:
        print(f"❌ Blocked updates ({len(blocked_updates)}):")
        for name, current, latest, update_type, reason in blocked_updates:
            print(f"   • {name}: {current} → {latest} ({update_type})")
            print(f"     {reason}")
        print()

    # Apply updates if requested
    if args.apply and safe_updates:
        print("🚀 Applying safe updates...")

        for name, current, latest, update_type in safe_updates:
            print(f"   Updating {name} to {latest}...")
            try:
                run_command(["uv", "add", f"{name}=={latest}"], capture_output=False)
            except subprocess.CalledProcessError:
                print(f"   ❌ Failed to update {name}")

        print("✅ Updates completed!")

        # Run sync to ensure consistency
        print("🔄 Syncing environment (including dev dependencies)...")
        run_command(["uv", "sync", "--extra", "dev"], capture_output=False)

    elif not args.apply:
        print("💡 Use --apply to execute safe updates")

    # Recommendations
    if blocked_updates:
        print("\n🎯 RECOMMENDATIONS")
        print("=" * 50)
        for name, current, latest, update_type, reason in blocked_updates:
            if "starlette" in name.lower() and "fastapi" in reason:
                print(f"📌 {name}: Wait for FastAPI to support Starlette {latest}")
            elif "major" in update_type:
                print(f"⚠️  {name}: Major update - review changelog before upgrading")
            else:
                print(f"🔍 {name}: Check dependency constraints")


if __name__ == "__main__":
    main()
