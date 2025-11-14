#!/usr/bin/env python3
"""
Report rapido dipendenze per Nutrifit Backend
"""

import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional, Union


def run_command(cmd: list[str]) -> Optional[str]:
    """Esegue comando e ritorna output"""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return None


def get_package_count() -> Union[int, str]:
    """Conta pacchetti installati"""
    try:
        output = run_command(["uv", "pip", "list"])
        if output:
            return len(output.split("\n")) - 1  # -1 per header
    except Exception:
        pass
    return "N/A"


def check_security() -> str:
    """Check veloce sicurezza"""
    try:
        result = subprocess.run(
            ["uv", "run", "pip-audit"], capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            return "✅ Clean"
        else:
            return "⚠️  Issues found"
    except Exception:
        return "❓ Unknown"


def get_pyproject_version() -> str:
    """Legge versione da pyproject.toml"""
    try:
        with open("pyproject.toml", "r") as f:
            for line in f:
                if line.startswith("version"):
                    return line.split('"')[1]
    except Exception:
        pass
    return "N/A"


def main() -> None:
    print("=" * 50)
    print("📊 NUTRIFIT DEPENDENCIES REPORT")
    print("=" * 50)

    # Info progetto
    version = get_pyproject_version()
    print(f"🚀 Progetto: nutrifit-backend v{version}")

    # Pacchetti
    pkg_count = get_package_count()
    print(f"📦 Pacchetti installati: {pkg_count}")

    # Sicurezza
    security_status = check_security()
    print(f"🔒 Sicurezza: {security_status}")

    # Dimensioni ambiente
    try:
        venv_size = subprocess.run(
            ["du", "-sh", ".venv"], capture_output=True, text=True, timeout=10
        )
        if venv_size.returncode == 0:
            size = venv_size.stdout.split()[0]
            print(f"💾 Dimensione .venv: {size}")
    except Exception:
        print("💾 Dimensione .venv: N/A")

    # Tree veloce
    print("\n🌳 Dipendenze principali:")
    try:
        tree = run_command(["uv", "tree", "--depth", "1"])
        if tree:
            lines = tree.split("\n")[1:11]  # Prime 10 righe
            for line in lines:
                if line.strip():
                    print(f"   {line}")
            if len(tree.split("\n")) > 11:
                print("   ...")
    except Exception:
        print("   Errore nel recupero tree")

    print(f"\n🕐 Report generato: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Log rapido
    log_path = Path("logs/deps_report_quick.txt")
    log_path.parent.mkdir(exist_ok=True)
    with open(log_path, "w") as f:
        f.write("Nutrifit Dependencies Quick Report\n")
        f.write(f"Generated: {datetime.now().isoformat()}\n")
        f.write(f"Version: {version}\n")
        f.write(f"Packages: {pkg_count}\n")
        f.write(f"Security: {security_status}\n")

    print(f"📄 Log salvato: {log_path}")


if __name__ == "__main__":
    main()
