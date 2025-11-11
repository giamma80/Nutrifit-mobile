# Dependencies Management con uv

## 📋 Target Makefile per Analisi Dipendenze

Il progetto Nutrifit Backend ora include target specializzati per l'analisi e ottimizzazione delle dipendenze usando **uv**.

### 🛠️ Target Disponibili

| Target | Descrizione | Uso |
|--------|-------------|-----|
| `make deps-check` | Check vulnerabilità (pip-audit) | Controllo sicurezza |
| `make deps-health` | Health check completo con statistiche | Monitoraggio generale |
| `make deps-update` | Mostra aggiornamenti disponibili (dry-run) | Pianificazione aggiornamenti |
| `make deps-outdated` | Lista pacchetti obsoleti | Identificazione dipendenze datate |

### � Integrazione con Preflight

Il controllo dipendenze è ora **integrato nel preflight** per garantire sicurezza pre-deploy:

```bash
make preflight  # Include deps-check automaticamente
```

#### Configurazione Controllo Dipendenze

- **`DEPS_CHECK_MODE=fail`** (default): Fallisce se vulnerabilità
- **`DEPS_CHECK_MODE=warn`**: Warning ma non blocca deploy
- **`DEPS_CHECK_MODE=skip`**: Salta controllo dipendenze

```bash
# Esempi configurazione
DEPS_CHECK_MODE=warn make preflight    # Warning per vulnerabilità  
DEPS_CHECK_MODE=skip make preflight    # Salta deps check
make preflight-config                  # Mostra configurazione corrente
```

### �🚀 Workflow Raccomandato

1. **Controllo quotidiano**:
   ```bash
   make deps-health
   ```

2. **Prima del deploy** (automatico):
   ```bash
   make preflight  # Include deps-check + altri controlli
   ```

3. **Controllo aggiornamenti**:
   ```bash
   make deps-update
   make deps-outdated  # Se servono dettagli specifici
   ```

   ```

4. **Configurazione preflight**:
   ```bash
   make preflight-config  # Mostra opzioni configurazione
   ```

### 📊 Output dei Report

- **JSON**: `logs/dependencies_report.json`
- **Log health**: `logs/deps_report_quick.txt`
- **Backup optimize**: `pyproject.toml.backup`
- **Preflight summary**: `logs/preflight_summary.log`

### 🔧 Strumenti Integrati

- **uv**: Gestione moderna dipendenze Python
- **pip-audit**: Controllo vulnerabilità PyPI
- **safety**: Database vulnerabilità commerciale
- **deptry**: Analisi dipendenze inutilizzate (opzionale)

### ✅ Best Practice Implementate

1. **Sicurezza first**: Controlli automatizzati vulnerabilità nel preflight
2. **Version ranges**: Uso di range invece di pin fissi
3. **Separazione dev/prod**: Dipendenze di sviluppo isolate
4. **Backup automatici**: Prima delle ottimizzazioni
5. **Report strutturati**: JSON + human-readable
6. **Integration preflight**: Controlli pre-deploy automatici con configurazione flessibile
7. **Fail-fast**: Blocco deploy se vulnerabilità critiche (configurabile)

### 🎯 Benefici

- **⚡ Velocità**: uv è 10-100x più veloce di pip
- **🔒 Sicurezza**: Controlli automatizzati vulnerabilità nel preflight
- **📊 Visibilità**: Report dettagliati stato dipendenze

## 📌 Note sulle Dipendenze Critiche

### FastAPI + Starlette Compatibility

**Situazione attuale (12 Nov 2025):**
- **FastAPI**: 0.121.1 (latest)
- **Starlette**: 0.49.3 (vincolata da FastAPI `<0.50.0`)
- **Starlette 0.50.0**: Disponibile ma incompatibile

**Vincolo dipendenza:**
```
FastAPI 0.121.1 richiede: starlette>=0.40.0,<0.50.0
```

**Strategia:**
- ⏳ **Attendere release FastAPI** che supporti Starlette 0.50.0+
- 🔄 **Monitorare** FastAPI releases su PyPI
- ⚡ **Aggiornare entrambi insieme** quando disponibile

**Come verificare:**
```bash
# Controlla se FastAPI supporta Starlette più recenti
uv add starlette==0.50.0  # Fallirà se incompatibile
```
- **🛠️ Automazione**: Target make per workflow ripetibili
- **💾 Efficienza**: Ottimizzazioni spazio e performance
- **🎛️ Configurabilità**: Modalità warn/skip per ambienti diversi