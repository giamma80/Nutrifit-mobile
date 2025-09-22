# Mobile (Flutter) - Bootstrap

> Stato: BOOTSTRAP (directory inizializzata, codice non ancora presente)

Questa cartella ospiterà l'app Flutter **Nutrifit Mobile**.

## Obiettivi Iniziali
- Fetch schema GraphQL dal backend
- Prima query `product(barcode)` con UI minimale
- Mutation `logMeal` con form semplice e output raw
- Strato caching locale (in-memory) e placeholder offline queue

## Roadmap Breve
| Step | Descrizione | Stato |
|------|-------------|-------|
| 1 | Script fetch schema (`tool/fetch_schema.dart` o shell) | TODO |
| 2 | Setup dipendenze base (`graphql_flutter` o `ferry`) | TODO |
| 3 | UI prototipo Product Lookup | TODO |
| 4 | UI logMeal form + response | TODO |
| 5 | Integrazione offline queue (stub) | TODO |
| 6 | Codegen fragments & models | TODO |

## Scelta Stack GraphQL (Da Valutare)
- Opzione 1: `graphql_flutter` (rapida, meno boilerplate)
- Opzione 2: `ferry` + codegen (scalabilità e normalizzazione avanzata)

Decisione verrà presa dopo definizione volume query/mutation stable.

## Script Schema (Planned)
Il file `../backend/graphql/schema.graphql` è la fonte. Verrà copiato qui (o in `lib/graphql/`) tramite script.

## Note Versioning
Versioni mobile taggate come `mobile-vX.Y.Z` indipendentemente dal backend.

## Contributi
Aggiungere issue con label `mobile` per priorità/feature.
