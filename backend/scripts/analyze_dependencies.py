#!/usr/bin/env python3
"""
Script per analizzare e ottimizzare le dipendenze del progetto
"""

import subprocess


def run_uv_command(cmd: list[str]) -> str:
    """Esegue un comando uv e ritorna l'output"""
    try:
        result = subprocess.run(["uv"] + cmd, capture_output=True, text=True, check=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Errore eseguendo uv {' '.join(cmd)}: {e}")
        return ""


def analyze_dependencies() -> None:
    """Analizza le dipendenze del progetto"""
    print("🔍 Analisi Dipendenze Nutrifit Backend\n")

    # 1. Tree delle dipendenze
    print("📊 Albero delle dipendenze:")
    tree_output = run_uv_command(["tree", "--depth", "2"])
    if tree_output:
        lines = tree_output.split("\n")
        for line in lines[:20]:  # Prime 20 righe
            print(line)
        print("...\n")

    # 2. Check vulnerabilità (se safety è installato)
    print("🔒 Check vulnerabilità...")
    try:
        safety_output = subprocess.run(
            ["uv", "run", "safety", "check", "--json"], capture_output=True, text=True, timeout=30
        )
        if safety_output.returncode == 0:
            print("✅ Nessuna vulnerabilità rilevata")
        else:
            print("⚠️  Vulnerabilità trovate - eseguire manualmente 'uv run safety check'")
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        print("⚠️  Safety non disponibile - installare con: uv add --group dev safety")

    # 3. Analisi dimensioni
    print("\n📦 Analisi dimensioni pacchetti...")
    run_uv_command(["tree", "--package", "nutrifit-backend"])

    print("\n✨ Raccomandazioni:")
    print("1. Rimuovi flake8 dalle dipendenze principali (è già in dev)")
    print("2. Considera version ranges invece di pin fissi per maggiore flessibilità")
    print("3. Valuta se tutte le dipendenze ML (pandas, scipy, statsmodels) sono necessarie")
    print("4. Usa 'uv add --group dev safety' per check vulnerabilità automatici")


if __name__ == "__main__":
    analyze_dependencies()
