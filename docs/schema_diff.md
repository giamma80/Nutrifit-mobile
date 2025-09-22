## Semantic GraphQL Schema Diff

Documento di riferimento completo per lo script `backend/scripts/verify_schema_breaking.py` che esegue un diff semantico (ridotto) tra lo schema GraphQL canonico del backend e il mirror versionato nella root (`graphql/schema.graphql`).

> Percorso Script
> Lo script canonico vive solamente in: `backend/scripts/verify_schema_breaking.py`.
> Il precedente stub duplicato in `scripts/verify_schema_breaking.py` è stato rimosso per evitare ambiguità.

### Obiettivo
Garantire che ogni modifica al contratto GraphQL sia:
1. Classificata (aligned / additive / breaking)
2. Visibile in CI con exit code coerente
3. Documentata (changelog + nota PR)

### Percorso File
| Ruolo | Path |
|-------|------|
| Fonte canonica | `backend/graphql/schema.graphql` |
| Mirror versionato | `graphql/schema.graphql` |
| Script diff | `backend/scripts/verify_schema_breaking.py` |
| Test | `backend/tests/test_schema_diff.py` |

### Categorie di Classificazione
| Categoria | Condizioni | Exit Code | Azione PR |
|-----------|-----------|-----------|-----------|
| `aligned` | Nessuna differenza semantica rilevante | 0 | Merge immediato |
| `additive` | Solo aggiunta di campi o valori enum | 0 | Aggiornare changelog backend |
| `breaking` | Rimozioni campi / violazioni interfacce | 1 | Richiede bump major + migrazione client |

In futuro verrà introdotta `deprecation` per cambi esclusivamente di marcatura `@deprecated`.
La categoria `deprecation` (work-in-progress) tratterà aggiunte di direttive `@deprecated` senza rimozioni come neutre (o separate) rispetto ad additive.

### Output JSON
Esempio:
```json
{
  "classification": "additive",
  "added_fields": {"MealEntry": ["nutrientSnapshotJson"]},
  "removed_fields": {},
  "added_enum_values": {},
  "interface_breaks": {},
  "tool": "verify_schema_breaking",
  "tool_version": "0.1.0"
}
```

| Campo | Descrizione |
|-------|-------------|
| `classification` | aligned / additive / breaking |
| `added_fields` | Campi nuovi raggruppati per type |
| `removed_fields` | Campi rimossi per type |
| `added_enum_values` | Valori enum aggiunti |
| `interface_breaks` | Violazioni implementazioni (campi mancanti) |
| `tool`, `tool_version` | Metadati script |

### Comandi Locali
```bash
cd backend
uv run python scripts/verify_schema_breaking.py | jq
```

Verifica exit code:
```bash
uv run python scripts/verify_schema_breaking.py >/dev/null || echo "classification=breaking"
```

### Integrazione CI (Proposta)
Step GitHub Action (`schema-diff.yml`):
1. Checkout
2. Install dipendenze backend (`uv sync`)
3. Export schema backend (target `schema-export`)
4. Eseguire script diff
5. `jq -r .classification` → set output
6. Se `breaking` → `exit 1`
7. Caricare artifact JSON
8. (Estensione) Commento automatico PR con tabella cambi

### Heuristics Attuali
- Parser basato su regex: `(type|interface|enum)` blocchi
- Estrazione campi tramite pattern `name:` (ignora argomenti / direttive)
- Interfacce: controlla presenza campi obbligatori nei type implementatori
- Enum: aggiunte considerate additive, direttive ignorate

### Limitazioni
| Area | Stato | Impatto |
|------|-------|---------|
| Argomenti campi | Non analizzati | Non rileva breaking su parametri / rename input |
| Input Object / Union | Non supportati | Cambi su questi tipi non classificati |
| Scalar custom | Ignorati | Aggiunta/rimozione non tracciata |
| Directive definitions | Ignorate | Aggiunta @custom non vista |
| Rename campo | Appare come remove+add | Necessaria heuristica rename |
| Deprecation | Non distinta | Deprecazioni non contano come additive dedicate |

### Roadmap Miglioramenti
| Priorità | Feature | Dettaglio |
|----------|---------|----------|
| Alta | Heuristica rename | Match nome simile + stesso tipo risultato |
| Media | Categoria `deprecation` | Separare cambi non breaking di sola marcatura |
| Media | Supporto Input / Union | Estendere regex o usare parser AST |
| Bassa | Parser AST ufficiale | Libreria `graphql-core` per robustezza |
| Bassa | Report Markdown | Output leggibile per commenti PR |

### Strategia Evolutiva
1. Congelare comportamento attuale (0.1.x)
2. Aggiungere test per deprecazioni (enum + field) → introdurre categoria
3. Refactor parser ad AST mantenendo test invariati
4. Aggiungere detection rename (opt-in) con flag `--detect-rename`

### Linee Guida per Contributi Schema
| Caso | Azione Richiesta |
|------|------------------|
| Aggiunta campo | Aggiornare schema backend + mirror + changelog (patch/minor) |
| Rimozione campo | Pianificare deprecation → rimozione in release major |
| Deprecation | Annotare `@deprecated(reason:"...")` + entry changelog |
| Aggiunta enum value | Aggiornare mirror + changelog |
| Violazione interfaccia | Aggiungere campo mancante o rimuovere implements |

### Test
I test in `backend/tests/test_schema_diff.py` generano scenari minimalisti creando versioni temporanee dei due file SDL e invocando lo script via subprocess, poi validano la classificazione.

Per aggiungere un nuovo caso:
1. Duplicare un test esistente
2. Modificare le SDL inline
3. Aggiornare asserzione su `classification`

### Manutenzione Versione Script
Incrementare `tool_version` quando:
- Cambia formato JSON
- Aggiunta nuova categoria
- Cambia semantica classificazione

Patch interne (refactor parser) senza modifiche output → stesso numero minor.

### Esempio Uso in Makefile (futuro)
```make
schema-semantic-check:
	uv run python backend/scripts/verify_schema_breaking.py | tee /tmp/schema_diff.json
	jq -e '.classification != "breaking"' /tmp/schema_diff.json >/dev/null || { echo 'Breaking change rilevato'; exit 1; }
```

### FAQ
**Perché regex e non parser AST?** Rapidità iniziale: implementazione <150 righe per coprire casi core. Si migrerà ad AST quando aumenterà la complessità (input/union/directive).

**Come gestire rename campo?** Processo consigliato: introdurre nuovo campo → marcare il vecchio `@deprecated` → rimuovere in major successiva.

**Posso ignorare un breaking temporaneamente?** Opzione futura: flag `--allow-breaking` per rami sperimentali; oggi no (fail immediato).

---
Ultimo aggiornamento: 2025-09-22
