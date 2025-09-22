# Schema Contract Policy

> Stato: Versione Iniziale

Questa policy definisce le regole di evoluzione del contratto GraphQL condiviso tra Backend, Mobile e Web Sandbox.

## Principi
1. **Fonte Unica di Verità**: lo schema runtime del backend è la sorgente; il mirror (`graphql/schema.graphql`) è una copia distribuita.
2. **Evoluzione Additiva Prima**: preferire aggiungere nuovi campi / tipi invece di modificare o rimuovere quelli esistenti.
3. **Deprecation Graduale**: ogni rimozione deve essere preceduta da una fase di deprecazione esplicita (`@deprecated(reason: "...")`).
4. **Breaking Changes Rari**: le modifiche breaking sono pianificate, raggruppate e accompagnate da MIGRATION GUIDES.
5. **Automazione Diff**: un workflow CI classifica differenze (additive / breaking / deprecation) e fallisce se breaking non marcata.

## Classificazione Cambi
| Tipo | Esempi | Label PR | Richiesto |
|------|--------|----------|-----------|
| Additive | nuovo campo opzionale, nuovo tipo, nuova query/mutation | `schema:additive` | Changelog se rilevante |
| Deprecation | aggiunta `@deprecated` con reason | `schema:deprecation` | Reason obbligatoria + data target |
| Breaking | rimozione campo, cambio tipo, campo obbligatorio aggiunto senza default | `breaking` | MIGRATION + versione major |

## Processo PR Schema
1. Modifica resolver / type backend.
2. `make schema-export` aggiorna `backend/graphql/schema.graphql`.
3. Copia (o script) aggiorna mirror `graphql/schema.graphql`.
4. Push PR con label adeguata.
5. Workflow `schema-diff` calcola diff:
   - Se breaking e manca label `breaking` → FAIL
   - Se deprecation senza reason → FAIL
6. Merge dopo revisione (mobile/web verificano impatto).

## Deprecation Timeline
| Fase | Azione | Durata Minima |
|------|--------|---------------|
| Introduzione | Aggiunta campo nuovo parallelo a legacy | - |
| Deprecazione | Campo legacy marcato `@deprecated` | ≥1 minor release backend |
| Rimozione | Rimozione campo legacy (breaking) | Major successiva |

## Regole Dettagliate
- Non rendere mai un campo opzionale → obbligatorio senza nuovo major.
- Evitare rename diretto: introdurre nuovo campo, marcare il vecchio deprecated, rimuovere in major.
- Trasformazioni semantiche (unità di misura, significato valore) = breaking anche se tipo statico invariato.
- Cambi ordine argomenti NON sono breaking in GraphQL, ma cambiare default sì.

## Policy Versioning
- Backend versiona SemVer (`vX.Y.Z`).
- Breaking → incremento X (major).
- Deprecation → incremento Y (minor) + nota changelog.
- Additive minore → minor o patch (se non impatta client).

## Changelog Schema
Ogni PR che tocca lo schema deve aggiornare la sezione `[Unreleased]` del `CHANGELOG.md` (root o backend) con formato:
```
### Schema
- (Type) Aggiunto campo `Product.fiber` (additive).
```

## Validazione Automatica (futuro)
Script `scripts/verify_schema_breaking.py` (TODO) produrrà output JSON:
```
{
  "classification": "additive|breaking|deprecation",
  "summary": ["Changed type of Product.calories from Int to Float"],
  "errors": []
}
```

Il workflow userà questo output per decidere PASS/FAIL.

## Esempi
- Aggiunta campo opzionale: additive.
- Rimozione campo: breaking.
- Cambio `Int` → `Float`: breaking.
- Aggiunta mutation: additive.
- Aggiunta argomento non obbligatorio: additive.
- Aggiunta argomento obbligatorio senza default: breaking.

## FAQ
**Perché mirror root?** Riduce coupling temporale: mobile/web possono aggiornare da mirror stabile durante refactor backend.

**Posso saltare deprecation?** Solo se il campo è stato introdotto da pochissimo e non ancora usato (eccezione rara, documentare in PR).

**Come gestire campi calcolati sperimentali?** Prefisso opzionale (es. `experimental_`) + sezione docs; possono essere rimossi più rapidamente ma sempre annunciati.

---
Fine documento.
